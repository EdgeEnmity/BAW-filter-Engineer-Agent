# baw-material-query 技能文档

**功能:** 查询BAW谐振器材料参数库

---

## 材料库位置

```
D:\Users\jinhao.dai\桌面\OC\lib\material_library.xlsx
```

---

## 库结构

4个工作表:
1. **MHB_<3GHz** - 中高频段材料参数 (<3GHz)
2. **UHB_>3GHz** - 超高频段材料参数 (>3GHz)
3. **材料对比** - MHB vs UHB 对比
4. **使用说明** - 参数文档

---

## 可用材料

| 材料 | 描述 | Sc掺杂选项 |
|------|------|-----------|
| Moly | 钼,电极材料 | / |
| SiO2 | 二氧化硅,温度补偿 | / |
| AlN | 氮化铝,压电材料 | 0%, 9.5%, 20% |
| AlScN | 掺钪AlN (仅UHB) | 30%, 36% |

---

## 参数定义

| 参数 | 单位 | 描述 |
|------|------|------|
| rho | kg/m³ | 密度 |
| c33 | Pa | 弹性刚度常数 |
| e33 | C/m² | 压电应力常数 |
| eps33 | F/m | 绝对介电常数 |
| Q_Mech | - | 机械品质因数 |
| Q_Die | - | 介电品质因数 |
| Tempco_c33 | ppm/°C | c33温度系数 |

---

## Python API 使用

```python
from scripts.query_material import query_material, get_all_materials

# 查询特定材料
material = query_material(
    material_name='AlN',
    band='MHB',
    sc_doping=0
)

# 获取所有可用材料
all_materials = get_all_materials()

# 获取某频段所有AlN变体
aln_variants = query_material(
    material_name='AlN', 
    band='UHB'
)
```

---

## 命令行使用

```bash
# 查询AlN MHB参数
python scripts/query_material.py --material AlN --band MHB --sc 0

# 列出所有MHB材料
python scripts/query_material.py --band MHB --list-all

# 查询所有AlN Sc变体
python scripts/query_material.py --material AlN --band UHB --all-sc
```

---

## 返回格式

```python
{
    'Material': 'AlN',
    'Sc_doping': 0,
    'Band': 'MHB',
    'rho_kg_m3': 3342.99664,
    'c33_Pa': 389379000000.0,
    'e33_C_m2': 1.463568,
    'eps33_F_m': 8.8775e-11,
    'Q_Mech': 3713,
    'Q_Die': 527
}
```

---

## 使用场景

1. **设计FBAR谐振器**: 查询AlN MHB参数进行频率计算
2. **温度补偿设计**: 查询SiO2参数与AlN配对
3. **高频滤波器设计**: 查询AlN UHB或高Sc掺杂AlScN
4. **电极选择**: 查询Moly参数评估声学损耗

---

## 注意事项

- Sc掺杂仅适用于AlN材料
- MHB和UHB的AlN参数不同,根据目标频率选择
- SiO2的eps33为0(非压电材料)
