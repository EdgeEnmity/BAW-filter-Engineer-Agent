1. 任务目标
    基于输入的mason模型、输入的材料参数库和输入的谐振器测试结果建立BAW filter可用的PDK

2. 任务领域
    PDK - PDK的逻辑搭建

3. 上游依赖
    mason模型的code，材料参数库，pdk的code已写成skill文档并包含了源码
    
4. 成功标准
    AI Agent理解了pdk的逻辑
    我输入实测结果后能够正确完成插值
    能够输出ADS可用的PDK包（之后会给额外的输入，用于交互ADS）

5. 硬边界
    暂无，后面遇到再说

6. 分阶段交付
    Phase 1	模块接口/伪代码/数据流图	人工 review 逻辑
    Phase 2	核心算法/插值逻辑	跑通 + 抽查输出
    Phase 3	集成到主流程 + 自动化测试	回归测试通过

7. 验证与验收方式
    Phase 1 人工review输出的谐振器的结果
    Phase 2 review参数化的谐振器性能（包括kt2，Qs，Qp，fs，阻抗等等）

8. 已知风险与阻塞
    可能卡在理解Hybrid PDK的逻辑或操作上
    PDK的外推可能会出现异常结果
    bad data可能影响PDK效果
    不了解ADS与python和c代码的交互

