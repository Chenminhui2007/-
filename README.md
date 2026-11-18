# EduMatch Evidence 2026.2

基于 [RedStoneGuo/EduMatch](https://github.com/RedStoneGuo/EduMatch) 的产教智对竞赛升级版。保留原作者RsGuo署名与MIT许可证；公开代码基线 `bda36d847b074da0ea030decf0d2573ff126649f`。

本版采用“对话Agent编排＋本地确定性工具”：围绕高校专业调整，完成三维诊断、课程方案检查、条件情景和风险追溯。优先支持信管案例。学生只需提供个人情况，公开高校与市场资料由系统读取或查询。

## 与旧版的主要区别

- 三维分列，禁止无依据的综合TSI；旧48关键词匹配仅作探索。
- 任务级C/A/U证据和覆盖上下界；路径或映射未复核不发布正式分数。
- 方案检查增加原文支持定位、任务复核与资源条件；未知容量不能当成可行。
- 前后比较固定岗位、任务和证据快照；不把补资料或改课名当作教育收益。
- 私有交互日志记录提案、评价、修订理由及关联；不伪造真人交互。
- 5个新版MCP工具、JSON CLI及合成示例。

## 快速运行

Python 3.10+，在本仓库目录执行：

```powershell
python -m pip install -r requirements.txt
python scripts/evidence_agent.py coverage --input examples/evidence_v2/coverage.json --output runs/coverage.json
python scripts/evidence_agent.py evaluate --input examples/evidence_v2/proposal.json --session private_sessions/demo.jsonl --output runs/evaluation.json
python -m pytest tests -q
python -m mcp_servers.server --group evidence_v2 --selftest
```

示例明确标为合成，只验证机制。真实招聘、培养方案原件、文献PDF、个人资料均不在公开包中。真实诊断需要本地合法取得的数据；缺数据会明确报错，不回退到虚构事实。原有源代码工具保留，但不附旧原始数据、历史过程记录或演示页面。

详细机制、文献依据、四任务映射、真实案例流程及限制见 [使用与方法说明](docs/evidence_v2.md)、[文献元数据](docs/method_sources.json)、[数据接入](data/README.md)。

这是一版可交互调用的研究工具，尚不能证明真实培养或就业效果。高校审议、用户真实交互、实施验证和比赛报告仍需后续完成。
