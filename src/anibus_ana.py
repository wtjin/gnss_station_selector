import xml.etree.ElementTree as ET
from pathlib import Path
import subprocess
import os

def gene_rinex_code(site_name: str,
                    year: int,
                    doy: int,
                    data_root_path: str,
                ) -> tuple[str, str]:
    '''
    Generate RINEX file names, including observation data and broadcast ephemeris
    '''
    cyear = str(year).zfill(4)
    cdoy = str(doy).zfill(3)
    cyy = cyear[-2:]
    obs_file_name = site_name.strip().lower() + cdoy + '0.' + cyy + 'o'
    nav_file_name = 'brdm'+cdoy+'0.'+cyy + 'p'

    rinex_o_content = Path(data_root_path,'obs','daily',cyear,cdoy,obs_file_name)
    rinex_n_content = Path(data_root_path,'nav','daily',nav_file_name)

    return rinex_o_content, rinex_n_content

def replace_rinex(xml_path: str,
                  new_rinexo: str,
                  new_rinexn: str,
                  *, backup: bool = True) -> None:
    """
    Replace the text content of <rinexo> and <rinexn> in xml_path with the specified values.
    By default, the original file is backed up as *.bak first; 
    if someone wants to write to a new file, please modify the out_path.
    """
    xml_path = Path(xml_path)
    
    if not xml_path.exists():
        backup_path = xml_path.with_suffix(xml_path.suffix + '.bak')
        if backup_path.exists():
            import shutil
            shutil.copy(backup_path, xml_path)
        else:
            raise FileNotFoundError(f"cannot find XML file: {xml_path} And there are no backup files available.")
    
    if xml_path.stat().st_size == 0:
        raise ValueError(f"XML file is empty: {xml_path}")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    inp = root.find('inp')
    if inp is None:
        raise ValueError("Cannot find the <inp> node")

    rinexo_node = inp.find('rinexo')
    rinexn_node = inp.find('rinexn')

    if rinexo_node is None or rinexn_node is None:
        raise ValueError("Cannot find <rinexo> or <rinexn> nodes")

    rinexo_node.text = new_rinexo
    rinexn_node.text = new_rinexn

    if backup:
        xml_path.replace(xml_path.with_suffix(xml_path.suffix + '.bak'))

    tree.write(xml_path, encoding='utf-8', xml_declaration=True)

def exec_anibus_single_site(xml_file: str,
                            anubis_bin_pathandname: str,
                            site_name: str,
                            year: int,
                            doy: int,
                            data_root_path: str,
                            work_root_path: str,
                            ) -> None:
    """
    Perform a single-station, single-day analysis using anubis
    """
    rinex_o_content, rinex_n_content = gene_rinex_code(site_name,year,doy,data_root_path)
    replace_rinex(xml_file, str(rinex_o_content), str(rinex_n_content))

    
    anubis_work_path = Path(work_root_path,'work'+str(year).zfill(4)+str(doy).zfill(3),'anubis')
    if not anubis_work_path.exists():
        os.makedirs(anubis_work_path)
    os.chdir(anubis_work_path)
    os.system(f'{anubis_bin_pathandname} -x {xml_file}')

def exec_anibus_multi_sites(xml_file: str,
                            anubis_bin_pathandname: str,
                            site_list: list[str],
                            year: int,
                            doy: int,
                            data_root_path: str,
                            work_root_path: str,
                            ) -> None:
    """
    Perform a multiple-stations, single-day analysis using anubis
    """
    for site_name in site_list:
        exec_anibus_single_site(xml_file, anubis_bin_pathandname, site_name, year, doy, data_root_path, work_root_path)

def exec_anibus_multi_days(xml_file: str,
                           anubis_bin_pathandname: str,
                           site_list_file: str,
                           year: int,
                           doy_start: int,
                           doy_end: int,
                           data_root_path: str,
                           work_root_path: str,
                           ) -> None:

    """
    Perform a multiple-stations, mutiple-days analysis using anubis
    """
    from site_list import read_list
    sitelist = read_list(site_list_file)

    for doy in range(doy_start, doy_end+1):
        exec_anibus_multi_sites(xml_file, anubis_bin_pathandname, sitelist, year, doy, data_root_path, work_root_path)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--xml_file', help='XML file path')
    parser.add_argument('--anubis_bin', help='Path of the anubis executable program')
    parser.add_argument('--site_list_file', help='Path of the site list file')
    parser.add_argument('--year', type=int, help='year')
    parser.add_argument('--doy_start', type=int, help='start of DOY')
    parser.add_argument('--doy_end', type=int, help='end of DOY')
    parser.add_argument('--data_root_path', help='Data root directory path')
    parser.add_argument('--work_root_path', help='Working root directory path')
    # ===========================

    args = parser.parse_args()
    exec_anibus_multi_days(args.xml_file, args.anubis_bin, args.site_list_file, args.year, args.doy_start, args.doy_end, args.data_root_path, args.work_root_path)