# baw-pdk 技能文档

**功能:** BAW工艺设计套件,简化谐振器设计

---

## 设计概念

PDK封装Mason模型复杂度:
- **固定层叠:** PS/TE/PZ/BE/SD
- **调谐参数:** ML厚度、面积
- **输出:** S1P文件

---

## 核心功能

1. 单次仿真
2. 频率匹配(自动查找ML)
3. 批量仿真
4. PDK库生成

---

## Python API 使用

```python
from skills.baw-pdk.scripts.baw_pdk import BAWPDK

pdk = BAWPDK()

# 单次仿真
pdk.configure(area_um2=10000, ml_thickness_nm=100)
result = pdk.simulate(output_file='resonator.s1p')

# 为目标频率查找ML
result = pdk.find_ml_for_frequency(
    target_fs_hz=2.5e9,
    output_file='target.s1p'
)

# 批量扫描
results = pdk.batch_simulate(
    ml_thicknesses=[0, 50, 100, 150, 200],
    areas=[10000, 20000],
    output_dir='batch/'
)

# 生成PDK库
library = pdk.generate_pdk_library(
    fs_range_ghz=(2.0, 2.8),
    fs_step_mhz=50,
    output_dir='library/'
)
```

---

## 命令行使用

```bash
# 单次仿真
python baw_pdk.py simulate --area 10000 --ml 100 -o out.s1p

# 查找ML
python baw_pdk.py find-ml --target-fs 2.5 -o out.s1p

# 批量仿真
python baw_pdk.py batch --ml-list "[0,50,100]" -d out/

# 生成库
python baw_pdk.py library --fs-start 2.0 --fs-stop 2.8 -d lib/
```

---

## PDK参数

| 参数 | 默认值 | 描述 |
|------|--------|------|
| Area | 10000 um² | 谐振器面积 |
| ML Material | Mo | 质量加载材料 |
| ML Thickness | 0 nm | 0=无ML |

---

## 频率调谐原理

**Mass Loading增加电极质量,降低谐振频率:**

- ML厚度 ↑ → 质量 ↑ → 谐振频率 ↓
- 典型范围: 0-500nm ML → ~200-400MHz频率偏移

---

## 输出文件

- `*.s1p`: Touchstone文件
- `batch_summary.csv`: 批量结果
- `pdk_library.csv`: 库汇总

---

## 依赖

- baw-mason-s1p skill
- numpy, pandas, matplotlib
