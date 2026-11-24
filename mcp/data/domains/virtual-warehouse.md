# 虚拟仓

## 用户目标

查询虚拟仓及库存，处理虚拟仓调拨、分配、归还和采购申请。

## 能力路由

| 业务能力 | 类型 | action |
| --- | --- | --- |
| 查询虚拟仓列表 / 库存 | 查询 | `webapi_itemapi_lockwarehouse_getwarehouselist` / `webapi_itemapi_iteminventory_getvirtualstock` |
| 创建 / 查询虚拟仓调拨单 | 写入 / 查询 | `webapi_itemapi_lockwarehouse_lwhallocationcreate` / `webapi_itemapi_lockwarehouse_getlwhallocationlist` |
| 创建 / 查询分配归还单据 | 写入 / 查询 | `webapi_itemapi_lockwarehouse_lwhoperationcreate` / `webapi_itemapi_lockwarehouse_getlwhoperationlist` |
| 创建更新 / 查询采购申请单 | 写入 / 查询 | `webapi_itemapi_lockwarehouse_lockpurchase_createorupdatepurchase` / `webapi_itemapi_lockwarehouse_lockpurchase_getpagelockpurchases` |
| 提交审核、审核或打回采购申请 | 写入 | `webapi_itemapi_lockwarehouse_lockpurchase_verifylockpurchases` |

## 执行要点

- 先查询运营云仓中的虚拟仓列表和目标虚拟仓 ID，不要把实体仓、分仓或普通仓位 ID 用在虚拟仓接口。
- 查库存时明确用户要看哪个虚拟仓、哪些 SKU，以及是单仓结果还是多虚拟仓汇总。
- 创建虚拟仓调拨时明确来源、目标、SKU 和数量；查询调拨单用于跟进处理状态和实际结果。
- 分配与归还是相反业务方向，必须确认当前操作类型和原始分配关系，不能仅凭数量正负猜测。
- 创建或更新采购申请前先查询现有申请，区分新增申请与修改已有申请，避免重复创建。
- “提交审核/审核/打回采购申请单”当前缺少公开参数文档，标记为 `unavailable_current_catalog`，即使用户要求也必须说明暂不可用。
- 实体仓库存、实体仓调拨和普通采购分别读取[库存](inventory.md)、[调拨](transfers.md)与[采购](purchasing.md)，不要混用单据类型。

## 结果呈现

- 虚拟仓库存始终带虚拟仓名称/编号与 SKU，展示当前量、已分配量、已归还量及可解释的剩余口径。
- 虚拟仓调拨明确来源与目标；分配、归还要用业务方向文字表达，不能只显示数量正负。
- 采购申请展示申请单号、申请状态、虚拟仓、SKU、申请数量和审核进度；不得把申请数量算作已采购或已入库。
- 审核能力不可用时直接说明当前公开参数不足，不建议用户尝试拼接字段。

## 典型问题

- “直播仓 A001 还剩多少可分配？”：查询指定虚拟仓库存，展示总量、已分配和可用口径。
- “把活动仓的20件归还主运营仓”：确认原分配关系和方向后执行，回执说明来源、目标、SKU 与数量。
