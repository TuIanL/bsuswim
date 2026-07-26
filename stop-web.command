#!/bin/zsh
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-5174}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
PID_FILE="$ROOT_DIR/.web-dev.pid"
BACKEND_PID_FILE="$ROOT_DIR/.backend-dev.pid"
LOG_FILE="$ROOT_DIR/.web-dev.log"
BACKEND_LOG_FILE="$ROOT_DIR/.backend-dev.log"

echo "== 智泳云枢 Web 关闭脚本 =="
echo "项目目录: $ROOT_DIR"
echo

STOPPED=0

# ── 关闭前端进程 ──
if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    echo "正在关闭前端进程 PID: $PID"
    kill "$PID" 2>/dev/null || true

    for i in {1..10}; do
      if ! kill -0 "$PID" 2>/dev/null; then
        STOPPED=1
        break
      fi
      sleep 1
    done

    if kill -0 "$PID" 2>/dev/null; then
      echo "前端进程未正常退出，正在强制关闭..."
      kill -9 "$PID" 2>/dev/null || true
      STOPPED=1
    fi
  fi
  rm -f "$PID_FILE"
fi

# ── 关闭后端进程 ──
if [ -f "$BACKEND_PID_FILE" ]; then
  BE_PID="$(cat "$BACKEND_PID_FILE")"
  if kill -0 "$BE_PID" 2>/dev/null; then
    echo "正在关闭后端进程 PID: $BE_PID"
    kill "$BE_PID" 2>/dev/null || true

    for i in {1..10}; do
      if ! kill -0 "$BE_PID" 2>/dev/null; then
        STOPPED=1
        break
      fi
      sleep 1
    done

    if kill -0 "$BE_PID" 2>/dev/null; then
      echo "后端进程未正常退出，正在强制关闭..."
      kill -9 "$BE_PID" 2>/dev/null || true
      STOPPED=1
    fi
  fi
  rm -f "$BACKEND_PID_FILE"
fi

# ── 清理残留端口占用 ──
PORT_PIDS="$(lsof -ti tcp:"$PORT" 2>/dev/null || true)"
if [ -n "$PORT_PIDS" ]; then
  echo "发现仍有进程占用端口 $PORT，正在关闭:"
  echo "$PORT_PIDS"
  echo "$PORT_PIDS" | xargs kill 2>/dev/null || true
  STOPPED=1
fi

BACKEND_PORT_PIDS="$(lsof -ti tcp:"$BACKEND_PORT" 2>/dev/null || true)"
if [ -n "$BACKEND_PORT_PIDS" ]; then
  echo "发现仍有进程占用端口 $BACKEND_PORT，正在关闭:"
  echo "$BACKEND_PORT_PIDS"
  echo "$BACKEND_PORT_PIDS" | xargs kill 2>/dev/null || true
  STOPPED=1
fi

if [ "$STOPPED" -eq 1 ]; then
  echo
  echo "前后端服务已关闭。"
else
  echo "没有发现正在运行的服务。"
fi

echo
echo "日志文件保留在: $LOG_FILE"
echo "                $BACKEND_LOG_FILE"
echo "按任意键退出..."
read -k 1
