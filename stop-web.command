#!/bin/zsh
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-5173}"
PID_FILE="$ROOT_DIR/.web-dev.pid"
LOG_FILE="$ROOT_DIR/.web-dev.log"

echo "== 智泳云枢 Web 关闭脚本 =="
echo "项目目录: $ROOT_DIR"
echo

STOPPED=0

if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null; then
    echo "正在关闭 PID: $PID"
    kill "$PID" 2>/dev/null || true

    for i in {1..10}; do
      if ! kill -0 "$PID" 2>/dev/null; then
        STOPPED=1
        break
      fi
      sleep 1
    done

    if kill -0 "$PID" 2>/dev/null; then
      echo "进程未正常退出，正在强制关闭..."
      kill -9 "$PID" 2>/dev/null || true
      STOPPED=1
    fi
  fi
  rm -f "$PID_FILE"
fi

PORT_PIDS="$(lsof -ti tcp:"$PORT" 2>/dev/null || true)"
if [ -n "$PORT_PIDS" ]; then
  echo "发现仍有进程占用端口 $PORT，正在关闭:"
  echo "$PORT_PIDS"
  echo "$PORT_PIDS" | xargs kill 2>/dev/null || true
  STOPPED=1
fi

if [ "$STOPPED" -eq 1 ]; then
  echo
  echo "Web 服务已关闭。"
else
  echo "没有发现正在运行的 Web 服务。"
fi

echo
echo "日志文件保留在: $LOG_FILE"
echo "按任意键退出..."
read -k 1
