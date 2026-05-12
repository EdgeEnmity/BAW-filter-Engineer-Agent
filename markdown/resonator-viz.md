# resonator-viz 技能文档

**功能:** 谐振器性能可视化分析

---

## 支持的输入格式

### 1. Touchstone S1P文件
```python
analyzer.load_s1p('measurement.s1p')
```

### 2. Excel文件
```python
analyzer.load_excel('simulation.xlsx',
                   freq_column=0,
                   s11_real_col=1,
                   s11_imag_col=2,
                   freq_unit='GHz')
```

### 3. CSV文件
```python
analyzer.load_csv('data.csv', freq_unit='MHz')
```

### 4. 自动检测
```python
analyzer.load_data('file.s1p')  # 自动识别格式
```

### 5. 直接数组
```python
analyzer.set_data(frequency_array, s11_complex_array)
```

---

## 计算参数

| 参数 | 公式 | 描述 |
|------|------|------|
| 群延迟 | τg = -dφ/dω | 信号传播延迟 |
| Bode Q | Q = 2πf·τg·\|S11\|/(1-\|S11\|²) | 品质因数 |
| S11 (dB) | 20·log10(\|S11\|) | 反射系数 |
| Z11 (dB) | 20·log10(\|Z11\|) | 阻抗 |
| Y11 (dB) | 20·log10(\|Y11\|) | 导纳 |
| kt² | (π/2)(fr/fa)/tan(π/2·fr/fa) | 机电耦合系数 |

---

## 输出图表

### Standard (默认, 4图)
1. |S11| (dB) - 反射系数
2. |Z11| (Ω) - 阻抗幅度
3. Re(Y11) (dB) - 导纳实部
4. Q因子 (Bode)

### Simple (2图): S11 + Q
### Full (6图): Standard + 群延迟 + Smith圆图

---

## Python API 使用

```python
from scripts.resonator_viz import ResonatorAnalyzer

# 创建分析器
analyzer = ResonatorAnalyzer()

# 加载数据
analyzer.load_s1p('resonator.s1p')

# 获取参数
params = analyzer.get_resonant_params()
print(f"fr = {params['fr']/1e9:.3f} GHz")
print(f"kt² = {params['kt2']:.2%}")
print(f"Q = {params['q_max']:.0f}")

# 生成图表
analyzer.plot(plot_type='standard', save_path='analysis.png')

# 导出结果
analyzer.save_results('results.csv')
```

---

## 命令行使用

```bash
# S1P文件
python resonator_viz.py -i measurement.s1p -o plot.png

# Excel自定义列
python resonator_viz.py -i data.xlsx --freq-unit GHz \
    --freq-col 0 --real-col 1 --imag-col 2

# 完整分析并导出
python resonator_viz.py -i result.s1p --plot-type full \
    -o plot.png -e results.csv

# 仅保存,不显示
python resonator_viz.py -i data.s1p -o plot.png --no-show
```

---

## 谐振器参数

`get_resonant_params()` 返回:

```python
{
    'fr': resonant_frequency,      # Hz
    'fa': anti_resonant_frequency, # Hz
    'kt2': coupling_coefficient,   # 0-1
    'bandwidth': fa - fr,          # Hz
    'q_max': maximum_Q,
    'q_at_fr': Q_at_resonance,
    's11_min': minimum_S11_magnitude,
    's11_max': maximum_S11_magnitude
}
```

---

## 使用示例

### 分析VNA测量
```python
analyzer = ResonatorAnalyzer()
analyzer.load_s1p('vna_measurement.s1p')
params = analyzer.get_resonant_params()

print(f"谐振频率: {params['fr']/1e9:.3f} GHz")
print(f"Q因子: {params['q_max']:.0f}")
print(f"耦合系数: {params['kt2']:.2%}")

analyzer.plot(plot_type='full', save_path='vna_analysis.png')
```

### 批量处理
```python
import glob

for s1p_file in glob.glob('*.s1p'):
    analyzer = ResonatorAnalyzer()
    analyzer.load_s1p(s1p_file)
    params = analyzer.get_resonant_params()
    
    print(f"{s1p_file}: fr={params['fr']/1e9:.3f}GHz, "
          f"Q={params['q_max']:.0f}")
    
    analyzer.plot(save_path=f"{s1p_file.replace('.s1p', '.png')}",
                 show=False)
```

---

## 依赖

- numpy
- pandas
- matplotlib
- scikit-rf (可选,用于S1P和Smith圆图)
- scipy (可选,用于插值)
