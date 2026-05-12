# HETT-{任务编号} | {任务名称}

## 1. 任务元信息 (Task Meta)
| 字段 | 内容 |
|------|------|
| **任务编号** | HETT-001 |
| **任务领域** | □ PDK / □ Layout / □ Data Analysis / □ Filter Design / □ 跨域集成 |
| **优先级** | P0-P3 |
| **预估工时** | {人类审阅时间} + {Agent执行时间} |
| **上游依赖** | HETT-{xxx} (必须完成并验收通过) |
| **阻塞风险** | {列出可能阻塞Agent的已知问题} |
| **人类Owner** | {你的名字/角色} |
| **Agent角色** | □ 代码生成 / □ 架构重构 / □ 数据分析 / □ 文档生成 / □ 验证审查 |

---

## 2. 目标与边界 (Goal & Guardrails)

### 2.1 核心目标 (One-Sentence Goal)
用一句话说明这个任务要交付什么，**不要**描述过程。
&gt; 示例：生成支持 AW=1,2,3 且 OT=1,2,3 的 FBAR Unit Cell DoE Table，并输出 L10/L20/L25/L50 的 GDS 阵列。

### 2.2 成功标准 (Success Criteria)
- [ ] 标准1：{可量化、可自动验证的条件}
- [ ] 标准2：{边界情况的处理要求}
- [ ] 标准3：{性能/精度指标}

### 2.3 硬边界 (Hard Constraints) —— **Agent绝对不可突破**
1. **几何约束**：{例如：L30/L70/L80 不得包含谐振区和signal走线，但保留signal pad}
2. **数据契约**：{例如：DoE Table 的列名必须与 schema v2.1 一致}
3. **接口冻结**：{例如：PCell 的 Python API 签名不得改变，新增参数必须有默认值}
4. **工具链锁定**：{例如：GDS 输出必须用 gdstk，禁止引入 gdspy}
5. **安全/合规**：{例如：不得上传 wafer 实测数据到外部 API}

### 2.4 软边界 (Soft Guidelines) —— **Agent可偏离但需报告**
- {例如：代码风格优先遵循 PEP8，但允许为了可读性适当妥协}
- {例如：圆角逼近默认用 16 边形，但可根据面积大小自适应调整}

---

## 3. 输入上下文 (Input Context)

### 3.1 仓库位置 (Source of Truth)
&gt; **Harness 原则：仓库里没有的，就等于不存在。**

| 资源类型 | 仓库路径 | 版本/Commit | 说明 |
|---------|---------|------------|------|
| 上游代码 | `src/pcell/fbar_unit.py` | `a1b2c3d` | 当前验证通过的 L10-L50 生成逻辑 |
| 规格文档 | `docs/spec/doe_schema_v2.md` | `HEAD` | DoE Table 的列定义与约束 |
| 参考数据 | `data/ref/measured_s11.csv` | `HEAD` | 用于验证的实测 S 参数 |
| 设计规则 | `docs/drc/fbar_drc_rules.yaml` | `HEAD` | 当前生效的 DRC 规则集 |
| 历史任务 | `harness/HETT-xxx.md` | `HEAD` | 上游依赖任务的验收报告 |

### 3.2 环境状态 (Environment Snapshot)
- **Python 版本**：3.x
- **关键依赖版本**：`gdstk==0.x`, `numpy==1.x`, `pandas==2.x`
- **ADS 版本**：{你的 Keysight ADS 版本}
- **已知环境限制**：{例如：本地无法安装 gdspy，必须用纯 Python 方案}

### 3.3 背景知识 (Domain Context)
&gt; 用 3-5 句话给 Agent 建立领域认知，避免它"猜"你的意图。
- {例如：FBAR 的 L10 是空腔层，L20 是底电极，L25 是 OT 环，L50 是顶电极...}
- {例如：释放区域按面积分级放置，大面积用 5 个释放圆，小面积用 3 个...}
- {例如：Signal pad 和 Ground pad 之间必须保持电气隔离...}

---

## 4. 执行规范 (Execution Spec)

### 4.1 分阶段交付 (Phased Delivery)
&gt; 禁止一次性输出全部代码。按阶段交付，每阶段必须人类验收后才能进入下一阶段。

| 阶段 | 交付物 | 验收标准 | 预计轮次 |
|------|--------|---------|---------|
| Phase 1 | {例如：DoE Table 生成逻辑} | {例如：输出 3 组参数组合，人工检查几何合理性} | 2-3 轮 |
| Phase 2 | {例如：L50 Signal 走线梯形生成} | {例如：KLayout 打开 GDS 确认无短路} | 1-2 轮 |
| Phase 3 | {例如：完整 GDS 阵列输出} | {例如：5 个面积 × 3 个 AW 全部通过 DRC} | 1 轮 |

### 4.2 代码组织要求 (Code Organization)
- **新增文件路径**：`src/{模块}/{文件名}.py`
- **单元测试路径**：`tests/{模块}/test_{文件名}.py`
- **不得修改的文件**：{列出冻结的模块，防止 Agent 破坏已有逻辑}
- **日志/调试输出**：{例如：中间几何计算结果必须打印到 `logs/debug_{task_id}.log`}

### 4.3 人机交互协议 (Human-Agent Protocol)
- **每轮输出后，Agent必须**：
  1. 总结本轮修改点（diff summary）
  2. 标注潜在风险（risk flag）
  3. 提出下一轮建议（next step proposal）
- **人类反馈格式**：`[PASS]` / `[REJECT: {原因}]` / `[MODIFY: {具体指令}]`

---

## 5. 验证与验收 (Verification & Acceptance)

### 5.1 自动化验证 (Auto-Verification)
&gt; **Harness 原则：把验证编码进系统，不要靠人眼逐行检查。**

- [ ] **单元测试**：{例如：所有 Polygon 对象必须能通过 `.area` 和 `.bounds` 校验}
- [ ] **集成测试**：{例如：GDS 文件能在 KLayout 中打开且无报错}
- [ ] **DRC 检查**：{例如：运行 `python scripts/drc_check.py` 返回 0 错误}
- [ ] **回归测试**：{例如：与 HETT-002 的输出对比，差异仅在新增层}
- [ ] **数据契约测试**：{例如：DoE Table 输出符合 schema v2.1 的 JSON Schema}

### 5.2 人工验收检查点 (Human Gate)
- [ ] **Gate 1**：几何逻辑正确性（抽查 2-3 个 unit cell 的坐标）
- [ ] **Gate 2**：跨层对齐（L10/L20/L50 的谐振区中心对齐检查）
- [ ] **Gate 3**：边界情况（最小面积/最大面积的极端参数组合）

### 5.3 验收报告格式 (Acceptance Report)
Agent 必须在任务完成时输出以下报告：
```markdown
## 验收报告 (Acceptance Report)
- **任务编号**：HETT-001
- **完成状态**：✅ PASS / ❌ FAIL / ⚠️ PARTIAL
- **验证结果**：{列出所有自动化测试的通过情况}
- **已知缺陷**：{诚实列出未解决的问题及影响范围}
- **债务清单**：{临时方案、硬编码值、待重构点}
- **建议下游任务**：{基于本次交付，建议的 HETT-xxx 任务}