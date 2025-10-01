A Hybrid-Weight TOPSIS and Clustering Approach for Optimal GNSS Station Selection



python >=3.10

matplotlib==3.10.6

numpy==2.3.3

pandas==2.3.3

scikit_learn==1.7.2

### 1. Data and Directory Setup

* Define the root directory for data storage. We will use data_root_path to denote this directory. The directory structure for GNSS data is as follows:

  * Observation data: f”{data_root_path}/obs/daily/{year:04d}/{doy:03d}/”

  * Broadcast ephemerides: f”{data_root_path}/nav/daily/”

  * IGS weekly solution coordinate files (SINEX): f”{data_root_path}/snx/”

* Define the root working directory for algorithm execution. We will use work_root_path to denote this directory.

  * Analysis output from the Anubis software will be located at: f”{work_root_path}/work{year:04d}{doy:03d}/anubis/out/”

* Note: Once data_root_path and work_root_path are set, the subordinate directory structures described above are fixed and cannot be customized.

### 2. Data Preparation

* Download IGSNetwork.csv from: https://files.igs.org/pub/station/general/IGSNetwork.csv.

* Download the IGS weekly solution coordinate files for the specified year and Day of Year (DOY) into the f”{data_root_path}/snx/” directory.

* Download the GNSS broadcast ephemeris files for the specified time into the f”{data_root_path}/nav/daily/” directory.

* Generate an initial station list (S1) by filtering for stations that support all four GNSS systems (GPS, GLONASS, Galileo, and BeiDou) and have coordinates present in all weekly solution files within the analysis period.

  ```
  python gene_initial_4sys_sitelist.py --bindir XXX --sinex_root_path XXX --year XXX --doy_start XXX --doy_end XXX --out_file_path XXX
  ```

  For example:

  ```
  python gene_initial_4sys_sitelist.py --bindir /usr/bin --sinex_root_path /data1/jinweitong/data/gnss/snx --year 2022 --doy_start 92 --doy_end 92 --out_file_path /data1/jinweitong/work/choose_sta_work/sitelst/site_list_init_2022092
  ```

  * --bindir: Specifies the path to the wget executable. This program uses wget for file downloads. A binary is provided in the 3rd_party/bin directory if it is not installed on your system.

  * --sinex_root_path: The directory containing the IGS weekly solution files.

  * --year, --doy_start, --doy_end: Specify the analysis period. Setting doy_start and doy_end to the same value indicates a single-day analysis.

  * --out_file_path: Defines the full path and filename for the initial station list S1. This path is user-defined, and the file will be used in subsequent steps.

* Download the GNSS observation data for the stations in list S1 and store them in f”{data_root_path}/obs/daily/{year:04d}/{doy:03d}/”.

### 3. Data Quality Analysis using Anubis

* Execute the following script to perform data quality analysis with the Anubis software:

  ```
  python anibus_ana.py --xml_file XXX --anubis_bin XXX --site_list_file XXX --year XXX --doy_start XXX --doy_end XXX --data_root_path XXX --work_root_path XXX
  ```

  For example:

  ```
  python anibus_ana.py --xml_file /data1/jinweitong/work/choose_sta_work/config/anibus_chosensta_template_save --anubis_bin /home/jinweitong/open_source/anubis/anubis --site_list_file /data1/jinweitong/work/choose_sta_work/sitelst/site_list_init_2022092 --year 2022 --doy_start 92 --doy_end 92 --data_root_path /data1/jinweitong/data/gnss --work_root_path /data1/jinweitong/work/choose_sta_work
  ```

  * --xml_file: The Anubis configuration template for GNSS data preprocessing.

  * --anubis_bin: The full path to the Anubis executable.

  * --site_list_file: The initial station list file generated in step (2).

  * --data_root_path: The root data directory defined in step (1).

  * --work_root_path: The root working directory defined in step (1).

* Upon completion, this step generates analysis result files in the Anubis output directory: f”{work_root_path}/work{year:04d}{doy:03d}/anubis/out/”. The files are named using the format f”{site_name}{year:04d}{doy:03d}.xtr”, where site_name is the four-character station ID. For instance, the result for station ABMF on DOY 91 of 2022 would be ABMF2022091.xtr.

### 4. Data Quality Evaluation using Hybrid-Weight TOPSIS

* Execute the following script to evaluate station data quality:

  ```
  python station_eval.py --site_list_file XXX --year XXX --doy_start XXX --doy_end XXX --work_root_path XXX --out_path XXX --mode_flag XXX
  ```

  For example:

  ```
  python station_eval.py --site_list_file /data1/jinweitong/work/choose_sta_work/sitelst/site_list_init_2022092 --year 2022 --doy_start 92 --doy_end 92 --work_root_path /data1/jinweitong/work/choose_sta_work --out_path /data1/jinweitong/work/choose_sta_work/sta_eval --mode_flag S
  ```

  * --site_list_file: The initial station list file from step (2).

  * --work_root_path: The root working directory defined in step (1).

  * --out_path: A user-defined directory to store the station quality score files.

  * --mode_flag S: Indicates single-day processing mode.

* This step generates a CSV file containing the data quality scores for each station in the specified output path.

### 5. Station Selection using Spherical K-Means Clustering

* Finally, select the optimal station network using the following script:

  codeBash

  ```
  python choose_sta.py --chosen_num XX --site_list_file XXX --year XXX --doy_start XXX --doy_end XXX --work_root_path XXX --data_root_path XXX --out_path XXXX
  ```

  For example:

  ```
  python choose_sta.py --chosen_num 30 --site_list_file /data1/jinweitong/work/choose_sta_work/sitelst/site_list_init_2022092 --year 2022 --doy_start 92 --doy_end 92 --work_root_path /data1/jinweitong/work/choose_sta_work --data_root_path /data1/jinweitong/data/gnss --out_path /data1/jinweitong/work/choose_sta_work/chosen_sta_out
  ```

  * --chosen_num: The desired number of stations to select (e.g., 30).

  * --site_list_file: The initial station list file from step (2).

  * --work_root_path: The root working directory defined in step (1).

  * --data_root_path: The root data directory defined in step (1).

  * --out_path: A user-defined directory to store the final station lists.

* This step produces two output files in the specified path:

  * selected_stations_{chosen_num}_{year:04d}_{start_doy:03d}_{end_doy:03d}.txt

  * selected_stations_coord_{chosen_num}_{year:04d}_{start_doy:03d}_{end_doy:03d}.txt

* Following the example, the script will generate:

  * selected_stations_30_2022_092_092.txt

  * selected_stations_coord_30_2022_092_092.txt

* The first file contains the list of four-character station identifiers, while the second file contains their corresponding latitude and longitude coordinates.

