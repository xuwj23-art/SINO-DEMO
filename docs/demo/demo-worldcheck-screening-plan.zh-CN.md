# 新项目方案：World-Check 命中智能清除助手

> 本方案基于真实痛点（Gem_47 LI FENG 16+ 命中清除、Gem_50 ~2000 客户批量筛查）设计。
> 属 demo 分支延伸，未实现。数据全合成，不引用真实客户。
> 依据：`docs/reference/sino-rich-current-state-analysis.zh-CN.md`。

---

## 一、痛点（真实证据）

### Gem_47 — 单个 UBO 16+ 命中清除
UBO LI FENG 在 World-Check 命中 16+ 条：
- 中国移动董事长、几内亚比绍外交官、合肥/上海/山西/浙江国企领导
- 重庆 2130 万金融诈骗、湖南桃江/资阳有组织犯罪
- CSRC/CBIRC 警告、西部证券投行

员工操作：逐条分类（PEP/Sanctions/Adverse Media）→ 比对出生日期与履历 → 起草双语 False Positive 清除邮件 → 写 Python（pypdf）搜 PDF 找履历佐证 → 生成 Case Report。**极度依赖人工经验 + 工具拼凑，单个 UBO 耗时数天。**

### Gem_50 — 批量筛查
~2000 客户，World-Check CSV 导出无中文名列、无 API、无 Settings 权限，员工用 Excel 公式 `=IF(LEN(B2)<>LENB(B2),"含有中文","僅限英文")` 人肉挑中文、UTF-8 编码 65001、手工写 Resolution Note、手工导 PDF Case Report。

---

## 二、功能定位

**World-Check 命中智能清除助手**：给定一个合成 UBO 的 KYC 资料 + 一批 World-Check 命中记录，AI 自动完成：
1. 命中分类（PEP / Sanctions / Adverse Media）
2. 与 UBO KYC 比对（出生日期、履历、国籍）初判 True/False Positive
3. 为每条命中摘录比对证据
4. 生成双语 Resolution Note 草稿
5. 汇总 Case Report（含处置建议：清除 / 升级 EDD / 人工复核）

商业价值：把资深合规官数天的命中清除工作，变成带证据摘录的半自动流程。

---

## 三、合成数据设计

### 合成 UBO（剧本）

| UBO | 国籍 | 命中数 | 设计意图 |
|---|---|---|---|
| **李峰**（LI FENG） | 中国香港 | 16+ | 主剧本：大量命中但多为同名不同人，演示 False Positive 批量清除 |
| **Aung Min** | 缅甸 | 3 | 命中真实制裁名单（FATF 黑名单国），演示 True Positive → 升级 EDD |
| **陈静** | 中国内地 | 5 | 部分命中 PEP（地方官员），演示混合判定 |

### 合成命中记录结构
```json
{
  "hit_id": "WC-001",
  "category": "PEP",           // PEP | Sanctions | AdverseMedia
  "matched_name": "Li Feng",
  "match_type": "exact",       // exact | fuzzy | alias
  "title": "前中国移动董事长",
  "country": "CN",
  "dob": "1952-08-01",         // 命中对象的出生日期（用于比对）
  "source": "World-Check One",
  "risk_note": "曾任大型国企主要负责人"
}
```

UBO 的 KYC（复用 demoClients 的 KYC 层结构）含真实出生日期、履历、国籍，供 AI 比对。

---

## 四、后端实现（新增，不改现有）

### 新增 schema
```python
class DemoScreeningHit(BaseModel):
    hit_id: str
    category: str        # PEP | Sanctions | AdverseMedia
    matched_name: str
    match_type: str
    title: str
    country: str
    dob: str
    source: str
    risk_note: str

class DemoScreeningRequest(BaseModel):
    doc_text: str = ""
    ubo: dict            # UBO 的 KYC（姓名/出生日期/国籍/履历）
    hits: list[dict]     # 命中记录

class DemoScreeningHitResult(BaseModel):
    hit_id: str
    category: str
    verdict: str         # false_positive | true_positive | needs_review
    evidence: str        # 比对证据（出生日期/履历差异）
    risk_note: str

class DemoScreeningResponse(BaseModel):
    results: list[DemoScreeningHitResult]
    resolution_note: str      # 双语清除说明草稿
    overall_action: str       # clear | escalate_edd | manual_review
    cited_page: int | None = None
    quote: str = ""
    summary: str
```

### 新建 `demo_screening.py`
- `screen(doc_text, ubo, hits) -> dict`：一次 AI 调用
- prompt：给定 UBO KYC + 命中列表，逐条比对出生日期/履历/国籍，判定 false_positive/true_positive/needs_review，附证据；生成双语 Resolution Note；给总体处置建议 + 政策引用
- 复用 `_truncate_doc` / `_extract_json` / `llm.generate` 模式

### 追加 endpoint
- `POST /api/v1/demo/screening/analyze`

---

## 五、前端实现

### 新建 `ScreeningPanel.tsx`
- UBO 选择（3 个剧本 UBO）
- 命中列表展示（按 category 分组：PEP/Sanctions/AdverseMedia，颜色区分）
- 点「AI 智能清除」→ 逐条揭示 verdict（✅ False Positive / ❌ True Positive / ⚠ 待复核）+ 证据
- Resolution Note 双语展示（可复制）
- 总体处置建议 + 政策溯源 chip
- 复用三阶段动画 + 逐项揭示（同合规初审）

### 接入
- 工作台加第 6 个 Tab「名单筛查」或在合规初审内加子页

---

## 六、演示画面

```
选 UBO「李峰」→ 显示 16 条命中（PEP 10 / Sanctions 3 / AdverseMedia 3）
点「AI 智能清除」
  ▸ 正在比对 KYC 资料…
  ▸ 正在分类命中…
  ▸ 正在逐条判定…
  逐项揭示：
    WC-001 前中国移动董事长 → ✅ False Positive（出生日期不符：UBO 1968 vs 命中 1952）
    WC-002 几内亚比绍外交官 → ✅ False Positive（国籍不符：UBO 中国香港 vs 命中几内亚比绍）
    WC-005 重庆金融诈骗 → ⚠ 待复核（同名同省，需进一步核实身份证号）
    ...
  Resolution Note（双语）：
    "经比对，16 条命中中 14 条为同名不同人（出生日期/国籍/履历不符），
     2 条待人工复核。建议清除 14 条，对 2 条进行身份核实。"
  总体处置：manual_review（2 条待复核）
  [溯源 政策第X页：名单筛查与命中处理]
```

---

## 七、工时预估

- 后端：~2h（schema + screen.py + endpoint）
- 前端：~3h（数据 + ScreeningPanel + 接入）
- 测试 + 联调：~1h
- **总计 ~6h**

---

## 八、安全自检

- 全合成数据（虚构 UBO、虚构命中）✅
- 不连真实 World-Check ✅
- 不引用真实客户（LI FENG 等为虚构姓名，巧合不对应真人）✅
- AI 输出带政策引用 ✅
- Resolution Note 为草稿，最终须人工确认 ✅
