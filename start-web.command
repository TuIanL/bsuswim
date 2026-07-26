#!/bin/zsh
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend-vue"
BACKEND_DIR="$ROOT_DIR/backend"
PORT="${PORT:-5174}"
BACKEND_PORT="${BACKEND_PORT:-8001}"
HOST="127.0.0.1"
PID_FILE="$ROOT_DIR/.web-dev.pid"
BACKEND_PID_FILE="$ROOT_DIR/.backend-dev.pid"
LOG_FILE="$ROOT_DIR/.web-dev.log"
BACKEND_LOG_FILE="$ROOT_DIR/.backend-dev.log"
URL="http://$HOST:$PORT"
BACKEND_URL="http://$HOST:$BACKEND_PORT"

echo "== 智泳云枢 Web 启动脚本 =="
echo "项目目录: $ROOT_DIR"
echo "前端地址: $URL"
echo "后端地址: $BACKEND_URL"
echo

# ── 1. Docker postgres ──
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    echo "正在启动本地数据库容器 postgres..."
    docker compose -f "$ROOT_DIR/docker-compose.yml" up -d postgres
    echo "等待 postgres 就绪..."
    for i in {1..20}; do
      if docker exec bsuswim-postgres pg_isready -U swim >/dev/null 2>&1; then
        echo "postgres 已就绪"
        break
      fi
      sleep 1
    done
    echo
  else
    echo "Docker 当前没有运行，已跳过数据库容器启动。"
    echo "后端需要数据库才能运行，请先打开 Docker Desktop。"
    echo
  fi
else
  echo "未找到 docker 命令，已跳过数据库容器启动。"
  echo
fi

# ── 2. Alembic migration ──
if [ -d "$BACKEND_DIR" ]; then
  echo "正在检查数据库 migration..."
  cd "$BACKEND_DIR"
  if command -v uv >/dev/null 2>&1; then
    uv run alembic upgrade head 2>/dev/null || echo "alembic migration 跳过（可能未配置）"
  else
    python -m alembic upgrade head 2>/dev/null || echo "alembic migration 跳过（可能未配置）"
  fi
  if command -v uv >/dev/null 2>&1; then
    uv run python scripts/seed_dev_user.py 2>/dev/null || echo "开发账号 seed 跳过（可能未配置）"
  else
    python scripts/seed_dev_user.py 2>/dev/null || echo "开发账号 seed 跳过（可能未配置）"
  fi
  echo
fi

# ── 3. Check existing processes ──
if [ -f "$PID_FILE" ] && [ -f "$BACKEND_PID_FILE" ]; then
  OLD_FE_PID="$(cat "$PID_FILE")"
  OLD_BE_PID="$(cat "$BACKEND_PID_FILE")"
  FE_RUNNING=0
  BE_RUNNING=0
  kill -0 "$OLD_FE_PID" 2>/dev/null && FE_RUNNING=1
  kill -0 "$OLD_BE_PID" 2>/dev/null && BE_RUNNING=1
  if [ "$FE_RUNNING" -eq 1 ] && [ "$BE_RUNNING" -eq 1 ]; then
    echo "前后端已经在运行。"
    echo "  前端 PID: $OLD_FE_PID"
    echo "  后端 PID: $OLD_BE_PID"
    open "$URL" >/dev/null 2>&1 || true
    echo "按任意键退出..."
    read -k 1
    exit 0
  fi
  rm -f "$PID_FILE" "$BACKEND_PID_FILE"
fi

# ── 4. Start backend ──
if [ -d "$BACKEND_DIR" ]; then
  echo "正在启动 FastAPI 后端..."
  cd "$BACKEND_DIR"
  if command -v uv >/dev/null 2>&1; then
    nohup uv run uvicorn app.main:app --host "$HOST" --port "$BACKEND_PORT" --reload > "$BACKEND_LOG_FILE" 2>&1 &
  else
    nohup python -m uvicorn app.main:app --host "$HOST" --port "$BACKEND_PORT" --reload > "$BACKEND_LOG_FILE" 2>&1 &
  fi
  BACKEND_PID=$!
  echo "$BACKEND_PID" > "$BACKEND_PID_FILE"
  echo "后端 PID: $BACKEND_PID"
  echo "后端日志: $BACKEND_LOG_FILE"

  echo "等待后端就绪..."
  for i in {1..30}; do
    if curl -fsS "$BACKEND_URL/health" >/dev/null 2>&1; then
      echo "后端已就绪"
      break
    fi
    sleep 1
  done
  echo
fi

# ── 5. Start frontend ──
if [ ! -d "$FRONTEND_DIR" ]; then
  echo "找不到 frontend-vue 目录: $FRONTEND_DIR"
  echo "按任意键退出..."
  read -k 1
  exit 1
fi

cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
  echo "首次启动：正在安装前端依赖..."
  npm install
  echo
fi

echo "正在启动 Vue/Vite 开发服务器..."
VITE_API_BASE_URL="$BACKEND_URL" nohup npm run dev -- --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

echo "前端 PID: $SERVER_PID"
echo "前端日志: $LOG_FILE"
echo
echo "等待前端就绪..."

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

echo "前端启动时间较长，请查看日志:"
echo "$LOG_FILE"
echo
echo "也可以稍后手动打开: $URL"
echo "按任意键退出..."
read -k 1
