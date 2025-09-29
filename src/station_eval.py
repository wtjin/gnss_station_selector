# Evaluating the data quality of stations using hyprid TOPSIS
# input：
'''
1. Station list file
2. The result file of station data quality analyzed by anubis
3. Mode: Single-day quality evaluation or multi-day quality evaluation, 
where M stands for multi-day and S stands for single-day
'''

import numpy as np
import pandas as pd
from pathlib import Path
import os

def directional_norm(df, direction):
    """Direction normalization"""
    x = df.values.copy().astype(float)
    for j, d in enumerate(direction):
        col_data = x[:, j]
        if d == 1:  # benefit-type
            max_val = col_data.max()
            if max_val > 1e-10:
                x[:,j] = col_data / max_val
            else:
                x[:,j] = 1.0  
        else:  # cost-type
            max_val, min_val = col_data.max(), col_data.min()
            if max_val > min_val + 1e-10:
                x[:,j] = (max_val - col_data) / (max_val - min_val)
            else:
                x[:,j] = 1.0  
    return pd.DataFrame(x, index=df.index, columns=df.columns)

def entropy_weight(mat, smooth=1e-10):
    
    
    mat_pos = np.abs(mat) + smooth
    
    # Calculate the probability matrix
    p = mat_pos / mat_pos.sum(axis=0)
    
    # Calculate information entropy
    entropy = -np.sum(p * np.log(p + smooth), axis=0) / np.log(mat_pos.shape[0])
    
    # Calculate the weight
    d = 1 - entropy
    w = d / (d.sum() + smooth)
    
    return w

def calculate_ahp_weights(judgment_matrix: np.ndarray):
    """Calculating subjective weights using the AHP judgment matrix"""
    
    n = judgment_matrix.shape[0]
    if n != judgment_matrix.shape[1]:
        raise ValueError("The judgment matrix must be a square matrix!")
        
    col_sums = judgment_matrix.sum(axis=0)
    norm_matrix = judgment_matrix / col_sums
    
    weights = norm_matrix.mean(axis=1)
        
    return weights / weights.sum()
def get_quality_level(score: float) -> str:
    if score >= 0.8:
        return 'Excellent'
    elif score >= 0.6:
        return 'Good'
    elif score >= 0.4:
        return 'Fair'
    else:
        return 'Poor'

def gnss_topsis_evaluation(stations: pd.DataFrame, w_sys: dict=None, show_details:bool=True)->pd.DataFrame:
    """
    Main function for quality evaluation of GNSS station data
    
    Parameters:
    - stations: DataFrame,Station data, the column name format is '{system}_{indicator}_{yyyydoy}'
    - w_sys: dict,System weight, default weight is {'G':0.40, 'R':0.2, 'E':0.2, 'C':0.2}
    - show_details: bool,Whether to output detailed information
    
    Returns:
    - DataFrame: Evaluation results, including TOPSIS scores and quality grades
    """
    
    # Default system weight
    if w_sys is None:
        w_sys = {'G':0.40, 'R':0.20, 'E':0.20, 'C':0.20}
    
    # Indicator direction: 1 means the benefit-type, 0 means the cost-type
    direction = np.array([1,0,0,0,0,0,0,0,1,1]*4)
    
    
    norm = directional_norm(stations, direction)
    
    # Calculate the weight of indicators for each system
    w_ind = {}
    if show_details:
        print("=== Weight of each system ===")
    
    # Subjective weight
    ahp_judgment_matrix = np.array([
    # nobs, csAll, nSlp, nJmp, nGap, nPcs,  mp1,  mp2, cnr1, cnr2
    [1.0,   3.0,   3.0,  5.0,  7.0,  7.0,  3.0,  3.0,  1.0,  1.0],  # _nobs
    [1/3,   1.0,   1.0,  3.0,  5.0,  5.0,  1/3,  1/3,  1/3,  1/3],  # _csAll
    [1/3,   1.0,   1.0,  3.0,  5.0,  5.0,  1/3,  1/3,  1/3,  1/3],  # _nSlp
    [1/5,   1/3,   1/3,  1.0,  3.0,  3.0,  1/5,  1/5,  1/5,  1/5],  # _nJmp
    [1/7,   1/5,   1/5,  1/3,  1.0,  1.0,  1/7,  1/7,  1/7,  1/7],  # _nGap
    [1/7,   1/5,   1/5,  1/3,  1.0,  1.0,  1/7,  1/7,  1/7,  1/7],  # _nPcs
    [1/3,   3.0,   3.0,  5.0,  7.0,  7.0,  1.0,  1.0,  1/3,  1/3],  # _mp1
    [1/3,   3.0,   3.0,  5.0,  7.0,  7.0,  1.0,  1.0,  1/3,  1/3],  # _mp2
    [1.0,   3.0,   3.0,  5.0,  7.0,  7.0,  3.0,  3.0,  1.0,  1.0],  # _cnr1
    [1.0,   3.0,   3.0,  5.0,  7.0,  7.0,  3.0,  3.0,  1.0,  1.0]   # _cnr2
    ])

    subjective_weights = calculate_ahp_weights(ahp_judgment_matrix)
    
    for sys in ['G','R','E','C']:
        sub = norm[[c for c in norm.columns if c.startswith(sys)]]
        objective_weights = entropy_weight(sub.values)
        # weights for each system
        alpha = 0.7  # Subjective weights are more important
        combined_weights = alpha * subjective_weights + (1 - alpha) * objective_weights
        combined_weights = combined_weights / combined_weights.sum()
        w_ind[sys] = combined_weights
        # w_ind[sys] = entropy_weight(sub.values)
        
        if show_details:
            indicators = ['nobs','csAll','nSlp','nJmp','nGap','nPcs','mp1','mp2','cnr1','cnr2']
            print(f"{sys}system:")
            for i, ind in enumerate(indicators):
                print(f"  {ind}: {w_ind[sys][i]:.4f}")
    
    if show_details:
        print(f"\n=== System Weight ===")
        for sys, weight in w_sys.items():
            print(f"{sys}system: {weight}")
    
    # Calculate the weighted matrix
    weighted = pd.DataFrame(0.0, index=norm.index, columns=norm.columns)
    for sys in ['G','R','E','C']:
        sub_cols = [c for c in norm.columns if c.startswith(sys)]
        # system weight × weight for each system
        final_weights = w_ind[sys] * w_sys[sys]
        weighted[sub_cols] = norm[sub_cols] * final_weights
    
    # TOPSIS computation
    ideal_best = weighted.max()
    ideal_worst = weighted.min()
    
    d_best  = np.sqrt(((weighted - ideal_best)**2).sum(axis=1))
    d_worst = np.sqrt(((weighted - ideal_worst)**2).sum(axis=1))
    
    C = d_worst / (d_best + d_worst + 1e-12)
    
    
    result_df = stations.copy()
    result_df['topsis_score'] = C
    result_df['quality_level'] = result_df['topsis_score'].apply(get_quality_level)
    result_df = result_df.sort_values('topsis_score', ascending=False)


    
    # Statistics and output
    if show_details:
        print(f"\n=== Statistics of evaluation results ===")
        print(f"Total number of participating evaluation stations: {len(result_df)}")
        print(f"Average TOPSIS score: {result_df['topsis_score'].mean():.4f}")
        print(f"Highest score: {result_df['topsis_score'].max():.4f}")
        print(f"minimum score: {result_df['topsis_score'].min():.4f}")
        
        print(f"\n=== Quality level distribution (%) ===")
        level_counts = result_df['quality_level'].value_counts()
        for level, count in level_counts.items():
            percentage = count / len(result_df) * 100
            print(f"{level}: {count} ({percentage:.1f}%)")
        
        
        # details of the top 10
        print(f"\n=== Top 10 stations ===")
        top_10 = result_df[['topsis_score', 'quality_level']].head(10)
        print(top_10)
    
    return result_df

def station_eval_main(site_list_file: str, year: int, 
                    doy_start: int, doy_end: int, 
                    work_root_path: str, out_path: str,
                    mode_flag: str):
    """
    Main program entry
    - site_list_file: Site list file
    - year: year
    - doy_start: Start of day of year
    - doy_end: End of Day of Year
    - work_root_path: working directory
    - out_path: Output file directory
    - mode_flag: Mode selection: M stands for multiple days, 
                S stands for single day. 
                When S is selected, doy_end can also be bigger than doy_start,
                and the files will be output on a daily basis.
    """
    from extract_qc import extract_qc_single_day,extract_qc_multiple_days
    from site_list import read_list

    site_list = read_list(site_list_file)
    if not os.path.exists(out_path):
        os.mkdir(out_path)

    if args.mode_flag.upper() == 'S':
        for doy in range(doy_start, doy_end+1):
            stations_data = extract_qc_single_day(site_list, year, doy, work_root_path)
            stations_data.set_index('site_name', inplace=True)
            results = gnss_topsis_evaluation(stations_data)
            result_file_name = Path(args.out_path, f'sta_rank_evaluation_{year:04d}_{doy:03d}_{doy:03d}.csv')
            results[['topsis_score', 'quality_level']].to_csv(result_file_name)

    elif args.mode_flag.upper() == 'M':
        stations_data = extract_qc_multiple_days(site_list, year, doy_start, doy_end, work_root_path)
        stations_data.set_index('site_name', inplace=True)
        results = gnss_topsis_evaluation(stations_data)
        result_file_name = Path(args.out_path, f'sta_rank_evaluation_{year:04d}_{doy_start:03d}_{doy_end:03d}.csv')
        results[['topsis_score', 'quality_level']].to_csv(result_file_name)

    else:
        print('the mode_flag is not correct, please input S or M')


if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--site_list_file', help='Site list file path')
    parser.add_argument('--year', type=int, help='year')
    parser.add_argument('--doy_start', type=int, help='start of day of year')
    parser.add_argument('--doy_end', type=int, help='end of day of year')
    parser.add_argument('--work_root_path', help='Working root directory path')
    parser.add_argument('--out_path', help='Output path of the station scoring file')
    parser.add_argument('--mode_flag', help='Multi-day or single-day mode: M represents multi-day mode, and S represents single-day mode.')
    # ===========================

    args = parser.parse_args()
    station_eval_main(args.site_list_file, 
        args.year, args.doy_start, args.doy_end, 
        args.work_root_path, args.out_path, 
        args.mode_flag)

    