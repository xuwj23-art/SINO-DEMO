# 演示版说明（一次性 Demo）

> **性质**：这是为现场演示临时搭建的**一次性版本**，位于 git 分支 `demo`。它**刻意偏离** 0006 正式方向，未改动进度文档与正式架构。演示结束后按需保留或丢弃，不要合回 `main` 的正式实现。

## 与 0006 正式方向的区别

| 维度 | 正式方向（0006） | 本演示 |
|---|---|---|
| 检索 | bge-m3 embedding + 内存向量余弦 | **无检索**：整篇文档文本直接进 Opus 4.8 长上下文 |
| PDF 抽取 | 后端 PyMuPDF（页码 + bbox） | **浏览器端 pdf.js** 抽取（带 `===== Page N =====` 页码标记） |
| 后端状态 | 内存 DOCUMENTS/CHUNKS/EMBEDDINGS | **对文档无状态**：文档文本由前端随请求发来 |
| 部署 | 本地 | 主应用本地；**监管测试站上 Vercel** |

未触碰 `pdf_extract.py` / `embeddings.py` / `state.py`，也未改 `docs/decisions/0006` 与 `docs/progress/*`。演示路径不加载 `sentence-transformers`/`torch`（懒加载，不触发即不下载 2GB 模型）。

## 组成

- **后端（复用现有 FastAPI）** —— 新增：
  - `backend/app/services/demo_rag.py`：`answer()`（整文问答，返回带页码+引文的 citations）、`analyze_update()`（监管推送摘要 + 对当前文档的改进建议）。
  - `backend/app/routers/demo.py`：`POST /api/v1/demo/ask`、`POST /api/v1/demo/regulatory/analyze`、`GET /api/v1/demo/regulatory/updates`（代理测试站，失败不 500）。
  - `backend/app/schemas.py`：新增 Demo* 模型；`main.py` 挂载 demo router。
- **前端（复用 Vite + React19 + MUI6）** —— 新增：
  - `frontend/src/api/demo.ts`、`frontend/src/lib/pdfText.ts`（pdf.js 抽取 + worker 配置）、
    `frontend/src/components/PdfViewer.tsx`（预览 + 跳页 + 引文文本层高亮）、
    `frontend/src/pages/demo/DemoWorkbench.tsx`（问答 / 监管雷达 + 右侧 PDF）。
  - `App.tsx` 直接渲染 `DemoWorkbench`。新增依赖：`react-pdf`、`pdfjs-dist`、`axios`。
- **监管测试站** `regulatory-test-site/`（独立 Next.js，App Router）：发布页 `/` + `GET/POST /api/updates`（CORS 全开）。存储用 Upstash Redis（REST），env 缺失时回退进程内存。

## 本地启动

### 一键启动（推荐）
在 Git Bash 里：
```bash
./scripts/start-demo.sh
```
脚本会：先清理占用 8000/5173/3001 的残留进程 → 依次起后端(Sino-ai)、监管测试站、前端 → 打印三个地址 → 汇总日志到 `tmp/demo-logs/`。**Ctrl+C 一次性关闭全部**。
- 后端 Python 默认用 `Sino-ai` 环境路径；若你的路径不同，用 `DEMO_PYTHON=/c/Users/<you>/anaconda3/envs/Sino-ai/python.exe ./scripts/start-demo.sh` 覆盖。
- 打开 http://localhost:5173 即演示前端；http://localhost:3001 是监管发布站。

> ⚠️ **发布监管推送请用测试站的网页表单**（http://localhost:3001），不要用 `curl` 在 Git Bash 里发中文 —— Git Bash 的 curl 会把 UTF-8 中文编码搞坏，导致雷达里显示乱码。网页表单/浏览器发布则完全正常。彩排时如需重置，测试站列表右上角有「清空全部」按钮（或对 `/api/updates` 发 DELETE）。

### 手动分别启动（备用）

**1. 后端**（用项目 conda 环境 `Sino-ai`，已装 anthropic/fastapi/torch 等全部依赖）：
```bash
conda activate Sino-ai
cd backend
uvicorn app.main:app --reload   # http://localhost:8000
```
`.env` 需有 `ANTHROPIC_API_KEY`；`REGULATORY_TEST_SITE_URL` 指向测试站（本地 `http://localhost:3001` 或 Vercel 地址，**去掉尾斜杠**）。

**2. 前端**：
```bash
cd frontend
pnpm install
pnpm dev            # http://localhost:5173
# 若本机 pnpm 因依赖校验报错，改用： ./node_modules/.bin/vite
```
如后端不在默认地址，设 `frontend/.env` 的 `VITE_API_BASE_URL=http://localhost:8000`。

**3. 监管测试站**：
```bash
cd regulatory-test-site
pnpm install
./node_modules/.bin/next dev -p 3001    # http://localhost:3001
# 注意：本机 `pnpm dev`/`pnpm build` 会因严格依赖校验(忽略 sharp 构建脚本)失败，
# 直接用 ./node_modules/.bin/next 可绕开；Vercel 部署不受影响。
```

## 部署监管测试站到 Vercel

1. 在 Vercel 新建项目，Root Directory 选 `regulatory-test-site`（或单独仓库）。
2. （推荐）加 Upstash Redis：Vercel Marketplace 装 Upstash，或在 upstash.com 建免费库，把 `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` 填进 Vercel 环境变量。不配则用内存回退（冷启动会丢数据，演示前先发布几条即可）。
3. 部署后拿到公网地址，回填本地后端 `.env` 的 `REGULATORY_TEST_SITE_URL`。

> 主应用（Python 后端 + Vite 前端）**明天本地跑**。因正式后端依赖 torch/bge-m3（>1GB），不适配 Vercel serverless；主应用上 Vercel 属后续单独课题。

## 演示前自检

后端起来后可再跑一次真实 Opus 冒烟（会消耗少量额度）：
```bash
curl http://localhost:8000/api/v1/debug/llm          # 返回一句中文即 key/网关正常
curl -X POST http://localhost:8000/api/v1/demo/ask \
  -H "Content-Type: application/json" \
  -d '{"doc_text":"===== Page 1 =====\n地址证明有效期不得超过3个月。","question":"有效期多久？"}'
# 期望：answer 命中“3个月”，citations 含 page:1
```
> **已用真实 Opus（Sino-ai 环境）端到端验证通过**：`/debug/llm` 正常返回；`/demo/ask` 返回正确答案 + 精确到页的引文；`/demo/regulatory/analyze` 正确识别推送与文档冲突并给出带页码的修改建议。此外 `/regulatory/updates` 代理、前端 `tsc`+`vite build`、测试站 `next build`、测试站 publish/list/CORS 均已验证。

## 演示语料（已备好，强关联）

围绕 SFC《反洗钱及反恐怖分子资金筹集指引》的「2021 旧版 → 2023.06 修订」时间线：

- **上传文档**（模拟内部政策）：`docs/demo/assets/demo_internal_aml_policy_v2022_TC.pdf`
  —— 繁体、2 页、署名「盛富證券有限公司（示範）」的内部 AML/KYC 政策，按 2021 旧规写（PEP 一律持续强化不设解除、电汇 T+1、无 VA 专章等）。
  用 `scripts/generate_demo_policy_pdf.py` 生成（Sino-ai 环境需 `reportlab`，已装；字体用 `msjh.ttc` 嵌入 TTF —— **勿改回 CID 字体 MSung-Light，会导致文本层提取乱码**）。
- **监管推送**（贴到测试站）：`docs/demo/assets/regulatory-push_23EC21_TC.md`
  —— 基于 SFC 2023-05-24 通函（refNo 23EC21）整理，含现成标题/正文 + 预期改进点对照表。
- **真实来源**：[SFC AML/CFT 页面](https://www.sfc.hk/en/Rules-and-standards/Anti-money-laundering-and-counter-financing-of-terrorism)、[2021 旧版指引](https://www.sfc.hk/-/media/EN/assets/components/codes/files-current/web/guidelines/guideline-on-anti-money-laundering-and-counter-financing-of-terrorism-for-licensed-corporations/AML-Guideline-for-LCs_Eng_30-Sep-2021.pdf)、[2023.06 新版](https://www.sfc.hk/-/media/EN/assets/components/codes/files-current/web/guidelines/guideline-on-anti-money-laundering-and-counter-financing-of-terrorism-for-licensed-corporations/AML-Guideline-for-LCs-and-SFC-licensed-VASPs_Eng_1-Jun-2023.pdf)、[通函 23EC21](https://apps.sfc.hk/edistributionWeb/api/circular/openFile?lang=EN&refNo=23EC21)。

> 已用真实 Opus 实测该语料：问「对曾任政治人物如何处理」→ 正确引用第 1 页；发布上述推送 → AI 摘要 + 5 条精准修改建议（PEP 豁免、定义更新、电汇时限 T+1→即时、VA 专章、依据更新），全部对到正确章节页码。

## 现场演示脚本（5-8 分钟）

1. 打开演示前端，**上传一份文字型 policy PDF** → 右侧渲染出 PDF，显示页数/字符数。
2. 在「文档问答」提问（如“地址证明有效期是多久？”）→ 得到答案 + `[1] 第 n 页` 引用 chip。
3. **点引用 chip** → 右侧 PDF 跳到该页并高亮引文段落。
4. 切到**监管测试站**，「发布」一条监管推送（如收紧地址证明有效期）。
5. 数秒内演示前端「监管雷达」弹通知并出现该条 → 点「分析对当前文档的影响」→ 展示 AI 摘要 + 相关性 + 对当前文档的具体改进建议（建议带页码 chip，可跳转）。

## 已知取舍 / 兜底

- 引文高亮基于文本层子串匹配，个别引文可能搜不到 → **降级为只跳页不高亮**，不影响演示。
- 扫描件/图片型 PDF 抽不出文本（无 OCR）→ 用文字型 PDF。
- 文档过长按 `MAX_DOC_CHARS`（12 万字符）截断。
- 网络/模型抖动兜底：演示前录一段屏 + 预置好测试站的几条推送。
