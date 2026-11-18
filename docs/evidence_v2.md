# EduMatch Evidence 2026.2：本对话编排的专业调整工具

## 使用边界

本版采用方案1：对话中的Agent负责理解问题、检索、提出方案、解释失败和修订；本地代码负责证据结构检查、数值计算、课程硬约束、条件情景与交互留痕。没有把关键词查询器包装成自动生成模型，也不声称复现Self-RAG、ACE或TRACE。

优先案例为北京工业大学信息管理与信息系统。学生只提供个人经历与问题；培养方案、岗位和文献由系统查找。学生不代表全体学生或学院决策者。公开高校材料不代表高校参与了访谈。

## 四任务与工具

|赛题任务|实现与入口|当前限制|
|---|---|---|
|现状差距|`diagnose`读取冻结的招聘、课程、计划、历史资源，技能/方向/规模分列；`coverage`计算任务级C/A/U|旧48标签仅探索；正式任务映射与完整修读路径须复核|
|方案设计|`evaluate`检查课程增删改合并、学分学时、先修、文献支持定位、资源；保留分流工具|结构检查不能判定教育合理性；容量未知仅为条件方案|
|效果验证|`compare`检查冻结口径后计算覆盖区间差；原有四年队列及三情景工具保留|条件推演不是未来就业预测；设计覆盖不是学习达成|
|风险应对|评价结果给出课程、分流、规模滞后、资源风险及动作关联|通用风险条目仍须针对实际动作审议，概率未估计|

任务3按赛题选择合适验证路径，不要求所有验证方法都做。技术测试不能替代真实案例与教育效果验证。

## 指标及依据

1. **技能结构**：IS2020六领域用于组织能力，评价叶节点须为可观察任务。广告同任务去重计数，`p=count/N`，`w=count/sum(count)`。权重描述样本提及结构，不是教育重要性。C要求适用版本的目标、活动、考核及任务层级复核；A要求完整核查后的未覆盖依据；其他为U。下界`100ΣwC`，上界`100Σw(C+U)`。未知不得填零；映射或路径未核验不发布正式分数。课名匹配不能证明覆盖。
2. **培养方向**：岗位群数及明确分母的份额、任务—课程—考核链、志愿和确认容量分别呈现。交叉岗位不能将份额直接转成招生名额。方向覆盖属于技能分组，不能再重复加进综合分。
3. **规模匹配**：公开招生计划、实际录取/报到、历史去向、可用资源和假设分别登记。`resource_pressure`按同单位同期间计算需求/可用量与缺口。未知容量不算零或无限大。历史师资总量不等于可新增容量。

不输出三维综合TSI。学分/师资硬约束不可被市场热度补偿。尚无真实决策者偏好，也无完整同口径输入。C/A/U和区间为本项目操作化，不能冒称文献原有量表。

前后比较同时要求共同证据快照、相同任务和岗位样本，以及调用者确认路径范围与测量层次相同。计算`[after.lower-before.upper, after.upper-before.lower]`。补资料导致U变C不是课程改革效果。哈希仅校验声明内容一致，不能代替语义与真实性审查。

## 文献怎样进入实现

|原文与核读位置|落实内容|不可越过的边界|
|---|---|---|
|ACM/AIS IS2020，PDF36—40、43—47页|任务定义与框架出处必填；能力映射未复核阻断正式覆盖|国际指南不直接提供中国高校权重|
|Biggs 1996《Enhancing teaching through constructive alignment》，PDF4—5、13页|学习目标、活动、考核同时作为证据与动作字段|不提供最优学时系数|
|OECD/JRC 2008《Handbook on Constructing Composite Indicators》，PDF34、36、42页；Saisana等2005，PDF3—4页|构念、重复计量、缺失与敏感性分开；不凑三维总分|并非文献禁止所有综合指标|
|Hevner等2004 MIS Quarterly，PDF8—10、12页|技术验证、案例验证、教育效果分别记录|有原型不等于证明教育收益|
|ALCE，EMNLP2023，PDF4、8—9页|方案引用须登记支持论断、原文定位与复核状态|代码只能检查结构，语义支持仍需核读|
|TravelPlanner，ICML2024，PDF3—6页|课程硬约束与整案可行性单独检查|旅游任务成绩不能迁移到专业调整|
|τ-bench，ICLR2025；ACE、TRACE，ICLR2026公开稿|提案—评价—修订留痕及最终状态检查|测试为合成；未复现论文算法或基准成绩|

补充文献的公开元数据、核读位置、方法用途及局限见`method_sources.json`。不随代码再分发全文PDF。2018国家标准公开副本需结合现行适用规则及学校培养要求核验，不能将最低师资标准当扩招许可。

## 本地操作

Python 3.10+，从仓库根目录执行。CLI用JSON文件，输出明确指定路径。真实交互默认保存在被Git忽略的`private_sessions/`。

```powershell
python scripts/evidence_agent.py coverage --input examples/evidence_v2/coverage.json --output runs/coverage.json
python scripts/evidence_agent.py evaluate --input examples/evidence_v2/proposal.json --session private_sessions/demo.jsonl --output runs/evaluation.json
python scripts/evidence_agent.py public-summary --session private_sessions/demo.jsonl --output runs/session_metadata.json
```

这些示例均为合成数据，不是北工大真实案例。`evaluate`自动记录方案与评价；修订时附`--parent 上一次proposal_event_hash --reason 修改依据`。不自动编造学生回复，也不自动把失败方案修改成看似通过。

接入本地经授权的整理数据后：

```powershell
python scripts/evidence_agent.py diagnose --input examples/evidence_v2/imis_request.json --data-root data/competition_2026 --session private_sessions/imis.jsonl --output runs/imis.json
python -m mcp_servers.server --group evidence_v2
```

MCP提供5个`evidence_v2_*`工具；原`competition_*`保留数据追溯、课程及情景计算。MCP是否已被某客户端安装和实际调用，需分别验证；代码发布不会自动修改客户端配置。

`record`用于登记真实输入：JSON需含`kind:"input"`、`origin:"student_self_report"`、`payload`。公开材料来源用`public_document`并附`source`；高校直接提供的声明用`institution_statement`并附来源。来源标签是调用者声明，记录链不能证明真实身份。单写入者本地JSONL日志，不是防篡改签名系统；公开摘要只导出事件类型与计数。

## 后续真实案例流程

读取公开资料和原文 → 学生描述真实经历 → 根据证据诊断 → 提出具体动作 → 外部工具返回错误/缺项 → 依据错误修订并保留父方案 → 固定口径进行条件验证 → 审议风险。未知教学证据优先形成检索任务，不直接触发删课。

本次代码升级不代表已经完成学生真实复核、教师审议、实际实施、PDF报告或PPT大纲。接下来的案例使用本版记录真实过程。
