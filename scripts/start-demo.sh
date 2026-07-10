#!/usr/bin/env bash
# One-command launcher for the demo (Windows / Git Bash).
#
#   ./scripts/start-demo.sh
#
# Starts three servers with a clean port state, streams their logs, and shuts
# them all down on Ctrl+C. See docs/demo/DEMO-NOTES.zh-CN.md.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Backend interpreter: prefer the project's conda env `Sino-ai`, auto-detecting
# common install locations so the script works on any machine (not just the
# original author's). Override with DEMO_PYTHON if your env lives elsewhere.
detect_python() {
  if [ -n "${DEMO_PYTHON:-}" ] && [ -x "$DEMO_PYTHON" ]; then
    echo "$DEMO_PYTHON"; return
  fi
  local candidates=(
    "/c/Users/$USER/anaconda3/envs/Sino-ai/python.exe"
    "/c/Users/$USERNAME/anaconda3/envs/Sino-ai/python.exe"
    "/c/ProgramData/anaconda3/envs/Sino-ai/python.exe"
    "/c/Users/$USER/anaconda3/python.exe"
    "/c/ProgramData/anaconda3/python.exe"
    "$(command -v python 2>/dev/null)"
    "$(command -v python3 2>/dev/null)"
  )
  for p in "${candidates[@]}"; do
    [ -n "$p" ] && [ -x "$p" ] && echo "$p" && return
  done
}
PYTHON="$(detect_python)"

BACKEND_PORT=8000
FRONTEND_PORT=5173
TESTSITE_PORT=3001

kill_port() {
  local port="$1"
  local pids
  pids=$(netstat -ano 2>/dev/null | grep -E ":${port}\b" | grep LISTENING | awk '{print $NF}' | sort -u)
  for pid in $pids; do
    [ -n "$pid" ] && taskkill //PID "$pid" //F >/dev/null 2>&1 && echo "  freed port $port (killed PID $pid)"
  done
}

kill_orphan_uvicorn() {
  # A stale uvicorn serving our app can keep holding the port. Kill only python
  # processes that run *our* app (matched by 'app.main') — narrow on purpose so
  # unrelated python/multiprocessing work is left alone.
  powershell.exe -NoProfile -Command \
    "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -like '*app.main*' } | ForEach-Object { Stop-Process -Id \$_.ProcessId -Force -ErrorAction SilentlyContinue }" \
    >/dev/null 2>&1 || true
}

echo "==> Cleaning stale processes on ports $BACKEND_PORT / $FRONTEND_PORT / $TESTSITE_PORT"
kill_port "$BACKEND_PORT"; kill_port "$FRONTEND_PORT"; kill_port "$TESTSITE_PORT"
kill_orphan_uvicorn
sleep 1

if [ -z "$PYTHON" ] || { [ ! -x "$PYTHON" ] && ! command -v "$PYTHON" >/dev/null 2>&1; }; then
  echo "!! Python not found."
  echo "   Install conda + create env 'Sino-ai', or set DEMO_PYTHON to your python.exe, e.g.:"
  echo "   DEMO_PYTHON=/c/Users/<you>/anaconda3/envs/Sino-ai/python.exe ./scripts/start-demo.sh"
  exit 1
fi

# Best-effort: print this machine's LAN IPv4 so you can hand the URL to colleagues.
LAN_IP="$(powershell.exe -NoProfile -Command "(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { \$_.IPAddress -notlike '127.*' -and \$_.IPAddress -notlike '169.*' -and \$_.InterfaceAlias -notlike '*Loopback*' -and \$_.InterfaceAlias -notlike '*vEthernet*' } | Select-Object -First 1).IPAddress" 2>/dev/null | tr -d '\r' | tr -d ' ')"

PIDS=()
cleanup() {
  echo ""
  echo "==> Shutting down demo servers..."
  for pid in "${PIDS[@]}"; do kill "$pid" >/dev/null 2>&1; done
  kill_port "$BACKEND_PORT"; kill_port "$FRONTEND_PORT"; kill_port "$TESTSITE_PORT"
  echo "    done."
  exit 0
}
trap cleanup INT TERM

# NOTE: intentionally NO --reload. uvicorn --reload forks a child worker; when
# this script is killed, that child can be orphaned and keep holding the port
# while serving stale code. A single process starts fresh and dies cleanly.
echo "==> [1/3] Backend (FastAPI + Opus)  http://localhost:$BACKEND_PORT"
( cd "$ROOT/backend" && "$PYTHON" -m uvicorn app.main:app --port "$BACKEND_PORT" ) \
  > "$LOG_DIR/backend.log" 2>&1 &
PIDS+=($!)

echo "==> [2/3] Regulatory test site      http://localhost:$TESTSITE_PORT"
( cd "$ROOT/regulatory-test-site" && ./node_modules/.bin/next dev -p "$TESTSITE_PORT" ) \
  > "$LOG_DIR/testsite.log" 2>&1 &
PIDS+=($!)

echo "==> [3/3] Frontend (Vite)           http://localhost:$FRONTEND_PORT"
( cd "$ROOT/frontend" && ./node_modules/.bin/vite --port "$FRONTEND_PORT" ) \
  > "$LOG_DIR/frontend.log" 2>&1 &
PIDS+=($!)

echo ""
echo "==> Starting up... (logs: tmp/demo-logs/*.log)"
sleep 6
echo ""
echo "======================================================================"
echo "  本机访问      : http://localhost:$FRONTEND_PORT"
if [ -n "$LAN_IP" ]; then
  echo "  同事访问(内网): http://$LAN_IP:$FRONTEND_PORT"
  echo "                  ↑ 把这个链接发给同内网的同事"
else
  echo "  (未能自动检测内网 IP；同事请用本机的内网 IP + :$FRONTEND_PORT 访问)"
fi
echo "  监管测试站    : http://localhost:$TESTSITE_PORT"
echo "  后端 API 文档 : http://localhost:$BACKEND_PORT/docs"
echo "----------------------------------------------------------------------"
echo "  上传 PDF : docs/demo/assets/demo_internal_aml_policy_v2022_TC.pdf"
echo "  推送文本 : docs/demo/assets/regulatory-push_23EC21_TC.md"
echo "  经测试站 WEB 表单发布（不要用 curl，CJK 会乱码）。"
echo "======================================================================"
echo "  Ctrl+C 停止全部服务。"
echo ""

# Stream all logs until Ctrl+C.
tail -f "$LOG_DIR/backend.log" "$LOG_DIR/frontend.log" "$LOG_DIR/testsite.log" &
PIDS+=($!)
wait
