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
    生成rinex文件名,包括obs和广播星历
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
    把 xml_path 里的 <rinexo> 与 <rinexn> 文本内容替换为指定值。
    默认先备份原文件为 *.bak；若想写到新文件，请自行修改 out_path。
    """
    xml_path = Path(xml_path)
    
    # 检查文件是否存在
    if not xml_path.exists():
        # 如果存在备份文件，则从备份文件恢复
        backup_path = xml_path.with_suffix(xml_path.suffix + '.bak')
        if backup_path.exists():
            import shutil
            shutil.copy(backup_path, xml_path)
        else:
            raise FileNotFoundError(f"找不到XML文件: {xml_path} 且无备份文件可用")
    
    # 检查文件是否为空
    if xml_path.stat().st_size == 0:
        raise ValueError(f"XML文件为空: {xml_path}")

    # 1. 读文件
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # 2. 定位并替换
    inp = root.find('inp')
    if inp is None:
        raise ValueError("找不到 <inp> 节点")

    rinexo_node = inp.find('rinexo')
    rinexn_node = inp.find('rinexn')

    if rinexo_node is None or rinexn_node is None:
        raise ValueError("找不到 <rinexo> 或 <rinexn> 节点")

    rinexo_node.text = new_rinexo
    rinexn_node.text = new_rinexn

    # 3. 备份、写回
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
    执行单站单日 anibus分析
    """
    rinex_o_content, rinex_n_content = gene_rinex_code(site_name,year,doy,data_root_path)
    replace_rinex(xml_file, str(rinex_o_content), str(rinex_n_content))

    # 执行外部命令
    # 切换到work_root_path目录下
    anubis_work_path = Path(work_root_path,'work'+str(year).zfill(4)+str(doy).zfill(3),'anubis')
    if not anubis_work_path.exists():  # 如果目录不存在，则创建
        os.makedirs(anubis_work_path)
    os.chdir(anubis_work_path)
    # subprocess.run([anubis_bin_pathandname, '-x', xml_file], check=True)
    # 把subprocess替换成os.system
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
    执行多站单日 anibus分析
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
    执行多站多日 anibus分析
    """
    from site_list import read_list
    sitelist = read_list(site_list_file)

    for doy in range(doy_start, doy_end+1):
        exec_anibus_multi_sites(xml_file, anubis_bin_pathandname, sitelist, year, doy, data_root_path, work_root_path)


if __name__ == '__main__':
    # ===== 设置命令行参数 =====
    import argparse
    parser = argparse.ArgumentParser()

    parser.add_argument('--xml_file', help='xml文件路径')
    parser.add_argument('--anubis_bin', help='anubis二进制文件路径')
    parser.add_argument('--site_list_file', help='站点列表文件路径')
    parser.add_argument('--year', type=int, help='年份')
    parser.add_argument('--doy_start', type=int, help='开始年积日')
    parser.add_argument('--doy_end', type=int, help='结束年积日')
    parser.add_argument('--data_root_path', help='数据根目录路径')
    parser.add_argument('--work_root_path', help='工作根目录路径') 
    # ===========================

    args = parser.parse_args()
    exec_anibus_multi_days(args.xml_file, args.anubis_bin, args.site_list_file, args.year, args.doy_start, args.doy_end, args.data_root_path, args.work_root_path)