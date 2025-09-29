import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from pathlib import Path
import os
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

def ecef2pos(r):
    """  ECEF to LLH position conversion
    r[0:3]=x,y,z
    pos[0:3]=lat,lon,h
    from pyrtklib
    """
    RE_WGS84 = 6378137.0
    FE_WGS84 = 1.0/298.257223563
    
    pos = np.zeros(3)
    e2 = FE_WGS84*(2-FE_WGS84)
    r2 = r[0]**2+r[1]**2
    v = RE_WGS84
    z = r[2]
    zk = 0
    while abs(z - zk) >= 1e-4:
        zk = z
        sinp = z / np.sqrt(r2+z**2)
        v = RE_WGS84 / np.sqrt(1 - e2 * sinp**2)
        z = r[2] + v * e2 * sinp
    pos[0] = np.arctan(z / np.sqrt(r2)) if r2 > 1e-12 else np.pi / 2 * np.sign(r[2])
    pos[1] = np.arctan2(r[1], r[0]) if r2 > 1e-12 else 0
    pos[2] = np.sqrt(r2 + z**2) - v
    return pos

class SphericalKMeansStationSelector:
    """
    Spherical K-means station selection.
    select the station with the highest quality score in each cluster
    """
    
    def __init__(self, n_clusters, n_init=20, max_iter=300, random_state=42):
        """
        Initialize the selector
        
        Parameters:
        - n_clusters: Number of clusters (i.e., the number of stations to be selected)
        - n_init: Number of runs for K-means++ initialization
        - max_iter: The maximum number of iterations per run
        - random_state: random seed
        """
        self.n_clusters = n_clusters
        self.n_init = n_init
        self.max_iter = max_iter
        self.random_state = random_state
        self.best_result = None
        self.stability_metrics = None
    
    def xyz_to_llh(self, df, xyz_col=['x', 'y', 'z']):
        """
        Convert three-dimensional Cartesian coordinates 
        to longitude, latitude, and geodetic height coordinates
        
        Parameters:
        - df: pandas DataFrame,Containing coordinate information
        - xyz_col: The column names of three-dimensional rectangular coordinates
        """
        xyz = df[xyz_col].values
        pos = np.apply_along_axis(ecef2pos, 1, xyz)

        df['latitude'] = np.degrees(pos[:, 0])
        df['longitude'] = np.degrees(pos[:, 1])
        df['height'] = pos[:, 2]
        
        return df

    
    def spherical_kmeans_plus_plus_init(self, coords_normalized, n_clusters, random_state=None):
        """
        spherical K-means++ initialization
        """
        np.random.seed(random_state)
        n_samples = len(coords_normalized)
        
        # Randomly select the first center
        centers = []
        first_idx = np.random.randint(0, n_samples)
        centers.append(coords_normalized[first_idx])
        
        # Select the remaining k-1 centers
        for _ in range(1, n_clusters):
            # Calculate the spherical distance from each point to the nearest selected center
            distances = np.zeros(n_samples)
            
            for i, point in enumerate(coords_normalized):
                min_dist = float('inf')
                for center in centers:
                    cosine_sim = np.clip(np.dot(point, center), -1.0, 1.0)
                    angular_dist = np.arccos(cosine_sim)
                    min_dist = min(min_dist, angular_dist)
                distances[i] = min_dist
            
            # Probability selection based on squared distance
            probabilities = distances ** 2
            probabilities /= probabilities.sum()
            
            # Select the next center
            next_idx = np.random.choice(n_samples, p=probabilities)
            centers.append(coords_normalized[next_idx])
        
        return np.array(centers)
    
    def spherical_kmeans_single_run(self, coords_xyz, quality_scores, run_id=0):
        """
        Single run of spherical K-means
        """
        # Normalize to the unit sphere
        coords_normalized = coords_xyz / np.linalg.norm(coords_xyz, axis=1, keepdims=True)
        
        # K-means++ initialization
        initial_centers = self.spherical_kmeans_plus_plus_init(
            coords_normalized, self.n_clusters, random_state=self.random_state + run_id
        )
        
        # Use sklearn's KMeans with custom initialization
        kmeans = KMeans(
            n_clusters=self.n_clusters,
            init=initial_centers,
            n_init=1,
            max_iter=self.max_iter,
            random_state=self.random_state + run_id
        )
        
        cluster_labels = kmeans.fit_predict(coords_normalized)
        
        # Select the station with the highest quality score in each cluster.
        selected_indices = []
        selected_scores = []
        
        for cluster_id in range(self.n_clusters):

            cluster_mask = cluster_labels == cluster_id
            cluster_indices = np.where(cluster_mask)[0]
            
            if len(cluster_indices) == 0:
                # the cluster is empty, skip
                continue
            
            # get the quality scores of all stations in the cluster
            cluster_quality_scores = quality_scores.iloc[cluster_indices]
            
            # choose the station with the highest quality score
            best_local_idx = cluster_quality_scores.idxmax()
            best_score = cluster_quality_scores.loc[best_local_idx]
            
            '''
            ##### the following code which is commented out is for the paper
            # choose the station with the lowest quality score
            best_local_idx = cluster_quality_scores.idxmin()
            best_score = cluster_quality_scores.loc[best_local_idx]
            
            # choose the station with the middle quality score
            median_idx = len(cluster_quality_scores) // 2
            best_local_idx = cluster_quality_scores.sort_values().index[median_idx]
            best_score = cluster_quality_scores.loc[best_local_idx]
            
            # choose the station with the ith best quality score
            i = 2
            if len(cluster_quality_scores) > i:
                best_local_idx = cluster_quality_scores.sort_values(ascending=False).index[i]
                best_score = cluster_quality_scores.loc[best_local_idx]
            #####
            '''
            
            selected_indices.append(best_local_idx)
            selected_scores.append(best_score)
        
        # Calculate inertia (based on spherical distance)
        inertia = 0
        for i, point in enumerate(coords_normalized):
            cluster_id = cluster_labels[i]
            center = kmeans.cluster_centers_[cluster_id]
            center = center / np.linalg.norm(center)
            cosine_sim = np.clip(np.dot(point, center), -1.0, 1.0)
            angular_dist = np.arccos(cosine_sim)
            inertia += angular_dist ** 2
        
        return {
            'selected_indices': selected_indices,
            'selected_scores': selected_scores,
            'cluster_labels': cluster_labels,
            'cluster_centers': kmeans.cluster_centers_,
            'inertia': inertia,
            'run_id': run_id,
            'n_selected': len(selected_indices)
        }
    
    def fit(self, df, quality_col='quality_score'):
        """
        Perform spherical K-means clustering multiple times and select the best result
        
        Parameters:
        - df: pandas DataFrame, including station information
        - lat_col: Latitude column name
        - lon_col: Longitude column name
        - quality_col: Quality Score Column Name
        - height_col: Elevation column name (optional)
        - station_id_col: Station ID Column Name (Optional)
        """
        print(f"Start spherical K-means station selection...")
        print(f"Total number of stations: {len(df)}")
        print(f"The selected number of stations: {self.n_clusters}")
        print(f"Number of K-means++ runs: {self.n_init}")
        print("=" * 60)
        
        
        coords_xyz = df[['x', 'y', 'z']].values
        quality_scores = df[quality_col]
        
        # spherical K-means by multiple runs
        results = []
        
        for run in range(self.n_init):
            try:
                result = self.spherical_kmeans_single_run(
                    coords_xyz, quality_scores, run_id=run
                )
                results.append(result)
                
                if (run + 1) % 5 == 0:
                    print(f"Finish running {run + 1}/{self.n_init}, "
                          f"Current best inertia: {min(r['inertia'] for r in results):.4f}")
                          
            except Exception as e:
                print(f"{run} failed to run: {e}")
                continue
        
        if not results:
            raise ValueError("All runs have failed.")
        
        # Select the best result (with the smallest inertia)
        self.best_result = min(results, key=lambda x: x['inertia'])
        
        # Calculate the stability index
        inertias = [r['inertia'] for r in results]
        n_selected_counts = [r['n_selected'] for r in results]
        
        self.stability_metrics = {
            'mean_inertia': np.mean(inertias),
            'std_inertia': np.std(inertias),
            'coefficient_of_variation': np.std(inertias) / np.mean(inertias) if np.mean(inertias) > 0 else 0,
            'min_inertia': np.min(inertias),
            'max_inertia': np.max(inertias),
            'mean_n_selected': np.mean(n_selected_counts),
            'n_successful_runs': len(results)
        }
        
        selected_df = df.loc[self.best_result['selected_indices']].copy()
        
        cluster_info = []
        for i, idx in enumerate(self.best_result['selected_indices']):
            original_idx = df.index.get_loc(idx) if idx in df.index else -1
            if original_idx >= 0:
                cluster_id = self.best_result['cluster_labels'][original_idx]
                cluster_info.append(cluster_id)
            else:
                cluster_info.append(-1)
        
        selected_df['cluster_id'] = cluster_info
        selected_df['selected_quality_score'] = self.best_result['selected_scores']
        
        self.selected_stations = selected_df
        
        # Save the cluster ID and score of all stations
        all_stations_df = df.copy()
        all_stations_df['cluster_id'] = self.best_result['cluster_labels']
        all_stations_df['topsis_score'] = quality_scores
        self.all_stations_with_clusters = all_stations_df
        
        print(f"\nSelection completed!")
        print(f"{len(self.best_result['selected_indices'])} stations are selected successfully.")
        print(f"The best inertia: {self.best_result['inertia']:.4f}")
        print(f"the stability CV: {self.stability_metrics['coefficient_of_variation']:.4f}")
        print(f"Average quality score: {np.mean(self.best_result['selected_scores']):.4f}")
        
        return self
    
    def get_selected_stations(self):
        """
        Get the information of the selected stations
        """
        if self.selected_stations is None:
            raise ValueError("The fit() method has not been executed yet.")

        # Convert the xyz coordinates of the selected stations into longitude, latitude, and elevation for plotting.
        self.selected_stations = self.xyz_to_llh(self.selected_stations)
        
        return self.selected_stations
    
    def get_all_stations_with_clusters(self):
        """
        Obtain information of all stations participating in clustering, 
        including station name, longitude and latitude, cluster ID, and quality score.
        
        Returns:
        - pandas DataFrame, containing information of all stations participating in clustering
        """
        if not hasattr(self, 'all_stations_with_clusters'):
            raise ValueError("The fit() method has not been executed or there is no clustering information.")
        
        all_stations = self.all_stations_with_clusters.copy()
        
        all_stations = self.xyz_to_llh(all_stations)
        
        required_columns = ['site_name', 'latitude', 'longitude', 'cluster_id', 'topsis_score']
        for col in required_columns:
            if col not in all_stations.columns:
                raise ValueError(f"The lacked column: {col}")
        
        # Select the required columns
        result_df = all_stations[required_columns].copy()
        
        return result_df
    
    def get_stability_report(self):
        
        if self.stability_metrics is None:
            raise ValueError("The fit() method has not been executed")
        
        report = f"""
Stability Report on Spherical K-means
{'='*50}
Number of successful runs: {self.stability_metrics['n_successful_runs']}
Number of target clusters: {self.n_clusters}
Actual number of selected stations: {len(self.best_result['selected_indices'])}

Inertia:
  minimum value: {self.stability_metrics['min_inertia']:.4f}
  maximum value: {self.stability_metrics['max_inertia']:.4f}
  average value: {self.stability_metrics['mean_inertia']:.4f}
  standard deviation: {self.stability_metrics['std_inertia']:.4f}
  Coefficient of Variation: {self.stability_metrics['coefficient_of_variation']:.4f}

Quality score statistics:
  Average quality score: {np.mean(self.best_result['selected_scores']):.4f}
  Highest quality score: {np.max(self.best_result['selected_scores']):.4f}
  Minimum quality score: {np.min(self.best_result['selected_scores']):.4f}

Stability evaluation:
  {'excellent (CV < 0.05)' if self.stability_metrics['coefficient_of_variation'] < 0.05 
   else 'good (CV < 0.1)' if self.stability_metrics['coefficient_of_variation'] < 0.1
   else 'general (CV < 0.2)' if self.stability_metrics['coefficient_of_variation'] < 0.2
   else 'poor (CV >= 0.2)'}
        """
        
        return report
    



def choose_sta_main(chosen_num: int, year: int, doy_start: int, doy_end: int, work_root_path: str, data_root_path: str, site_list_file: str, out_path: str):
    """
    The main program for selecting stations using the spherical k-means algorithm based on station quality scores
    - chosen_num: The number of selected stations
    - year
    - doy_start: Start of day of the year
    - doy_end: End of Day of Year
    - work_root_path: working directory
    - data_root_path: Data Directory (mainly scanning the approximate location in the obs file)
    - site_list_file: Site list file
    - out_path: Output file directory
    """
    
    
    # read sta_rank file
    sta_rank_name = f"sta_rank_evaluation_{year:04d}_{doy_start:03d}_{doy_end:03d}.csv"
    df = pd.read_csv(Path(work_root_path, 'sta_eval', sta_rank_name))
    df = df[df['topsis_score'] > 1e-10]
    print("Data preview:")
    print(df.head())
    print(f"\nData shape: {df.shape}")
    
    
    selector = SphericalKMeansStationSelector(
        n_clusters=chosen_num,    # select n stations
        n_init=30,                # run K-means++ by 30 times
        random_state=42
    )
    
    from site_list import scan_rinexo_coord
    # obtain xyz from rinex o file
    sta_coord_df = scan_rinexo_coord(data_root_path, df['site_name'].tolist(), year, doy_start)
    df = df.merge(sta_coord_df, on='site_name', how='inner')

    df = df[df['topsis_score'] >= 0.8]

    
    # select stations
    selector.fit(df, quality_col='topsis_score')
    
    # obtain results
    selected_stations = selector.get_selected_stations()
    
    print(f"\nSelected station:")
    print(selected_stations[['site_name', 'latitude', 'longitude', 
                           'topsis_score']].head(10))
    
    # Save the station names of the selected stations to a text file, 
    # and save the coordinates of the selected stations to a text file.
    from site_list import write_site_list, write_site_list_coord
    if not os.path.exists(out_path): 
        os.makedirs(out_path)
    write_site_list(selected_stations['site_name'].tolist(), 
                    Path(out_path, f'selected_stations_{chosen_num}_{year:04d}_{doy_start:03d}_{doy_end:03d}.txt'))
    write_site_list_coord(selected_stations, 
                        Path(out_path, f'selected_stations_coord_{chosen_num}_{year:04d}_{doy_start:03d}_{doy_end:03d}.txt'), 
                        coord_col=['latitude', 'longitude'])

    
    # Output Stability Report
    print(selector.get_stability_report())
    
    # Save all the information of the stations participating in the clustering to a CSV file.
    all_stations_with_clusters = selector.get_all_stations_with_clusters()
    all_stations_csv_path = Path(out_path, f'all_stations_with_clusters_{chosen_num}_{year:04d}_{doy_start:03d}_{doy_end:03d}.csv')
    all_stations_with_clusters.to_csv(all_stations_csv_path, index=False)
    print(f"All the information of the stations participating in the clustering has been saved to: {all_stations_csv_path}")
    

if __name__ == "__main__":
    
    # ===== Set command-line parameters =====
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--chosen_num', type=int, help='The number of selected stations')
    parser.add_argument('--year', type=int, help='year')
    parser.add_argument('--doy_start', type=int, help='Start of day of year')
    parser.add_argument('--doy_end', type=int, help='End of year day of year')
    parser.add_argument('--work_root_path', help='Working root directory path')
    parser.add_argument('--data_root_path', help='Data root directory path')
    parser.add_argument('--site_list_file', help='Site list file path')
    parser.add_argument('--out_path', help='Output path of the station selection result file')
    # ===========================
    # year = 2025
    # doy_start = 1
    # doy_end = 1
    # work_root_path = 'D:/code_tmp/Python/cepnt_sta'
    # data_root_path = 'D:/code_tmp/Python/cepnt_sta'
    # site_list_file = 'site_list'
    # out_path = 'D:/code_tmp/Python/cepnt_sta/out'
    args = parser.parse_args()
    choose_sta_main(args.chosen_num, args.year, 
                    args.doy_start, args.doy_end, 
                    args.work_root_path, args.data_root_path, 
                    args.site_list_file, args.out_path)
    
