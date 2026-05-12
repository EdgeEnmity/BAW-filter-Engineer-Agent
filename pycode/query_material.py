"""
材料参数查询工具

提供BAW谐振器材料参数的查询接口。
材料库位置: D:/Users/jinhao.dai/Desktop/OC/lib/material_library.xlsx
"""

import pandas as pd
import argparse
from typing import Union, List, Dict, Optional

# 材料库默认路径
DEFAULT_LIB_PATH = r"D:\Users\jinhao.dai\桌面\OC\lib\material_library.xlsx"


def load_material_library(lib_path: str = DEFAULT_LIB_PATH) -> pd.ExcelFile:
    """加载材料参数库"""
    return pd.ExcelFile(lib_path)


def query_material(
    material_name: Optional[str] = None,
    band: Optional[str] = None,
    sc_doping: Optional[Union[int, float]] = None,
    lib_path: str = DEFAULT_LIB_PATH
) -> Union[Dict, pd.DataFrame, None]:
    """
    查询材料参数
    
    参数:
        material_name: 材料名称 ('AlN', 'Moly', 'SiO2'等)
        band: 频段 ('MHB' 或 'UHB')
        sc_doping: Sc掺杂比例 (0, 9.5, 20, 30, 36)
        lib_path: 材料库文件路径
    
    返回:
        单个材料字典或多个材料的DataFrame
    """
    xl_file = pd.ExcelFile(lib_path)
    
    # 确定查询哪个sheet
    if band:
        sheet_name = 'MHB_<3GHz' if band == 'MHB' else 'UHB_>3GHz'
    else:
        # 默认查询MHB
        sheet_name = 'MHB_<3GHz'
    
    df = pd.read_excel(xl_file, sheet_name=sheet_name)
    
    # 应用筛选条件
    if material_name:
        df = df[df['Material'] == material_name]
    
    if sc_doping is not None and material_name == 'AlN':
        df = df[df['Sc_doping'] == sc_doping]
    
    if len(df) == 0:
        return None
    
    # 如果只有一条记录，返回字典格式
    if len(df) == 1:
        result = df.iloc[0].to_dict()
        result['Band'] = 'MHB' if 'MHB' in sheet_name else 'UHB'
        return result
    
    # 多条记录返回DataFrame
    return df


def get_all_materials(band: Optional[str] = None, lib_path: str = DEFAULT_LIB_PATH) -> pd.DataFrame:
    """
    获取所有可用材料列表
    
    参数:
        band: 频段 ('MHB' 或 'UHB' 或 None表示全部)
        lib_path: 材料库文件路径
    
    返回:
        包含所有材料的DataFrame
    """
    xl_file = pd.ExcelFile(lib_path)
    
    if band == 'MHB':
        return pd.read_excel(xl_file, sheet_name='MHB_<3GHz')
    elif band == 'UHB':
        return pd.read_excel(xl_file, sheet_name='UHB_>3GHz')
    else:
        # 合并两个频段
        mhb = pd.read_excel(xl_file, sheet_name='MHB_<3GHz')
        uhb = pd.read_excel(xl_file, sheet_name='UHB_>3GHz')
        mhb['Band'] = 'MHB'
        uhb['Band'] = 'UHB'
        return pd.concat([mhb, uhb], ignore_index=True)


def get_aln_variants(band: str, lib_path: str = DEFAULT_LIB_PATH) -> pd.DataFrame:
    """
    获取AlN的所有Sc掺杂变体
    
    参数:
        band: 频段 ('MHB' 或 'UHB')
        lib_path: 材料库文件路径
    
    返回:
        包含所有AlN变体的DataFrame
    """
    return query_material(material_name='AlN', band=band, lib_path=lib_path)


def format_material_output(material: Dict) -> str:
    """格式化材料参数输出"""
    lines = [
        f"材料: {material.get('Material', 'N/A')}",
        f"频段: {material.get('Band', 'N/A')}",
    ]
    
    if material.get('Sc_doping') != '/':
        lines.append(f"Sc掺杂: {material.get('Sc_doping', 'N/A')}%")
    
    lines.extend([
        f"密度 (rho): {material.get('rho_kg_m3', 'N/A')} kg/m³",
        f"弹性刚度 (c33): {material.get('c33_Pa', 'N/A'):.3e} Pa",
    ])
    
    if material.get('e33_C_m2') not in ['/', None]:
        lines.append(f"压电常数 (e33): {material.get('e33_C_m2', 'N/A')} C/m²")
    
    if material.get('eps33_F_m') not in ['/', None, 0]:
        lines.append(f"介电常数 (eps33): {material.get('eps33_F_m', 'N/A'):.3e} F/m")
    
    lines.extend([
        f"机械Q值: {material.get('Q_Mech', 'N/A')}",
    ])
    
    if material.get('Q_Die') not in ['/', None]:
        lines.append(f"介电Q值: {material.get('Q_Die', 'N/A')}")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='材料参数查询工具')
    parser.add_argument('--material', '-m', help='材料名称 (AlN, Moly, SiO2)')
    parser.add_argument('--band', '-b', choices=['MHB', 'UHB'], help='频段 (MHB 或 UHB)')
    parser.add_argument('--sc', type=float, help='Sc掺杂比例 (0, 9.5, 20, 30, 36)')
    parser.add_argument('--list-all', action='store_true', help='列出所有材料')
    parser.add_argument('--all-sc', action='store_true', help='列出AlN所有Sc变体')
    parser.add_argument('--lib', default=DEFAULT_LIB_PATH, help='材料库路径')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("BAW材料参数查询")
    print("=" * 60)
    
    if args.list_all:
        # 列出所有材料
        band = args.band if args.band else 'MHB'
        materials = get_all_materials(band=band, lib_path=args.lib)
        print(f"\n{band}频段所有材料:")
        print(materials.to_string(index=False))
    
    elif args.all_sc and args.material == 'AlN':
        # 列出AlN所有Sc变体
        band = args.band if args.band else 'MHB'
        variants = get_aln_variants(band=band, lib_path=args.lib)
        print(f"\nAlN {band}频段所有Sc掺杂变体:")
        print(variants.to_string(index=False))
    
    else:
        # 查询特定材料
        result = query_material(
            material_name=args.material,
            band=args.band,
            sc_doping=args.sc,
            lib_path=args.lib
        )
        
        if result is None:
            print(f"\n未找到匹配的材料")
            return 1
        
        if isinstance(result, dict):
            print(f"\n查询结果:")
            print(format_material_output(result))
        else:
            print(f"\n查询结果 ({len(result)}条记录):")
            print(result.to_string(index=False))
    
    print("\n" + "=" * 60)
    return 0


if __name__ == '__main__':
    exit(main())
