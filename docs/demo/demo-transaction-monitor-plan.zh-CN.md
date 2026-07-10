# 演示功能「可疑交易实时预警 + AI 风险研判」实现方案（待审）

> 本文件为 demo 分支新增功能的设计草案，供审阅。**尚未实现**。
> 依据：`docs/decisions/0006-demo-mvp-scope-freeze.md`、`docs/demo/DEMO-NOTES.zh-CN.md`、
> 已完成的合规初审（功能 4）。
> 性质：一次性演示品（throwaway demo），不并入 main 正式线。

---

## 一、功能定位

**开户后的持续 AML 监控**：模拟交易系统持续接收客户交易流水，当出现可疑模式时实时预警，
AI 结合客户 KYC 背景 + 内部政策，给出风险研判与处置建议（带政策引用）。

商业价值叙事：把 AI 合规从"开户前审查"延伸到"开户后持续监控"，覆盖 AML 全生命周期。
对小型券商（合规人手紧张）价值尤甚——可疑交易识别是最耗人力、最易漏、监管处罚最重的环节。

> 数据策略：可疑交易模式参考公开监管处罚中常见的典型（第三者存款、频密大额转账、
> 快进快出、金额与收入不符、结构化分层），但**全部为合成虚构数据**，不引用任何真实客户。
> 演示叙事**不提任何历史罚款**，纯讲功能价值。

---

## 二、已确认的设计决策

| 项 | 决策 |
|---|---|
| 痛点呈现 | 演示时不提公司历史罚款，纯讲 AI 功能价值（安全克制） |
| 可疑交易数据 | 两者都要：参考公开处罚的典型可疑模式 + 通用可疑模式，全部合成虚构 |
| 审核路线 | 复用合规初审的"一次 AI 调用 + 前端展示"模式 |
| 通知机制 | 复用监管雷达的实时轮询 + Snackbar 弹窗 |
| 数据合规 | 全合成数据，不连真实交易系统，不涉真实客户 |

---

## 三、用户可见的交互流程

```
切到「交易监控」Tab（第 4 个 Tab）
  ├─ 顶部状态条：监控中（绿点）· 已处理 N 笔 · 待研判 M 笔
  │
  ├─ 交易流水区（实时滚动）：
  │   每笔：时间 · 客户 · 类型(买入/卖出/入金/出金/转账) · 金额 · 风险标记
  │   正常交易：✅ 灰色一行
  │   可疑交易：🔴 高亮 + ⚠ 图标 + "待研判" 按钮
  │
  ├─ 当出现可疑交易时：
  │   ① 顶部 Snackbar 弹窗："⚠ 可疑信号：王志強 5分钟内 3 笔大额入金 1500 万"
  │   ② 流水里该笔高亮
  │
  └─ 点「AI 风险研判」→ 展开研判卡片：
     ┌─────────────────────────────────────┐
     │ 风险等级：🔴 高 / 🟡 中 / 🟢 低       │
     │ 风险信号（逐条）：                     │
     │   • 短时多笔大额入金（结构化分层特征） │
     │   • 入金总额与年收入严重不符           │
     │   • 第三者账户转入（需核实关系）       │
     │ 关联客户背景：                         │
     │   开户初审：资金来源待复核（review）   │
     │   风险评级：高                         │
     │ 处置建议：                             │
     │   • 限制交易（ctrlLevel=1）           │
     │   • 提交 STR 可疑交易报告              │
     │   • 人工复核资金来源                   │
     │ [溯源 政策第X页：可疑交易识别]         │
     │                                       │
     │ [标记已处理] [限制账户] [提交STR]      │
     └─────────────────────────────────────┘
```

---

## 四、合成交易数据设计

### 4 个剧本客户的交易行为（复用 demoClients 的客户）

| 客户 | 交易模式 | 是否触发预警 | 设计意图 |
|---|---|---|---|
| **陳大文**(PEP) | 正常买入港股，金额与资产相符 | 否（偶尔 borderline） | PEP 客户正常交易，展示"不误报" |
| **李美玲**(地址超期) | 小额定期存款，工薪族模式 | 否 | 普通客户正常流水 |
| **王志強**(资金可疑) | **5分钟内 3 笔大额入金共 1500 万**，来自 2 个第三者账户 | 🔴 **是（主剧本）** | 第三者存款 + 金额不符 + 快进 |
| **張正常**(干净) | 正常买入，金额合理 | 否 | 反衬，证明不乱报 |

### 可疑信号触发规则（前端模拟，不用 AI 判断"是否可疑"）

AI 只负责"研判已识别的可疑交易"，是否可疑由前端规则判定（确定性，演示稳定）：

| 规则 | 触发条件 | 对应剧本 |
|---|---|---|
| 短时大额频密 | 同一客户 5 分钟内 ≥3 笔，总额 ≥500 万 | 王志強 |
| 第三者存款 | 入金来自非本人姓名账户 | 王志強 |
| 金额与收入不符 | 单笔/累计入金 > 客户年收入 5 倍 | 王志強 |
| 快进快出 | 入金后 1 小时内转出 ≥80% | 王志強（可选） |

### 交易流生成器（前端 setTimeout）

- 每 2-4 秒（随机）生成一笔交易，正常:可疑 ≈ 8:1
- 可疑交易按剧本预设触发（王志強的 3 笔连发在演示开始后 ~15-20 秒出现）
- 每笔交易字段：`id / time / client_id / client_name / type / amount / currency / counterparty(第三方时填) / suspect_flags[]`

---

## 五、后端实现（新增，不改现有功能）

### 新增 schema（`schemas.py` 追加）
```python
class DemoTransaction(BaseModel):
    id: str
    time: str
    client_id: str
    client_name: str
    type: str           # buy / sell / deposit / withdraw / transfer
    amount: float
    currency: str = "HKD"
    counterparty: str = ""     # 第三方账户名（如有）
    suspect_flags: list[str] = []  # ["large_frequency", "third_party", ...]

class DemoTxnAnalyzeRequest(BaseModel):
    doc_text: str = ""
    client: dict                 # 客户 KYC（同初审）
    transaction: dict            # 可疑交易 + suspect_flags

class DemoTxnAnalyzeResponse(BaseModel):
    risk_level: str              # high / medium / low
    signals: list[str]           # 风险信号描述
    client_context: str          # 关联客户背景
    actions: list[str]           # 处置建议
    cited_page: int | None = None
    quote: str = ""
    summary: str
```

### 新建 `backend/app/services/demo_txn_analyze.py`
- `analyze(doc_text, client, transaction) -> dict`：一次 AI 调用
- prompt 要求：基于可疑交易的 suspect_flags + 客户 KYC 背景 + 政策，输出 risk_level / signals / client_context / actions / cited_page+quote
- 复用 `demo_intake.py` 的 `_truncate_doc` / `_extract_json` / `llm.generate` 模式

### 追加 endpoint（`routers/demo.py` 追加，不改现有）
- `POST /api/v1/demo/transaction/analyze`

---

## 六、前端实现

### 新增文件
- `frontend/src/data/demoTransactions.ts`：交易流生成器 + 剧本交易序列
- `frontend/src/components/TransactionMonitor.tsx`：监控面板（流水 + 预警 + 研判）
- `frontend/src/api/demo.ts`：追加 `analyzeTransaction()` + 类型

### 修改
- `frontend/src/pages/demo/DemoWorkbench.tsx`：加第 4 个 Tab「交易监控」

### TransactionMonitor 组件
- 交易流：useState 数组，useEffect 里 setTimeout 持续 push 交易
- 可疑检测：每笔进来时跑规则，命中的标 suspect + 触发 Snackbar
- 研判面板：点「AI 风险研判」→ 调 `analyzeTransaction` → 展示结果 + 政策溯源 chip（复用 onCite）
- 处置按钮（限制账户/提交STR）：纯前端状态变化（标记已处理），不连真实系统

---

## 七、改动文件清单

| 文件 | 动作 | 改现有后端? |
|---|---|---|
| `backend/app/schemas.py` | 追加 DemoTxn* schema | 否（只追加） |
| `backend/app/services/demo_txn_analyze.py` | 新建 | 否 |
| `backend/app/routers/demo.py` | 追加 endpoint | 否（只追加） |
| `frontend/src/api/demo.ts` | 追加 analyzeTransaction + 类型 | 否（只追加） |
| `frontend/src/data/demoTransactions.ts` | 新建 | 否 |
| `frontend/src/components/TransactionMonitor.tsx` | 新建 | 否 |
| `frontend/src/pages/demo/DemoWorkbench.tsx` | 修改（加第 4 Tab） | 否（前端） |
| `docs/progress/2026-07-09.md` | 新建/追加 | 否 |

---

## 八、执行顺序

1. 后端：schema → demo_txn_analyze.py → endpoint → curl 冒烟（用王志強可疑交易测）
2. 前端数据：demoTransactions.ts（交易流生成器 + 剧本）
3. 前端面板：TransactionMonitor.tsx（流水 + 可疑检测 + Snackbar + 研判）
4. 接入工作台：第 4 个 Tab
5. 端到端联调 + 进度日志

预估工时：~4-5 小时。

---

## 九、安全与合规自检

- [ ] 全合成数据，可疑交易模式参考公开典型但不引用真实客户 ✅
- [ ] 不连真实交易系统（前端模拟交易流）✅
- [ ] 演示叙事不提历史罚款（用户要求）✅
- [ ] API key 只在后端 ✅
- [ ] AI 输出带政策引用 ✅
- [ ] 不扩大 0006 范围（属 AML 合规演示延伸）✅
- [ ] 进度日志追加 ✅
