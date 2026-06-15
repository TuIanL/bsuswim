#!/bin/zsh
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
PORT="${PORT:-3000}"
HOST="127.0.0.1"
PID_FILE="$ROOT_DIR/.web-dev.pid"
LOG_FILE="$ROOT_DIR/.web-dev.log"
URL="http://$HOST:$PORT"

echo "== 智泳云枢 Web 启动脚本 =="
echo "项目目录: $ROOT_DIR"
echo "访问地址: $URL"
echo

if [ ! -d "$FRONTEND_DIR" ]; then
  echo "找不到 frontend 目录: $FRONTEND_DIR"
  echo "按任意键退出..."
  read -k 1
  exit 1
fi

if [ -f "$PID_FILE" ]; then
  OLD_PID="$(cat "$PID_FILE")"
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Web 已经在运行，PID: $OLD_PID"
    open "$URL" >/dev/null 2>&1 || true
    echo "按任意键退出..."
    read -k 1
    exit 0
  fi
  rm -f "$PID_FILE"
fi

cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
  echo "首次启动：正在安装前端依赖..."
  npm install
  echo
fi

echo "正在启动 Next.js 开发服务器..."
nohup npm run dev -- --hostname "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

echo "PID: $SERVER_PID"
echo "日志: $LOG_FILE"
echo
echo "等待服务就绪..."

for i in {1..30}; do
  if curl -fsS "$URL" >/dev/null 2>&1; then
    echo "启动成功，正在打开浏览器..."
    open "$URL" >/dev/null 2>&1 || true
    echo
    echo "关闭时请双击 stop-web.command。"
    echo "按任意键退出此窗口，服务会继续运行。"
    read -k 1
    exit 0
  fi
  sleep 1
done

echo "服务启动时间较长，请查看日志:"
echo "$LOG_FILE"
echo
echo "也可以稍后手动打开: $URL"
echo "按任意键退出..."
read -k 1
