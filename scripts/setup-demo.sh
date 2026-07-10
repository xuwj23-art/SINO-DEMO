#!/usr/bin/env bash
# ============================================================
# One-time setup for the demo on a fresh machine (e.g. office intern PC).
# Run ONCE after `git clone`. It installs backend + frontend dependencies and
# checks the API key, then tells you how to start the demo.
#
#   ./scripts/setup-demo.sh
#
# Prerequisites (the deployment guide walks you through these):
#   - Python 3.12 (or conda env `Sino-ai`)
#   - Node.js 18+
#   - ANTHROPIC_API_KEY known (will be placed in backend/.env)
# ============================================================
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "============================================================"
echo "  Demo 一次性环境准备"
echo "============================================================"
echo ""

# --- 1. Detect Python -------------------------------------------------------
detect_python() {
  if [ -n "${DEMO_PYTHON:-}" ] && [ -x "$DEMO_PYTHON" ]; then echo "$DEMO_PYTHON"; return; fi
  local candidates=(
    "/c/Users/$USER/anaconda3/envs/Sino-ai/python.exe"
    "/c/Users/$USERNAME/anaconda3/envs/Sino-ai/python.exe"
    "/c/ProgramData/anaconda3/envs/Sino-ai/python.exe"
    "/c/Users/$USER/anaconda3/python.exe"
    "/c/ProgramData/anaconda3/python.exe"
    "$(command -v python 2>/dev/null)"
    "$(command -v python3 2>/dev/null)"
  )
  for p in "${candidates[@]}"; do [ -n "$p" ] && [ -x "$p" ] && echo "$p" && return; done
}
PYTHON="$(detect_python)"
if [ -z "$PYTHON" ]; then
  echo "!! 找不到 Python。请先装 Python 3.12，或设置 DEMO_PYTHON 指向你的 python.exe"
  exit 1
  fi
echo "[1/4] Python: $PYTHON"
echo ""

# --- 2. Backend deps (lightweight demo subset) ------------------------------
echo "[2/4] 安装后端依赖（精简版，约 100-200MB，跳过 torch 等）..."
"$PYTHON" -m pip install -r "$ROOT/backend/requirements-demo.txt" -q
if [ $? -ne 0 ]; then echo "!! 后端依赖安装失败"; exit 1; fi
echo "      完成。"
echo ""

# --- 3. Frontend deps -------------------------------------------------------
echo "[3/4] 安装前端依赖（frontend + regulatory-test-site，首次较慢）..."
( cd "$ROOT/frontend" && npm install --silent 2>/dev/null || npm install )
if [ $? -ne 0 ]; then echo "!! frontend 依赖安装失败"; exit 1; fi
( cd "$ROOT/regulatory-test-site" && npm install --silent 2>/dev/null || npm install )
if [ $? -ne 0 ]; then echo "!! regulatory-test-site 依赖安装失败"; exit 1; fi
echo "      完成。"
echo ""

# --- 4. API key check -------------------------------------------------------
echo "[4/4] 检查 API key..."
ENV_FILE="$ROOT/backend/.env"
if [ ! -f "$ENV_FILE" ]; then
  # Bootstrap from the example if present, then warn.
  [ -f "$ROOT/.env.example" ] && cp "$ROOT/.env.example" "$ENV_FILE" 2>/dev/null || true
fi
if [ -f "$ENV_FILE" ] && grep -q "ANTHROPIC_API_KEY=.\+" "$ENV_FILE" 2>/dev/null && ! grep -q "ANTHROPIC_API_KEY=your_" "$ENV_FILE" 2>/dev/null; then
  echo "      backend/.env 已配置 ANTHROPIC_API_KEY。"
else
  echo "!! 还没配置 ANTHROPIC_API_KEY。"
  echo "   请编辑 backend/.env，填入："
  echo "      ANTHROPIC_API_KEY=sk-ant-...（你的 key）"
  echo "      ANTHROPIC_BASE_URL=https://你的网关地址  （如果走 packyapi 网关）"
  echo "   配好后再运行 ./scripts/start-demo.sh"
fi
echo ""

echo "============================================================"
echo "  环境准备完成！"
echo "------------------------------------------------------------"
echo "  启动 demo :  ./scripts/start-demo.sh"
echo "  启动后会打印本机内网 IP，把 http://<内网IP>:5173 发给同事即可。"
echo "============================================================"
