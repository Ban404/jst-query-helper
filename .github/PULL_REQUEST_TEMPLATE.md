## 这次改了什么

<!-- 一句话说清 -->

## 为什么

<!-- 动机、背景 -->

## 怎么验证

<!-- 贴 python tools/verify_offline.py 和 python -m pytest tests/ -q 的结果 -->

```
(把通过结果贴这里)
```

## 自查清单

- [ ] 引导话术只改了 `guide.json` 一份，技能包与连接器包逐字一致
- [ ] 场景只改了 `scenarios.json` 一份，Python / Node 两份引擎都同步了
- [ ] 没有放宽只读白名单，没有删 `READONLY` 标记
- [ ] 没有提交真实账号 / 人名 / 公司名 / 店铺 ID / 序列号 / token / 本机路径
- [ ] 示例代码用的是占位假数据（如 `SN-DEMO-0001`）
- [ ] 更新了 `CHANGELOG.md`（如需要）与对应文档

## 相关 Issue

<!-- Closes #... -->
