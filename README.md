# 合规知识库 · AI 助手（演示版）

一个面向金融合规场景的 RAG 知识库演示系统：单文档智能问答（带引用溯源）、监管动态雷达、
开户前 AML/KYC 初审、可疑交易实时预警、AI 客服，以及一键生成合规邮件。

> ⚠️ **这是一个演示原型（demo）**，不是生产系统。全部数据为**虚构合成数据**，不含任何真实
> 客户、KYC 或 MNPI 信息。公司名「盛富證券」为虚构演示主体。

---

## 演示功能

| 功能 | 说明 |
|---|---|
| 📄 文档问答 | 上传文字型 PDF，基于文档内容回答，每条回答附**页码引用 + 原文高亮**；证据不足时拒绝作答 |
| 📡 监管雷达 | 演示监管发布站推送新规 → 自动抓取 → AI 摘要 + 对现有政策的影响建议 + 存量客户影响面 |
| ✅ 开户初审 | 选一份合成客户申请，AI 依据政策生成 checklist 并逐项核对（含政策溯源） |
| 📈 交易监控 | 海量正常交易流水中实时捕捉可疑交易（"大海捞针"视觉）+ AI 风险研判 |
| 🎧 AI 客服 | 基于文档的客服问答，证据不足时转人工 |
| ✉️ 邮件生成 | 初审/交易场景一键生成繁体中文合规邮件草稿 |

## 技术栈

- **后端**：FastAPI + Anthropic Claude（通过 Model Gateway 网关）
- **前端**：React 19 + Vite + MUI 6（PDF 解析在浏览器端用 pdf.js）
- **监管测试站**：Next.js（独立小应用，模拟监管推送）
- **数据**：全合成虚构，无真实数据；无数据库依赖，无状态

---

## 快速开始

### 前置条件
- Python 3.12
- Node.js 18+
- 一个 Anthropic API Key（或兼容网关）

### 步骤

```bash
# 1. 克隆
git clone https://github.com/xuwj23-art/SINO-DEMO.git
cd SINO-DEMO

# 2. 配置 API key
cp .env.example backend/.env
# 编辑 backend/.env，填入 ANTHROPIC_API_KEY（和 ANTHROPIC_BASE_URL 如走网关）

# 3. 一键安装依赖（首次，约 10-20 分钟）
./scripts/setup-demo.sh

# 4. 启动
./scripts/start-demo.sh
```

启动后浏览器打开 `http://localhost:5173`。

📚 完整部署说明（含内网部署、防火墙、常驻）见
[`docs/demo/deploy-to-intranet-pc.zh-CN.md`](docs/demo/deploy-to-intranet-pc.zh-CN.md)。

---

## 项目结构

```
backend/                  FastAPI 后端（demo 服务 + LLM 网关封装）
  app/services/demo_*.py  五大演示功能的后端逻辑
  requirements-demo.txt   精简依赖（跳过 torch 等重库）
frontend/                 React + Vite 前端工作台
  src/components/         各功能面板组件
  src/data/               合成客户与交易流数据（虚构）
regulatory-test-site/     监管发布测试站（Next.js）
scripts/                  启动与部署脚本
docs/demo/                演示文档与部署指南
```

## 安全说明

- API Key 只配置在后端 `backend/.env`（已被 `.gitignore` 排除），不进仓库、不暴露前端。
- 所有演示数据为虚构合成，不含真实客户资料。
- 本演示**未实现**权限过滤、真实监管来源接入、OCR、SSO 等生产特性。

## 许可

仅供学习与演示参考。
