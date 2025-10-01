# from the file provided by IGS(https://files.igs.org/pub/station/general/IGSNetwork.csv)
# Filter out the stations that support four systems and 
# have precise coordinates in all sinex weekly solution files during the analysis period.

import os
import platform
from time_convert import doy_mjd, mjd_gpswk,doy_ymd
from pathlib import Path
import pandas as pd

def download_metadata(bindir:str) -> None:
    if platform.system() == 'Windows':
        wget = os.path.join(bindir, 'wget.exe')
        wget += " -T 3 -t 10 -N -c "
    else:
        wget = os.path.join(bindir, 'wget')
        wget += " -T 3 -t 10 -N -c "
    metadata_addr = "https://files.igs.org/pub/station/general/IGSNetwork.csv"
    cmd_dl = wget + metadata_addr
    for value in range(1, 3):
    	os.system(cmd_dl)


def get_4sys_site_from_igs_metadata(igs_filename:str,
                                    year:int, 
                                    doy_start:int) -> list[str]:
    """
    support four systems
    """
    with open(igs_filename, 'r') as inp:
        alldata = inp.readlines()

    igs_site_name_4s = []

    for line in alldata:
        oneline = line.split(',')
        if oneline[0].startswith('#'):
            continue
        else:
            sat_system = oneline[8].split('+')
            if 'GPS' in sat_system and 'GLO' in sat_system and 'GAL' in sat_system and 'BDS' in sat_system:
                # rec_data_datestr = oneline[12]
                # # 日期格式: yyyy-mm-dd/yyyy-mm-ddThh:mmZ
                # rec_data_year = int(rec_data_datestr[0:4])
                # rec_data_month = int(rec_data_datestr[5:7])
                # rec_data_day = int(rec_data_datestr[8:10])
                # rec_data_year, rec_data_doy = doy_ymd(rec_data_year,rec_data_month,rec_data_day)
                # rec_data_mjd = doy_mjd(rec_data_year, rec_data_doy)
                # mjd = doy_mjd(year,doy_start)
                # if rec_data_mjd < mjd:
                #     # 接收到数据的日期早于分析时段
                #     igs_site_name_4s.append(oneline[0][0:4].upper())
                igs_site_name_4s.append(oneline[0][0:4].upper())

    return igs_site_name_4s

def generate_sinex_week_file_list(sinex_root_path:str, year:int, doy_start:int, doy_end:int) -> list[Path]:
    """
    return：
    - sinex_file_list: sinex file path:sinex_root_path/sinex_file_name
    """
    sinex_file_list = []

    for doy in range(doy_start, doy_end+1):
        mjd = doy_mjd(year, doy)
        gpsweek, gpsdow = mjd_gpswk(mjd)
        used_mjd = mjd_gpswk(gpsweek, 0)
        used_year, used_doy = doy_mjd(used_mjd)
        if gpsweek >= 2238:
            ### IGS0OPSSNX_20230010000_07D_07D_SOL.SNX
            sinex_file_name = f"IGS0OPSSNX_{used_year:04d}{used_doy:03d}0000_07D_07D_SOL.SNX"
        else:
            # igs22P2237.snx.Z
            sinex_file_name = f"igs{str(used_year)[-2:]}P{gpsweek:04d}.snx"
        sinex_file_list.append(Path(sinex_root_path,sinex_file_name))

    unique_sinex_file_list = list(dict.fromkeys(sinex_file_list))

    return unique_sinex_file_list
def delete_site_not_in_sinex(init_site_list:list[str], sinex_file_list:list[Path]) -> list[str]:
    """
    If the precise coordinates of the station exist in all sinex 
    weekly solution files, return the 4-system station name.
    """
    site_list = init_site_list.copy()
    i_len = len(sinex_file_list)
    
    sites_to_remove = []
    for site in site_list:
        site_found_in_all_files = True
        for i, sinex_file in enumerate(sinex_file_list):
            # print(f"Finding {site} in {i+1}/{i_len} sinex_file: {sinex_file}\n")
            try:
                with open(sinex_file, 'r') as inp:
                    all_data = inp.readlines()
            except FileNotFoundError:
                print(f"Warning: SINEX file {sinex_file} not found\n")
                site_found_in_all_files = False
                break
            
            # SOLUTION/ESTIMATE start and end indices
            s_index, e_index = None, None
            for index, line in enumerate(all_data):
                if line.startswith('+SOLUTION/ESTIMATE'):
                    s_index = index + 2  
                if line.startswith('-SOLUTION/ESTIMATE'):
                    e_index = index
                    break
            
            site_found = False
            if s_index is not None and e_index is not None:
                for line in all_data[s_index:e_index]:
                    if 'STAX' and site.upper() in line:
                        site_found = True
                        break
            
            if site_found:
                continue
            else:
                # The site was not found in the current file 
                # and is marked as not present in all files.
                print(f"{site} is not in {sinex_file}, will be removed\n")
                site_found_in_all_files = False
                break
        
        # If the site is not present in all files, mark it as deleted.
        if not site_found_in_all_files:
            sites_to_remove.append(site)
    
    # Delete the marked site
    for site in sites_to_remove:
        site_list.remove(site)
    
    return site_list

def write_clock_type(site_list: list[str], out_file_path:str):
    """
    Write the type of hydrogen atomic clock of the 
    selected observation stations into the file.
    """
    h_clk_flag = ['H-MASER','H_MASER','H2 MASER','HYDROGEN','UTC(','VCH-1008','EXTERNAL IMASER 3000','EXTERNAL MASER']
    with open('IGSNetwork.csv','r') as inp:
        lines = inp.readlines()
    
    with open(out_file_path, 'w') as outp:
        for site in site_list:
            for line in lines:
                if site.upper() == line.split(',')[0][0:4].upper():
                    clock_type = line.split(',')[21].upper()
                    if any(flag in clock_type for flag in h_clk_flag):
                        outp.write(site.upper()+'  '+clock_type+'\n')


def this_file_main(bindir:str, sinex_root_path:str, year:int, doy_start:int, doy_end:int, out_file_path:str):
    download_metadata(bindir)
    site_list = get_4sys_site_from_igs_metadata('IGSNetwork.csv',year,doy_start)
    sinex_file_list = generate_sinex_week_file_list(sinex_root_path, year, doy_start, doy_end)
    site_list = delete_site_not_in_sinex(site_list, sinex_file_list)
    
    from site_list import write_site_list
    write_site_list(site_list, out_file_path)
    write_clock_type(site_list,out_file_path+'_CLKTYPE')

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--bindir', help='The path of wget binary file')
    parser.add_argument('--sinex_root_path', help='Root directory of sinex weekly solution files')
    parser.add_argument('--year', type=int, help='year')
    parser.add_argument('--doy_start', type=int, help='start of DOY')
    parser.add_argument('--doy_end', type=int, help='end of DOY')
    parser.add_argument('--out_file_path', help='the full output path of the site list file')
    # ===========================

    args = parser.parse_args()
    this_file_main(bindir=args.bindir, 
                   sinex_root_path=args.sinex_root_path, 
                   year=args.year, doy_start=args.doy_start, doy_end=args.doy_end, 
                   out_file_path=args.out_file_path)


