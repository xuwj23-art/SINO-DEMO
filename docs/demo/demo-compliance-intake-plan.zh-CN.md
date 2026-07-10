# 演示功能「AI 合规初审」实现方案（草案待审）

> 本文件为 demo 分支上新增功能的设计草案，供审阅。**尚未实现**。
> 依据：`docs/decisions/0006-demo-mvp-scope-freeze.md` 功能 4、`docs/demo/DEMO-NOTES.zh-CN.md`、
> `docs/reference/trader-admin-system-usage-scenarios.zh-CN.md`。
> 性质：一次性演示品（throwaway demo），不并入 main 正式线。

---

## 一、功能定位

**开户前的 AI 合规初审**：客户提交开户 + KYC 申请，AI 对照公司内部 AML 政策，
自动生成开户审核 checklist，并逐项核对客户信息，输出带政策条款引用的初审结论。

商业价值叙事（对管理层）：**AI 替合规同事在开户源头把住 AML 关**，
把现在全人工、每份 20-40 分钟的审查，变成几分钟出一份带政策依据的初审清单，人只做最终复核。

> 与现有交易系统的关系：本交易系统 API 是「开户后」的资金/持仓/风控管理，
> 缺 PEP/资金来源/职业/收入等 KYC 字段；本功能补上「开户前」AML/KYC 审核这一环。

---

## 二、已确认的设计决策

| 项 | 决策 |
|---|---|
| 政策语料 | 扩写现有合成内部政策 PDF（`demo_internal_aml_policy_v2022_TC.pdf`），从 2 页扩到 4-5 页，补全开户审核条款，保持「公司内部政策」形态 |
| 审核范围 | 只做 AML/KYC 开户审核（身份、地址、PEP、受益所有人、资金来源、风险评级等） |
| 审核路线 | 路线 A：AI 后端一次调用返回全部结果，前端用动画逐项揭示（每项 0.5-0.8 秒间隔），总时长 ~10 秒 |
| 客户数据 | 预设 3-4 个剧本客户，演示时可挑选 |
| 数据合规 | 全部合成数据，不调用真实交易系统 API，不涉及真实客户资料 |

---

## 三、用户可见的交互流程

```
[合规初审 Tab]
  ① 选择剧本客户（3-4 张卡片，可点选）：陈大文(PEP) / 李美玲(地址超期) / 王志强(资金来源可疑) / 张正常(干净)
       ↓ 点击选中客户
  ② 展示客户档案：交易系统字段 + KYC 层字段（双栏）
       ↓ 点击「AI 合规初审」按钮
  ③ 阶段动画（前端）：
     ▸ 正在分析政策文件…   （读取已上传的政策 PDF，~1.5s）
     ▸ 正在生成审核清单…   （高亮出政策里的开户审核点，~1.5s）
     ▸ 正在逐项核对…       （逐条揭示 checklist 结果）
  ④ checklist 逐项揭示（每项 0.5-0.8s）：
     ☐ 身份证件核验        → ✅ 通过（身份证格式有效）
     ☐ 住址证明时效        → ❌ 不通过（已超 3 个月）[第 1 页]
     ☐ 政治人物(PEP)核查   → ❌ 不通过（为 PEP，须强化尽调）[第 1 页]
     ☐ 受益所有人核查      → ✅ 通过（个人户，无信托）
     ☐ 资金来源合理性      → ⚠ 待人工复核（收入与金额不符）
     ☐ 风险评级            → ⚠ 高风险（综合触发）
       ↓
  ⑤ 结论（任一 ❌ 即触发）：
     🔴 中断 —— 发现 N 项不通过 / M 项待复核
     问题点列表（每条带政策页码 chip → 点击跳转 PDF 高亮原文）
     底部：「初审未通过，请人工复核」
     
     —— 或全部 ✅/⚠ 时 ——
     🟢 初审无误，请人工复核
```

---

## 四、合成客户数据结构（双层）

```python
# 交易系统 API 字段层（字段名照搬真实 API）
"account": {
    "accNo": "SPDEMO001",
    "accName": "陳大文",
    "accNameUtf": "陈大文",
    "idNo": "A1234567(8)",        # 香港身份证格式
    "idType": "HKID",
    "baseCcy": "HKD",
    "aeId": "AE001",
    "maddress1/2/3": [...],
    "mobilePhone": "+852-98765432",
    "email": "demo@example.com",
    "country": 1,                 # 内部国家代码
    "sex": "M",
    "openAccountDate": "20260708",
    "ctrlLevel": 0,               # 开户时正常
    "accType": "MARGIN",          # 申请保证金账户
}

# 自建 KYC 层（本 API 没有，AML 初审必需）
"kyc": {
    "nationality": "HK",
    "date_of_birth": "1965-03-15",
    "occupation": "前政府官员",
    "employer": "（已退休）",
    "annual_income": 800000,      # HKD
    "net_worth": 5000000,
    "source_of_funds": "投资收益",
    "pep_flag": true,
    "pep_details": "2018-2022 任某国副部长",
    "risk_rating": "high",
    "address_proof_date": "2026-02-01",   # 地址证明签发日（演示超期）
    "address_proof_type": "水电费账单",
    "beneficial_owner": "self",           # 个人户
    "expected_monthly_turnover": 8000000, # 预期月交易量（与收入不符）
}

# 本次申请
"application": {
    "business_type": "保证金证券账户",
    "requested_products": ["港股", "窝轮"],
    "submitted_documents": ["身份证", "地址证明", "入金凭证"],
}
```

### 预设剧本客户（4 个）

| 客户 | 核心缺陷 | 预期初审结果 | 演示目的 |
|---|---|---|---|
| **陳大文** | PEP（前副部长）+ 收入与交易额不符 | ❌ 中断 | 高风险，PEP 强化尽调 |
| **李美玲** | 地址证明已超 3 个月 | ❌ 中断 | 常见易错，时效性 |
| **王志強** | 资金来源「投资收益」但无收入证明 + 大额入金 | ⚠ 待复核 | 资金来源可疑 |
| **張正常** | 全部合规 | ✅ 通过 | 展示「无误」分支，证明 AI 不是只会挑刺 |

---

## 五、政策 PDF 扩写计划

在 `scripts/generate_demo_policy_pdf.py` 基础上扩写，从 2 页（7 节）扩到 4-5 页，
新增/细化以下开户审核条款（仍为合成文件，署名「盛富证券（示范）」，依据 SFC 2021 指引）：

| 章节 | 新增/细化内容 | 对应审核点 |
|---|---|---|
| 第二节 CDD | 补：风险评级方法（高/中/低）、简化与强化尽调触发条件 | 风险评级 |
| 新增：资金来源核实 | 新增章节：须核实资金来源、大额入金须提供来源证明、与收入不符须人工复核 | 资金来源 |
| 第三节 PEP | 已有（持续强化、不设豁免、高层批准） | PEP 核查 |
| 第四节 受益所有人 | 已有（信托须识别 settlor/trustee/beneficiary） | 受益所有人 |
| 身份证件核验 | 新增：身份证件须有效、格式核验、非面对面额外核实 | 身份核验 |
| 开户审核总览 | 新增：开户前须完成上述所有审核项，任一不通过不得开户 | checklist 总纲 |

每条条款仍带「第 N 节」「第 N 页」标记，供 AI 引用页码。

---

## 六、后端实现

### 新增文件
- `backend/app/services/demo_intake.py`：初审逻辑
- `backend/app/routers/demo.py`：新增 endpoint（在现有 router 内追加）

### 新增 schema（`schemas.py` 追加）
```python
class DemoIntakeRequest(BaseModel):
    doc_text: str = ""              # 已上传的政策 PDF 文本
    client: dict                    # 合成客户（account + kyc + application）

class DemoChecklistItem(BaseModel):
    key: str                        # "id_verification"
    title: str                      # "身份证件核验"
    status: str                     # "pass" | "fail" | "review"
    detail: str                     # 说明
    cited_page: int | None = None   # 政策页码
    quote: str = ""                 # 政策原文（供前端高亮）

class DemoIntakeResponse(BaseModel):
    checklist: list[DemoChecklistItem]
    outcome: str                    # "passed" | "failed" | "needs_review"
    issues: list[DemoChecklistItem] # fail/review 项汇总
    summary: str                    # 一句话结论
```

### 新增 endpoint
`POST /api/v1/demo/intake` —— 入参 `doc_text + client`，返回 `DemoIntakeResponse`。

### AI prompt 设计（核心）
两个阶段合一（一次调用）：
1. **从政策文本提取开户审核点**（生成 checklist 模板）
2. **对照客户信息逐项判断**（填 status/detail/cited_page/quote）

system prompt 要点：
- 「你是 AML 合规审核助手。依据《政策》判断该客户的开户申请是否合规。」
- 「先从政策中识别所有开户前须完成的审核项（如身份核验、地址证明、PEP、受益所有人、资金来源、风险评级）。」
- 「再逐项核对客户信息。每项 status 为 pass/fail/review。」
- 「fail/review 项必须给出 cited_page（政策页码）和 quote（逐字抄录的政策原文 10-40 字）。」
- 「任一 fail → outcome=failed；无 fail 但有 review → needs_review；全 pass → passed。」
- 严格 JSON 输出（复用 `demo_rag.py` 的 `_extract_json`）。

### 复用
- `llm.generate()`、`_extract_json()`、`_truncate_doc()` 直接复用 `demo_rag.py`。
- 错误处理复用 `demo.py` 的 LlmConfigurationError/LlmServiceError 模式。

---

## 七、前端实现

### 新增/修改文件
- `frontend/src/api/demo.ts`：新增 `intake()` + 类型
- `frontend/src/pages/demo/DemoWorkbench.tsx`：新增第三个 Tab「合规初审」
- `frontend/src/data/demoClients.ts`（新建）：4 个剧本客户数据
- `frontend/src/components/IntakePanel.tsx`（新建）：初审面板（客户选择 + 动画 + checklist）

### Tab 结构（DemoWorkbench.tsx）
```
Tabs: [文档问答] [监管雷达] [合规初审(新)]
```

### 合规初审面板交互
1. **客户选择区**：4 张 MUI Card，显示姓名 + 一句话标签（PEP/地址超期/…），点选高亮。
2. **客户档案**：选中后展示双栏（交易系统字段 / KYC 字段）。
3. **「AI 合规初审」按钮**：点击触发 `intake()`。
4. **三阶段动画**（前端 setTimeout 控制）：
   - 阶段 1「正在分析政策文件…」1.5s
   - 阶段 2「正在生成审核清单…」1.5s（此时可调用 PdfViewer 高亮政策条款）
   - 阶段 3「正在逐项核对…」：AI 结果返回后，用 setInterval 每 0.6s 揭示一项（✅/❌/⚠）
5. **揭示中遇 ❌**：暂停揭示，标红该项，展开问题详情 + 政策页码 chip。
6. **结论条**：🔴 中断 / 🟢 通过，附「请人工复核」。

### 动画实现要点
- AI 结果在阶段 1 开始时就已请求（后端 ~8s），前端动画用 `await Promise.race([aiCall, delay])` 协调。
- 揭示动画用 `setInterval`，遇 `status==="fail"` 时 `clearInterval` 并停在该项。
- 政策页码 chip 点击 → 复用现有 `jumpToCitation(page, quote)` → PDF 跳页高亮。

---

## 八、改动文件清单

| 文件 | 动作 | 说明 |
|---|---|---|
| `scripts/generate_demo_policy_pdf.py` | 修改 | 扩写政策内容到 4-5 页 |
| `docs/demo/assets/demo_internal_aml_policy_v2022_TC.pdf` | 重新生成 | 扩写后重生成 |
| `backend/app/schemas.py` | 追加 | DemoIntake* 系列 schema |
| `backend/app/services/demo_intake.py` | 新建 | 初审逻辑 |
| `backend/app/routers/demo.py` | 追加 | `/demo/intake` endpoint |
| `frontend/src/api/demo.ts` | 追加 | `intake()` + 类型 |
| `frontend/src/data/demoClients.ts` | 新建 | 4 个剧本客户 |
| `frontend/src/components/IntakePanel.tsx` | 新建 | 初审面板 |
| `frontend/src/pages/demo/DemoWorkbench.tsx` | 修改 | 加第三个 Tab |
| `docs/progress/2026-07-08.md` | 追加 | 进度日志（规则要求） |

---

## 九、执行顺序（建议）

1. **扩写政策 PDF**（先做，是后续一切依据）→ 重新生成 PDF → 抽取验证文本层正常。
2. **后端**：schema → demo_intake.py → router endpoint → 用真实 Opus 冒烟测试（`/demo/intake`）。
3. **前端数据**：demoClients.ts（4 个剧本）。
4. **前端面板**：IntakePanel.tsx（客户选择 + 三阶段动画 + checklist 揭示）。
5. **接入工作台**：DemoWorkbench.tsx 加 Tab。
6. **端到端联调**：`./scripts/start-demo.sh` → 走完整流程。
7. **进度日志**：每步追加。

预估总工时：~5-6 小时（政策扩写 1h + 后端 1.5h + 前端 2.5h + 联调 1h）。

---

## 十、安全与合规自检（对照 0002 Review Gate）

- [ ] 合成数据：4 个剧本客户全部虚构，不含真实客户资料。✅
- [ ] 不调用真实交易系统 API（字段结构参考，数据自造）。✅
- [ ] API key 只在后端环境变量，不进前端。✅
- [ ] AI 输出带政策引用，无依据不臆测（prompt 强制 cited_page + quote）。✅
- [ ] 不扩大 0006 范围：本功能即 0006 功能 4。✅
- [ ] 文档语言：新增文档简体中文，字段名/URL 保持英文。✅
- [ ] 进度日志：每步追加，不覆盖。✅

> 本功能属安全相关（AML 合规），按 0002 应标注「待审查」。但 0006 演示阶段放宽：
> 数据全合成、不涉真实客户/权限过滤/密钥，可快速产出 + 抽查。
