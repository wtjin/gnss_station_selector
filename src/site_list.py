'''
Functions related to the site list
'''
import pandas as pd
from pathlib import Path
import numpy as np


def read_list(site_list_file: str) -> list[str]:
    """
    Read the site list file
    """
    with open(site_list_file, 'r') as inp:
        site_list = inp.readlines()
    
    site_list = [site.strip() for site in site_list if not site.startswith('#')]

    return site_list

def read_coord_from_rinexo(oFile:str)->list[float]:
    """
    Read approximate coordinate information from the RINEXO file
    """
    with open(oFile, 'r') as inp:
        all_data = inp.readlines()
    
    for data in all_data:
        if len(data) < 60:
            continue
        elif data[60:80].strip().upper() == 'APPROX POSITION XYZ':
            coord = data[0:60].split()
            coord = [float(x) for x in coord]
            return coord

def scan_rinexo_coord(data_root_path: str, site_list: list[str], year: int, doy: int)->pd.DataFrame:
    yy = str(year)[2:]
    doy_str = str(doy).zfill(3)

    df = pd.DataFrame(columns=['site_name', 'x', 'y', 'z'])
    for site in site_list:
        oFileName = f"{site.lower()}{doy_str}0.{yy}o"
        oFile = Path(data_root_path,'obs','daily',str(year),doy_str,oFileName)
        if not oFile.exists():
            continue
        coord = read_coord_from_rinexo(oFile)
        new_row = pd.DataFrame([{'site_name': site, 'x': coord[0], 'y': coord[1], 'z': coord[2]}])
        df = pd.concat([df, new_row], ignore_index=True)

    # df.set_index('site_name', inplace=True)
    return df

def write_site_list(site_list: list[str], out_path: str) -> None:
    """
    Write the site list to a file
    """
    with open(out_path, 'w') as outp:
        for site in site_list:
            outp.write(' ' + site.strip() + '\n')

def write_site_list_coord(df: pd.DataFrame, out_path: str, coord_col: list[str]=['latitude', 'longitude']) -> None:
    """
    Write the site list and coordinates into the file
    Latitude and longitude are written by default for drawing distribution maps.
    """
    coord_array = df[coord_col].values
    i_len = len(coord_col)
    with open(out_path, 'w') as outp:
        for coord in coord_array:
            coord_str = " ".join([f"{coord[i]:.4f}" for i in range(i_len)])
            outp.write(coord_str + "\n")            


