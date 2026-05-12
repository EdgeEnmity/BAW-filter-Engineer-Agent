# baw-mason-s1p 技能文档

**功能:** 使用1D Mason模型生成BAW谐振器S1P文件

---

## 标准层命名规范

| 层 | 全称 | 端子 | 功能 |
|----|------|------|------|
| PS | Passivation/Protection Structure | 0(GND) | 顶部钝化层 |
| TE | Top Electrode | 2(TOP) | 上电极 |
| PZ | PieZoelectric | 0(GND) | 压电层 |
| BE | Bottom Electrode | 1(BOT) | 下电极 |
| SD | Seeding/Substrate Device | 0(GND) | 底部种子层 |

---

## 内置模板

### standard_fbar (默认)
```
PS(AlN,100nm) / TE(Mo,240nm) / PZ(AlN,1000nm) / BE(Mo,240nm) / SD(AlN,25nm)
```

### minimal_fbar
```
TE(Mo,240nm) / PZ(AlN,1000nm) / BE(Mo,240nm)
```

### fbar_with_ru
```
PS(AlN,100nm) / TE(Ru,200nm) / PZ(AlN,1000nm) / BE(Ru,200nm) / SD(AlN,25nm)
```

### smr_basic
带布拉格反射镜 (W/SiO2层对)

---

## Python API 使用

```python
from skills.baw-mason-s1p.scripts.mason_s1p import MasonS1PGenerator

gen = MasonS1PGenerator()

# 方法1: 使用模板
gen.use_template('standard_fbar')

# 方法2: 模板+层覆盖
gen.use_template('standard_fbar', layer_overrides={
    'PZ': {'thk_nm': 1200},
    'TE': {'material': 'Ru'}
})

# 方法3: 先加载模板再修改
gen.use_template('standard_fbar')
gen.override_layers({
    'PZ': {'thk_nm': 1100, 'material': 'AlN'}
})

# 运行仿真
results = gen.simulate(
    area_um2=10000,
    f_start=1e9,
    f_stop=3e9,
    output_file='resonator.s1p'
)

print(f"fr: {results['fr']/1e9:.3f} GHz")
print(f"kt2: {results['kt2']:.2%}")
```

---

## 命令行使用

```bash
# 使用标准模板
python mason_s1p.py --template standard_fbar --area 10000 -o resonator.s1p

# 模板+覆盖(JSON格式)
python mason_s1p.py --template standard_fbar \
    --override '{"PZ":{"thk_nm":1200}}' \
    --area 10000 -o resonator.s1p

# 自定义CSV材料/层叠
python mason_s1p.py --material Material1.csv --stack Stack1.csv \
    --area 10000 -o resonator.s1p
```

---

## 层覆盖格式

```python
{
    'LayerName': {
        'thk_nm': <厚度>,           # 层厚度(nm)
        'material': '<材料名>',     # 材料名称
        'q_mech': <机械Q>,          # 可选: 机械品质因数
        'q_die': <介电Q>            # 可选: 介电品质因数
    }
}
```

**层名别名:**
- 'TOP', 'ELECTRODE_TOP' -> 'TE'
- 'BOTTOM', 'ELECTRODE_BOTTOM' -> 'BE'
- 'PIEZO', 'PZL' -> 'PZ'
- 'SEED', 'SUBSTRATE' -> 'SD'

---

## 使用示例

### 厚度扫描
```python
for pz_thk in [900, 1000, 1100, 1200]:
    gen = MasonS1PGenerator()
    gen.use_template('standard_fbar', {'PZ': {'thk_nm': pz_thk}})
    results = gen.simulate(area_um2=10000, 
                          output_file=f'res_{pz_thk}nm.s1p')
```

### 材料对比
```python
for electrode in ['Mo', 'Ru', 'W']:
    gen = MasonS1PGenerator()
    gen.use_template('standard_fbar', {
        'TE': {'material': electrode},
        'BE': {'material': electrode}
    })
    results = gen.simulate(area_um2=10000)
```

---

## 输出内容

- **S1P文件**: Touchstone格式S参数
- **图表**: S11幅度/相位, 阻抗曲线
- **参数**: fr, fa, kt2, C0

---

## 依赖

- numpy
- pandas
- matplotlib
- scikit-rf (可选,用于S1P导出)

---

## 材料库

默认材料:
- **AlN**: 氮化铝(压电材料)
- **Mo**: 钼(电极)
- **Ru**: 钌(电极)
- **W**: 钨(反射镜/电极)
- **SiO2**: 二氧化硅(温度补偿)
- **Ti**: 钛(粘附层)
