# 内网部署指南（公司电脑常驻 demo）

> 目标：在一台公司电脑（如 intern 机）上把 demo 跑起来并常驻，同内网的同事通过
> `http://<这台电脑的内网IP>:5173` 访问，**零安装、零配置**，只需点链接。
>
> API key 只存在这台部署机上，不外泄给同事、不进 git，符合合规要求。

---

## 前置条件（你需要先准备好）

1. **demo 分支已推到 GitHub** —— 公司电脑靠 `git clone` 拉代码。如果还没推，在开发机上执行：
   ```bash
   git push origin demo
   ```
   （已确认提交不含任何 API key，可以安全推送。）

2. **ANTHROPIC_API_KEY** —— 你手上要有有效的 key（以及 packyapi 网关地址，如果走网关）。

3. **公司电脑的基本权限** —— 能装软件、能保持开机、能连公司内网。

---

## 第 1 步：装 Git（公司电脑）

如果公司电脑还没有 Git：

1. 打开 https://git-scm.com/download/win ，下载 **64-bit Git for Windows Setup**。
2. 双击安装，**一路默认即可**（安装时会自带 Git Bash，后面要用）。
3. 装完，在桌面空白处右键 → 看到 **「Git Bash Here」** 就说明装好了。

> 如果公司有 IT 限制装软件，请走公司内部的软件安装流程，或请 IT 协助。

---

## 第 2 步：装 Python 和 Node.js（公司电脑）

demo 后端要 Python 3.12，前端要 Node.js 18+。

### Python
推荐装 **Miniconda**（轻量）：
1. 打开 https://docs.conda.io/en/latest/miniconda.html ，下载 Windows 64-bit 安装包。
2. 安装时勾选 **「Add Miniconda to PATH」**（方便 Git Bash 找到）。
3. 装完后打开 **Git Bash**，创建专用环境：
   ```bash
   conda create -n Sino-ai python=3.12 -y
   ```

> 没有conda也行——直接装 Python 3.12（https://www.python.org/downloads/ ），安装时勾选 "Add to PATH"。
> 启动脚本会自动找到 python。

### Node.js
1. 打开 https://nodejs.org/ ，下载 **LTS 版**（18 或更高）。
2. 一路默认安装。

---

## 第 3 步：下载 demo 代码（公司电脑）

打开 **Git Bash**，选一个目录（比如 `D:\`），执行：

```bash
cd /d/
git clone https://github.com/xuwj23-art/Knowledge-Base-Management-System.git
cd Knowledge-Base-Management-System
git checkout demo          # ← 切到 demo 分支（关键！）
```

> clone 后**默认在 main 分支，必须切到 demo 分支**，否则拿不到演示代码。

---

## 第 4 步：配置 API key（关键）

```bash
cp .env.example backend/.env
```

然后用记事本（或 `nano backend/.env`）编辑 `backend/.env`，填入：

```
ANTHROPIC_API_KEY=sk-ant-...你的key...
ANTHROPIC_BASE_URL=https://你的packyapi网关地址     # 走网关才需要这行
```

> 这个 `.env` 文件已被 `.gitignore` 排除，不会被提交，key 只存在这台电脑。

---

## 第 5 步：一键安装依赖（首次，约 10-20 分钟）

在项目根目录的 Git Bash 里执行：

```bash
./scripts/setup-demo.sh
```

这个脚本会：
- 自动找到 Python（conda 环境或系统 Python）
- 装后端依赖（**精简版，跳过 torch 等约 2-3GB 的死依赖，只装约 200MB**）
- 装两个前端的 npm 依赖（frontend + regulatory-test-site）
- 检查 `.env` 里的 key 是否填好

看到「环境准备完成」就成功了。

---

## 第 6 步：启动 demo（每次开机后执行）

```bash
./scripts/start-demo.sh
```

启动后会打印一段提示，**重点看这一行**：

```
同事访问(内网): http://192.168.x.x:5173
                ↑ 把这个链接发给同内网的同事
```

这就是同事要用的链接。**保持这个 Git Bash 窗口开着**（关了 demo 就停了）。

---

## 第 7 步：放行 Windows 防火墙（同事连不上的话）

如果同事打开链接是「无法访问」，多半是 Windows 防火墙挡了 5173 端口：

1. 打开「控制面板」→「Windows Defender 防火墙」→「高级设置」
2. 左侧点「入站规则」→ 右侧「新建规则」
3. 选「端口」→ TCP → 特定端口填 `5173` → 「允许连接」→ 全选（域/专用/公用）→ 命名为 `demo-vite`
4. 完成

> 只需放行 **5173** 一个端口。后端(8000)和监管站(3001)只服务本机，不用对外。

---

## 第 8 步：让 demo 常驻（电脑开机自动跑）

最简单的办法：把启动命令设为**开机启动项**。

1. 按 `Win+R`，输入 `shell:startup` 回车，打开启动文件夹。
2. 在里面新建一个 `start-demo.bat`，内容：
   ```bat
   @echo off
   cd /d D:\Knowledge-Base-Management-System
   "C:\Program Files\Git\bin\bash.exe" ./scripts/start-demo.sh
   ```
   （路径按你实际 clone 的位置改）
3. 以后每次开机，demo 会自动启动。

> 进阶：也可以用 **nssm** 把它装成 Windows 服务，更隐蔽、更稳。需要的话再说。

---

## 同事访问说明（复制发给他们）

> 在浏览器打开：**http://<内网IP>:5173**（IP 地址我稍后发）
>
> - 建议用 Chrome / Edge
> - 演示时先点「上传 PDF」，选 demo 策略文件
> - 这是一个演示用的系统，不含任何真实客户资料
> - **API 调用会产生费用，请勿高频刷接口**

---

## 故障排查

| 现象 | 原因 / 解决 |
|---|---|
| `git clone` 慢/失败 | 公司网络问题，重试或用手机热点试；或让 IT 开 GitHub 访问 |
| `setup-demo.sh` 卡在装依赖 | npm 在国内慢，可设镜像：`npm config set registry https://registry.npmmirror.com` |
| 同事打开链接转圈/超时 | 防火墙没放行 5173，见第 7 步 |
| 同事能打开但「调用失败」 | 后端没起来，或 `.env` 的 key 没配好；看 `tmp/demo-logs/backend.log` |
| AI 回答一直转圈 | Opus 偶尔慢（10-40s），等一下；超过 2 分钟多半是 key/网关问题 |
| 重启后内网 IP 变了 | 公司 IP 若是动态分配，重启后可能换；重新看启动提示里的 IP 并更新给同事 |

---

## 安全说明

- **API key 只在部署机的 `backend/.env`**，不进 git、不发给同事。
- 同事通过浏览器访问，所有 AI 请求由部署机代发，**同事拿不到 key**。
- demo 全程使用**合成虚构数据**，不含真实客户、KYC、MNPI。
- 但：任何拿到链接的人都能用 demo 消耗 AI 额度。**链接只发需要的人，不要公开**。
