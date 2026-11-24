# 贡献指南

谢谢你的兴趣。本项目欢迎：修 bug、补场景、改进新手引导、完善文档、补测试。

## 先读三件事

1. [免责声明](DISCLAIMER.md)——本项目的边界与法律定位；
2. [安全策略](SECURITY.md)——凭据怎么处理、什么不能提交；
3. [架构说明](docs/ARCHITECTURE.zh-CN.md)——代码怎么组织、两份实现怎么保持一致。

## 本地开发

只需 Python 3.8+ 和 Node 18+，不需要装水宝、不需要联网、不需要任何凭据。

```bash
git clone <你的仓库地址>.git && cd jst-query-helper
python -m pip install pytest       # 唯一开发依赖，仅测试用
python tools/verify_offline.py     # 纯离线自检：结构 / 脱敏 / 白名单 / 场景 / 打包
python -m pytest tests/ -q         # 离线单元测试
```

要在真实环境验证（需自己装好水宝并授权）：

```bash
python tools/verify_online.py
```

## 改东西时遵守这些约束

- **话术只改一处**：`guide.json`（引导）和 `scenarios.json`（场景）各是唯一来源，技能包一份、连接器包一份，改完两边必须逐字一致。`verify_offline.py` 会检查。
- **两份实现要对齐**：`skill/scripts/*.py` 与 `connector/*.mjs` 是同一套逻辑。改一边记得改另一边，并补测试。
- **只读不可破**：不要放宽白名单让写接口放行；不要删 `READONLY` 标记。`verify_offline.py` 会验证 36 查询放行、53 写入被拦。
- **接口清单来自重新识别**：`catalog/actions.json` 由 `tools/refresh_catalog.py` 从上游查询程序生成。不要手写改动；上游升级后重新跑一次并复核差异。
- **绝不提交敏感信息**：真实账号、人名、公司名、店铺 ID、序列号、token、本机绝对路径。`config.json` 和 `*.csv` 已被 gitignore。示例一律用明显占位的假数据（如 `SN-DEMO-0001`）。

## 提交与 PR

- 一个 PR 做一件事；标题一句话说清改了什么。
- 说明动机、改法、怎么验证（贴上 `verify_offline.py` 和 `pytest` 的通过结果）。
- 新增场景请在 `scenarios.json` 登记，并在两份引擎里都实现，`docs/SCENARIOS.zh-CN.md` 同步更新。
- 涉及引导话术的改动，请用小白视角走一遍 `skill/references/getting-started.md` 的剧本。

## 报告问题

用 Issue，说清楚：你的环境（系统 / 水宝版本 / Python 或 Node 版本）、做了什么、期望什么、实际什么。贴日志时**先打码** token、账号、SN、客户信息。安全问题走私密渠道，见 [SECURITY.md](SECURITY.md)。

## 行为准则

友善、就事论事、尊重不同水平的使用者。问题的提出者往往是不懂技术的普通人，耐心一点。
