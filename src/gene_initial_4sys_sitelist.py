# 从IGS给出的测站列表中(https://files.igs.org/pub/station/general/IGSNetwork.csv)
# 筛选出具有支持四系统且在分析时段内所有的sinex周解文件中都存在精密坐标的测站

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
    筛选支持四系统,且在分析时段内ReceiverDateInstalled要早于year,doy_start这样才能
    保证有数据
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
    生成可sinex文件路径
    参数：
    - sinex_root_path: sinex文件根目录
    - year: 年份
    - doy_start: 开始年积日
    - doy_end: 结束年积日
    返回：
    - sinex_file_list: sinex文件路径:sinex_root_path/sinex_file_name
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

    # 去除重复元素但保持顺序不变
    unique_sinex_file_list = list(dict.fromkeys(sinex_file_list))

    return unique_sinex_file_list
def delete_site_not_in_sinex(init_site_list:list[str], sinex_file_list:list[Path]) -> list[str]:
    """
    如果所有的sinex周解文件中都存在该测站的精密坐标,则返回4系统测站名称
    """
    site_list = init_site_list.copy()
    i_len = len(sinex_file_list)
    
    # 遍历所有站点
    sites_to_remove = []
    for site in site_list:
        site_found_in_all_files = True
        # 检查当前站点是否在所有SINEX文件中都存在
        for i, sinex_file in enumerate(sinex_file_list):
            # print(f"Finding {site} in {i+1}/{i_len} sinex_file: {sinex_file}\n")
            try:
                with open(sinex_file, 'r') as inp:
                    all_data = inp.readlines()
            except FileNotFoundError:
                print(f"Warning: SINEX file {sinex_file} not found\n")
                site_found_in_all_files = False
                break
            
            # 查找 SOLUTION/ESTIMATE 块的开始和结束位置
            s_index, e_index = None, None
            for index, line in enumerate(all_data):
                if line.startswith('+SOLUTION/ESTIMATE'):
                    s_index = index + 2  # 从下一行开始
                if line.startswith('-SOLUTION/ESTIMATE'):
                    e_index = index
                    break
            
            # 检查站点是否在 SOLUTION/ESTIMATE 块中
            site_found = False
            if s_index is not None and e_index is not None:
                # 在 SOLUTION/ESTIMATE 块中查找 STAX + 站点名的行
                for line in all_data[s_index:e_index]:
                    # 检查是否为STAX行且站点名匹配（通常格式为STAX XXXX）
                    if 'STAX' and site.upper() in line:
                        site_found = True
                        break
            
            if site_found:
                # 站点在当前文件中找到，继续检查下一个文件
                # print(f"{site} found in {sinex_file}\n")
                continue
            else:
                # 站点在当前文件中未找到，标记为不在所有文件中
                print(f"{site} is not in {sinex_file}, will be removed\n")
                site_found_in_all_files = False
                break
        
        # 如果站点不在所有文件中，则标记为删除
        if not site_found_in_all_files:
            sites_to_remove.append(site)
    
    # 删除标记的站点
    for site in sites_to_remove:
        site_list.remove(site)
    
    return site_list

def write_clock_type(site_list: list[str], out_file_path:str):
    """
    把选出来的测站的是氢原子钟的类型写到文件中
    """
    h_clk_flag = ['H-MASER','H_MASER','H2 MASER','HYDROGEN','UTC(','VCH-1008','EXTERNAL IMASER 3000','EXTERNAL MASER']
    with open('IGSNetwork.csv','r') as inp:
        lines = inp.readlines()
    
    with open(out_file_path, 'w') as outp:
        for site in site_list:
            for line in lines:
                if site.upper() == line.split(',')[0][0:4].upper():
                    # 判断原子钟类型
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
    # 命令行参数版本
    # ===== 设置命令行参数 =====
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--bindir', help='wget的路径')
    parser.add_argument('--sinex_root_path', help='sinex周解文件根目录')
    parser.add_argument('--year', type=int, help='年份')
    parser.add_argument('--doy_start', type=int, help='开始年积日')
    parser.add_argument('--doy_end', type=int, help='结束年积日')
    parser.add_argument('--out_file_path', help='输出站点列表文件完整路径')
    # ===========================

    args = parser.parse_args()
    this_file_main(bindir=args.bindir, 
                   sinex_root_path=args.sinex_root_path, 
                   year=args.year, doy_start=args.doy_start, doy_end=args.doy_end, 
                   out_file_path=args.out_file_path)


