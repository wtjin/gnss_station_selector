# Extract information from anubis's calculation results
# input:
"""
1. Station list file
2. Path of the Anubis analysis result file: /work/work$yyyy$doy/anubis/output/$sitename+year+doy.xtr
"""

# final return：
"""
panda dataframe: [site_name, 
G_nobs_yyyydoy,G_csAll_yyyydoy,G_nSlp_yyyydoy,G_nJmp_yyyydoy,G_nGap_yyyydoy,G_nPcs_yyyydoy,
G_mp1_yyyydoy,G_mp2_yyyydoy,G_cnr1_yyyydoy,G_cnr2_yyyydoy,
R……,
E……,
C……]
"""
# Where to find it in the file
"""
(Each system has 10 indicators)
#====== Summary statistics:
nobs
csAll、nSlp、nJmp、nGap、nPcs、mp1、mp2
#====== Signal to noise ratio:
cnr1、cnr2

"""
# 

import re
import os
import pandas as pd
from pathlib import Path


def extract_qc_single_site(site_name: str, year: int, doy: int, work_root_path: str) -> dict:
    """
    Extract qc information from the analysis results of a single station
    """
    qc_dict = {} 

    qc_file_name = site_name.upper() + str(year).zfill(4)+str(doy).zfill(3) +'.xtr'
    qc_file_path = Path(work_root_path, 'work'+str(year).zfill(4)+str(doy).zfill(3), 
                        'anubis', 'out', qc_file_name)
    
    # penalty values
    if not qc_file_path.exists():
        qc_dict['GPS'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
        qc_dict['GLO'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
        qc_dict['GAL'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
        qc_dict['BDS'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
        
        return qc_dict
    
    with open(qc_file_path, "r") as file:
        data = file.readlines()

    # extract summary statistics
    s_index = 0
    for index, line in enumerate(data):
        if line.startswith('#====== Summary statistics'):
            s_index = index
        elif line.startswith('#======') and index > s_index:
            e_index = index
            break
    ## Excluding extreme cases with only a few epochs
    for line in data[s_index:e_index]:
        if line.startswith('=TOTSUM'):
            tmp_list = line.split()
            hours = float(tmp_list[5])
            if hours < 0.5 + 1e-10:
                print('Only several epochs, skip this station\n')
                qc_dict['GPS'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
                qc_dict['GLO'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
                qc_dict['GAL'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
                qc_dict['BDS'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
        
                return qc_dict
    ## Lack of observation data from a certain system
    lack_of_sys = {'G':False, 'R':False, 'E':False, 'C':False}
    for line in data[s_index:e_index]:
        if line.startswith('=GPSSUM'):
            lack_of_sys['G'] = True
            continue
        elif line.startswith('=GLOSUM'):
            lack_of_sys['R'] = True
            continue
        elif line.startswith('=GALSUM'):
            lack_of_sys['E'] = True
            continue
        elif line.startswith('=BDSSUM'):
            lack_of_sys['C'] = True
            continue
    # If the observation data of a certain system is missing, then return the penalty value.
    if False in lack_of_sys.values():
        print('Obs of certain system is lack, skip this station\n')
        qc_dict['GPS'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
        qc_dict['GLO'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
        qc_dict['GAL'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
        qc_dict['BDS'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
        
        return qc_dict


    ## extract csAll、nSlp、nJmp、nGap、nPcs、mp1、mp2 from summary statistics
    for ii, line in enumerate(data[s_index:e_index]):
        if line.startswith('=GPSSUM'):
            tmp_list = line.split()
            G_csAll = int(tmp_list[10])
            G_nSlp = int(tmp_list[14])
            G_nJmp= int(tmp_list[15])
            G_nGap = int(tmp_list[16])
            G_nPcs = int(tmp_list[17])
            # 如果不存在mp1、mp2,表示该系统仅存在单频观测值,此时需要标识一下
            # 对于定轨估钟而言该系统仅存在单频观测值无法使用
            if tmp_list[18].strip() == '-':
                G_mp1 = -1
                G_mp2 = -1
            elif tmp_list[19].strip() == '-':
                G_mp1 = -1
                G_mp2 = -1
            else:
                G_mp1 = float(tmp_list[18])
                G_mp2 = float(tmp_list[19])

        elif line.startswith('=GALSUM'):
            tmp_list = line.split()
            E_csAll = int(tmp_list[10])
            E_nSlp = int(tmp_list[14])
            E_nJmp= int(tmp_list[15])
            E_nGap = int(tmp_list[16])
            E_nPcs = int(tmp_list[17])
            # If mp1 and mp2 do not exist, it indicates that only 
            # single-frequency observations exist in the system, 
            # and in this case, it needs to be marked.
            # For orbit determination and clock estimation, 
            # this system can only provide single-frequency observations 
            # and thus cannot be used.
            if tmp_list[18].strip() == '-':
                E_mp1 = -1
                E_mp2 = -1
            elif tmp_list[22].strip() == '-':
                E_mp1 = -1
                E_mp2 = -1
            else:
                E_mp1 = float(tmp_list[18])
                E_mp2 = float(tmp_list[22])
                   
        elif line.startswith('=GLOSUM'):
            tmp_list = line.split()
            R_csAll = int(tmp_list[10])
            R_nSlp = int(tmp_list[14])
            R_nJmp= int(tmp_list[15])
            R_nGap = int(tmp_list[16])
            R_nPcs = int(tmp_list[17])
            # If mp1 and mp2 do not exist, it indicates that only 
            # single-frequency observations exist in the system, 
            # and in this case, it needs to be marked.
            # For orbit determination and clock estimation, 
            # this system can only provide single-frequency observations 
            # and thus cannot be used.
            if tmp_list[18].strip() == '-':
                R_mp1 = -1
                R_mp2 = -1
            elif tmp_list[19].strip() == '-':
                R_mp1 = -1
                R_mp2 = -1
            else:
                R_mp1 = float(tmp_list[18])
                R_mp2 = float(tmp_list[19])
            
        elif line.startswith('=BDSSUM'):
            tmp_list = line.split()
            C_csAll = int(tmp_list[10])
            C_nSlp = int(tmp_list[14])
            C_nJmp= int(tmp_list[15])
            C_nGap = int(tmp_list[17])
            C_nPcs = int(tmp_list[17])
            # If mp1 and mp2 do not exist, it indicates that only 
            # single-frequency observations exist in the system, 
            # and in this case, it needs to be marked.
            # For orbit determination and clock estimation, 
            # this system can only provide single-frequency observations 
            # and thus cannot be used.
            if tmp_list[19].strip() == '-':
                C_mp1 = -1
                C_mp2 = -1
            elif tmp_list[23].strip() == '-':
                C_mp1 = -1
                C_mp2 = -1
            else:
                C_mp1 = float(tmp_list[19])
                C_mp2 = float(tmp_list[23])
            break
        
    ## nobs
    GPS_obs_lst = []
    GAL_obs_lst = []
    GLO_obs_lst = []
    BDS_obs_lst = []
    GLO_2P_flag = True
    GAL_X_flag = False
    for ii, line in enumerate(data[s_index:e_index]):
        if line.startswith('=GPSC1C'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GPS_obs_lst.append(have_obs)
            continue
        elif line.startswith('=GPSC2W'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GPS_obs_lst.append(have_obs)
            continue
        elif line.startswith('=GPSL1C'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GPS_obs_lst.append(have_obs)
            continue
        elif line.startswith('=GPSL2W'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GPS_obs_lst.append(have_obs)
            continue
        
        if line.startswith('=GALC1C'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GAL_obs_lst.append(have_obs)
            continue
        elif line.startswith('=GALC5Q'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GAL_obs_lst.append(have_obs)
            continue
        elif line.startswith('=GALL1C'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GAL_obs_lst.append(have_obs)
            continue
        elif line.startswith('=GALL5Q'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GAL_obs_lst.append(have_obs)
            continue
        
        # If there are no observation data for 1C and 5Q,
        #  then check whether there are observation data for 1X and 5X.
        if line.startswith('=GALC1X'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GAL_obs_lst.append(have_obs)
            continue
        elif line.startswith('=GALC5X'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GAL_obs_lst.append(have_obs)
            continue
        elif line.startswith('=GALL1X'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GAL_obs_lst.append(have_obs)
            continue
        elif line.startswith('=GALL5X'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GAL_obs_lst.append(have_obs)
            GAL_X_flag = True
            continue


        if line.startswith('=GLOC1C'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GLO_obs_lst.append(have_obs)
            continue
        elif line.startswith('=GLOC2P'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GLO_obs_lst.append(have_obs)
            continue
        elif line.startswith('=GLOL1C'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GLO_obs_lst.append(have_obs)
            # When reading up to L, if there is still only one, 
            # it can be determined that there are no observed values of 2P.
            if len(GLO_obs_lst) == 2 and data[s_index+ii-1].startswith('=GLOC2C'):
                tmp_list = line.split()
                have_obs = int(tmp_list[8])
                GLO_obs_lst.append(have_obs)
                GLO_2P_flag = False
                continue


        elif line.startswith('=GLOL2P'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GLO_obs_lst.append(have_obs)
            continue
        
        # Even if GLONASS has finished reading the observation data and they are still incomplete,
        # it proves that the L2P observation data have not been read.
        if len(GLO_obs_lst) == 3 and GLO_2P_flag == False and data[s_index+ii].startswith('=GLOL2C'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            GLO_obs_lst.append(have_obs)
            continue
        
        

        if line.startswith('=BDSC2I'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            BDS_obs_lst.append(have_obs)
            continue
        elif line.startswith('=BDSC6I'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            BDS_obs_lst.append(have_obs)
            continue
        elif line.startswith('=BDSL2I'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            BDS_obs_lst.append(have_obs)
            continue
        elif line.startswith('=BDSL6I'):
            tmp_list = line.split()
            have_obs = int(tmp_list[8])
            BDS_obs_lst.append(have_obs)

            break

    G_nobs = sum(GPS_obs_lst)
    R_nobs = sum(GLO_obs_lst)
    C_nobs = sum(BDS_obs_lst)
    E_nobs = sum(GAL_obs_lst)

    # #====== Signal to noise ratio
    for index2, line in enumerate(data):
        if line.startswith('#====== Signal to noise ratio'):
            cnr_index = index2 + 1
            break
    
    for line in data[cnr_index:]:
        if line.startswith('=GPSS1C'):
            tmp_list = line.split()
            G_cnr1 = float(tmp_list[3])
        elif line.startswith('=GPSS2W'):
            tmp_list = line.split()
            G_cnr2 = float(tmp_list[3])
        
        if GAL_X_flag == True:
            # If there is no 1C and 5Q data, use X data.
            if line.startswith('=GALS1X'):
                tmp_list = line.split()
                E_cnr1 = float(tmp_list[3])
            elif line.startswith('=GALS5X'):
                tmp_list = line.split()
                E_cnr2 = float(tmp_list[3])
        else:
            if line.startswith('=GALS1C'):
                tmp_list = line.split()
                E_cnr1 = float(tmp_list[3])
            elif line.startswith('=GALS5Q'):
                tmp_list = line.split()
                E_cnr2 = float(tmp_list[3])
        
        
        
        
        if line.startswith('=GLOS1C'):
            tmp_list = line.split()
            R_cnr1 = float(tmp_list[3])
        elif GLO_2P_flag == True and line.startswith('=GLOS2P'):
            tmp_list = line.split()
            R_cnr2 = float(tmp_list[3])
        elif GLO_2P_flag == False and line.startswith('=GLOS2C'):
            tmp_list = line.split()
            R_cnr2 = float(tmp_list[3])
        
        if line.startswith('=BDSS2I'):
            tmp_list = line.split()
            C_cnr1 = float(tmp_list[3])
        elif line.startswith('=BDSS6I'):
            tmp_list = line.split()
            C_cnr2 = float(tmp_list[3])

            break
    
    # single frequency
    if G_mp1 < 0.0:
        # For orbit determination and clock estimation, single-frequency observation is not suitable, 
        # so other indicators are all set to the worst.
        qc_dict['GPS'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
    else:
        qc_dict['GPS'] = [G_nobs,G_csAll,G_nSlp,G_nJmp,G_nGap,G_nPcs,G_mp1,G_mp2,G_cnr1,G_cnr2]

    if R_mp1 < 0.0:
        qc_dict['GLO'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
    else:
        qc_dict['GLO'] = [R_nobs,R_csAll,R_nSlp,R_nJmp,R_nGap,R_nPcs,R_mp1,R_mp2,R_cnr1,R_cnr2]

    if E_mp1 < 0.0:
        qc_dict['GAL'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
    else:
        qc_dict['GAL'] = [E_nobs,E_csAll,E_nSlp,E_nJmp,E_nGap,E_nPcs,E_mp1,E_mp2,E_cnr1,E_cnr2]

    if C_mp1 < 0.0:
        qc_dict['BDS'] = [0,999999,999999,999999,999999,999999,999999,999999,0,0]
    else:
        qc_dict['BDS'] = [C_nobs,C_csAll,C_nSlp,C_nJmp,C_nGap,C_nPcs,C_mp1,C_mp2,C_cnr1,C_cnr2]

    # qc_dict['GPS'] = [G_nobs,G_csAll,G_nSlp,G_nJmp,G_nGap,G_nPcs,G_mp1,G_mp2,G_cnr1,G_cnr2]
    # qc_dict['GLO'] = [R_nobs,R_csAll,R_nSlp,R_nJmp,R_nGap,R_nPcs,R_mp1,R_mp2,R_cnr1,R_cnr2]
    # qc_dict['GAL'] = [E_nobs,E_csAll,E_nSlp,E_nJmp,E_nGap,E_nPcs,E_mp1,E_mp2,E_cnr1,E_cnr2]
    # qc_dict['BDS'] = [C_nobs,C_csAll,C_nSlp,C_nJmp,C_nGap,C_nPcs,C_mp1,C_mp2,C_cnr1,C_cnr2]

    return qc_dict


    
# Extract the QC information of multiple stations on a single day
def extract_qc_single_day(site_list: list[str], year: int, doy: int, work_root_path: str) -> pd.DataFrame:
    all_sites_data = []
    col_name = ['site_name',
                f"G_nobs_{year:04d}{doy:03d}",
                f"G_csAll_{year:04d}{doy:03d}",
                f"G_nSlp_{year:04d}{doy:03d}",
                f"G_nJmp_{year:04d}{doy:03d}",
                f"G_nGap_{year:04d}{doy:03d}",
                f"G_nPcs_{year:04d}{doy:03d}",
                f"G_mp1_{year:04d}{doy:03d}",
                f"G_mp2_{year:04d}{doy:03d}",
                f"G_cnr1_{year:04d}{doy:03d}",
                f"G_cnr2_{year:04d}{doy:03d}",
                f"R_nobs_{year:04d}{doy:03d}",
                f"R_csAll_{year:04d}{doy:03d}",
                f"R_nSlp_{year:04d}{doy:03d}",
                f"R_nJmp_{year:04d}{doy:03d}",
                f"R_nGap_{year:04d}{doy:03d}",
                f"R_nPcs_{year:04d}{doy:03d}",
                f"R_mp1_{year:04d}{doy:03d}",
                f"R_mp2_{year:04d}{doy:03d}",
                f"R_cnr1_{year:04d}{doy:03d}",
                f"R_cnr2_{year:04d}{doy:03d}",
                f"E_nobs_{year:04d}{doy:03d}",
                f"E_csAll_{year:04d}{doy:03d}",
                f"E_nSlp_{year:04d}{doy:03d}",
                f"E_nJmp_{year:04d}{doy:03d}",
                f"E_nGap_{year:04d}{doy:03d}",
                f"E_nPcs_{year:04d}{doy:03d}",
                f"E_mp1_{year:04d}{doy:03d}",
                f"E_mp2_{year:04d}{doy:03d}",
                f"E_cnr1_{year:04d}{doy:03d}",
                f"E_cnr2_{year:04d}{doy:03d}",
                f"C_nobs_{year:04d}{doy:03d}",
                f"C_csAll_{year:04d}{doy:03d}",
                f"C_nSlp_{year:04d}{doy:03d}",
                f"C_nJmp_{year:04d}{doy:03d}",
                f"C_nGap_{year:04d}{doy:03d}",
                f"C_nPcs_{year:04d}{doy:03d}",
                f"C_mp1_{year:04d}{doy:03d}",
                f"C_mp2_{year:04d}{doy:03d}",
                f"C_cnr1_{year:04d}{doy:03d}",
                f"C_cnr2_{year:04d}{doy:03d}",
                ]

    for site_name in site_list:
        one_site_dict = extract_qc_single_site(site_name, year, doy, work_root_path)
        # One line of data from a single station: [site_name] + GPS index + GLO index + GAL index + BDS index
        one_site_data = [site_name] + one_site_dict['GPS'] + one_site_dict['GLO'] + one_site_dict['GAL'] + one_site_dict['BDS']
        all_sites_data.append(one_site_data)

    
    return pd.DataFrame(all_sites_data, columns=col_name)


def extract_qc_multiple_days(site_list:list[str], year: int, doy_start: int, doy_end: int, work_root_path: str) -> pd.DataFrame:
    all_days_df = None
    for doy in range(doy_start, doy_end + 1):
        daily_df = extract_qc_single_day(site_list, year, doy, work_root_path)
        if all_days_df is None:
            all_days_df = daily_df
        else:
            all_days_df = pd.merge(all_days_df, daily_df, on='site_name', how='outer')

    return all_days_df



if __name__ == "__main__":
    site_name = 'JOZ2'
    site_list = [site_name]
    year = 2022
    doy = 91
    work_root_path = '/data1/jinweitong/work/choose_sta_work'
    # extract_qc_single_site(site_name, year, doy, work_root_path)
    my_pd_frame = extract_qc_single_day(site_list, year, doy, work_root_path)
    pass