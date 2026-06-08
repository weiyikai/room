#!/usr/bin/env bash
# ============================================================
# 一键部署脚本 — 动环安全评估管理系统
# 用法: ./deploy.sh [选项]
# ============================================================
set -euo pipefail

# ====================== 颜色输出 ======================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; }

# ====================== 配置变量 ======================
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

ENV_FILE=".env"
NACOS_CONFIG_FILE="nacos.yaml"
NACOS_DATA_ID="django-room-settings.yaml"
NACOS_GROUP="${NACOS_GROUP:-DEFAULT_GROUP}"
NACOS_PORT="${NACOS_PORT:-8848}"
BACKEND_CONTAINER="room"
NACOS_CONTAINER="nacos"
COMPOSE_FILE="docker-compose.yml"

# ====================== 工具函数 ======================

# 检测 docker compose 命令（V2 优先）
detect_compose_cmd() {
    if docker compose version &>/dev/null 2>&1; then
        echo "docker compose"
    elif command -v docker-compose &>/dev/null 2>&1; then
        echo "docker-compose"
    else
        echo ""
    fi
}

COMPOSE_CMD=$(detect_compose_cmd)

# 检查前置条件
check_prerequisites() {
    info "正在检查运行环境..."

    if ! command -v docker &>/dev/null; then
        error "未检测到 Docker，请先安装 Docker"
        exit 1
    fi
    success "Docker 已安装: $(docker --version)"

    if [ -z "$COMPOSE_CMD" ]; then
        error "未检测到 Docker Compose（docker compose 或 docker-compose），请先安装"
        exit 1
    fi
    success "Docker Compose 可用: $COMPOSE_CMD"

    # 检查 Docker 是否在运行
    if ! docker info &>/dev/null 2>&1; then
        error "Docker 服务未运行，请启动 Docker Desktop 或 Docker 服务"
        exit 1
    fi
    success "Docker 服务正在运行"

    # 检查 .env 文件
    if [ ! -f "$ENV_FILE" ]; then
        warn ".env 文件不存在，将从项目默认配置创建"
        cat > "$ENV_FILE" << 'EOF'
# .env 文件 — Docker Compose 环境变量
NACOS_SERVER_ADDR=nacos:8848

# Nacos 认证（需要时取消注释）
# NACOS_USERNAME=
# NACOS_PASSWORD=

# 切换分组只改这一行！
NACOS_GROUP=DEFAULT_GROUP
# NACOS_GROUP=DEV_GROUP
# NACOS_GROUP=PROD_GROUP
EOF
        success "已创建 .env 文件，请根据需要修改后重新运行"
        exit 0
    fi
    success ".env 文件存在"

    # 加载 .env 获取 NACOS_GROUP
    if [ -f "$ENV_FILE" ]; then
        # shellcheck disable=SC2046
        export $(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$' | xargs 2>/dev/null || true)
    fi
}

# 等待 Nacos 健康
wait_for_nacos() {
    local max_attempts=30
    local attempt=1

    info "等待 Nacos 启动就绪（最多 ${max_attempts} 次尝试，每次 2s）..."

    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "http://localhost:${NACOS_PORT}/nacos/actuator/health" >/dev/null 2>&1; then
            success "Nacos 已就绪 (http://localhost:${NACOS_PORT}/nacos)"
            return 0
        fi
        printf "."
        sleep 2
        attempt=$((attempt + 1))
    done

    error "Nacos 启动超时，请检查 Docker 日志: docker logs ${NACOS_CONTAINER}"
    return 1
}

# 等待后端容器就绪
wait_for_backend() {
    local max_attempts=15
    local attempt=1

    info "等待后端容器启动就绪..."

    while [ $attempt -le $max_attempts ]; do
        if docker ps --format '{{.Names}}' --filter "name=^${BACKEND_CONTAINER}$" | grep -q .; then
            # 容器已运行，再等一下让 Django 完全启动
            sleep 3
            success "后端容器已就绪"
            return 0
        fi
        printf "."
        sleep 2
        attempt=$((attempt + 1))
    done

    error "后端容器启动超时，请检查: docker logs ${BACKEND_CONTAINER}"
    return 1
}

# 容器内执行命令
run_in_backend() {
    local cmd="$1"
    local desc="$2"
    info "$desc"
    if docker exec "$BACKEND_CONTAINER" sh -c "$cmd"; then
        success "$desc — 完成"
    else
        error "$desc — 失败，请检查容器日志"
        return 1
    fi
}

# ====================== 子命令实现 ======================

# 推送配置到 Nacos
cmd_push_config() {
    info "正在推送配置到 Nacos..."

    if [ ! -f "$NACOS_CONFIG_FILE" ]; then
        error "配置文件 $NACOS_CONFIG_FILE 不存在，请先创建"
        exit 1
    fi

    # 确保 Nacos 在运行
    if ! curl -s -f "http://localhost:${NACOS_PORT}/nacos/actuator/health" >/dev/null 2>&1; then
        error "Nacos 未运行，请先启动 Nacos: $COMPOSE_CMD up -d nacos"
        exit 1
    fi

    # 使用 Nacos Open API 推送配置
    local content
    content=$(cat "$NACOS_CONFIG_FILE")

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "http://localhost:${NACOS_PORT}/nacos/v1/cs/configs" \
        --data-urlencode "dataId=${NACOS_DATA_ID}" \
        --data-urlencode "group=${NACOS_GROUP}" \
        --data-urlencode "content=${content}" \
        --data-urlencode "type=yaml")

    if [ "$http_code" = "200" ]; then
        success "配置已推送到 Nacos (dataId=${NACOS_DATA_ID}, group=${NACOS_GROUP})"
    else
        error "配置推送失败，HTTP 状态码: ${http_code}"
        exit 1
    fi
}

# 构建后端镜像
cmd_build() {
    info "正在构建后端 Docker 镜像..."
    $COMPOSE_CMD build backend
    success "后端镜像构建完成"
}

# 数据库迁移
cmd_migrate() {
    # 确保后端容器在运行
    if ! docker ps --format '{{.Names}}' --filter "name=^${BACKEND_CONTAINER}$" | grep -q .; then
        error "后端容器未运行，请先启动: ./deploy.sh"
        exit 1
    fi
    run_in_backend "python manage.py migrate" "数据库迁移 (migrate)"
}

# 收集静态文件
cmd_collect_static() {
    if ! docker ps --format '{{.Names}}' --filter "name=^${BACKEND_CONTAINER}$" | grep -q .; then
        error "后端容器未运行，请先启动: ./deploy.sh"
        exit 1
    fi
    run_in_backend "python manage.py collectstatic --noinput" "静态文件收集 (collectstatic)"
}

# 查看状态
cmd_status() {
    info "服务运行状态:"
    echo ""
    $COMPOSE_CMD ps
    echo ""
    info "容器资源使用:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        "$NACOS_CONTAINER" "$BACKEND_CONTAINER" "nginx" 2>/dev/null || true
}

# 停止并清理
cmd_down() {
    warn "正在停止所有服务..."
    $COMPOSE_CMD down
    success "所有服务已停止并清理"
}

# 完整部署
cmd_deploy() {
    local do_build=false

    # 解析构建选项
    if [ "${1:-}" = "--build" ]; then
        do_build=true
    fi

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║   动环安全评估管理系统 — 一键部署脚本   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""

    # ---- Step 1: 环境检查 ----
    info "Step 1/7: 环境检查"
    check_prerequisites
    echo ""

    # ---- Step 2: 启动 Nacos ----
    info "Step 2/7: 启动 Nacos 服务注册中心"
    $COMPOSE_CMD up -d nacos
    wait_for_nacos || exit 1
    echo ""

    # ---- Step 3: 推送配置 ----
    info "Step 3/7: 推送配置到 Nacos"
    if [ -f "$NACOS_CONFIG_FILE" ]; then
        cmd_push_config
    else
        warn "nacos.yaml 不存在，跳过配置推送（将使用本地默认配置）"
    fi
    echo ""

    # ---- Step 4: 构建镜像 ----
    info "Step 4/7: 构建后端镜像"
    # 检查是否需要构建
    if $do_build || ! docker image inspect room-backend:latest &>/dev/null 2>&1; then
        cmd_build
    else
        success "镜像 room-backend:latest 已存在，跳过构建（使用 --build 强制重建）"
    fi
    echo ""

    # ---- Step 5: 启动所有服务 ----
    info "Step 5/7: 启动后端 + Nginx"
    $COMPOSE_CMD up -d backend nginx
    wait_for_backend || exit 1
    echo ""

    # ---- Step 6: 数据库迁移 ----
    info "Step 6/7: 数据库迁移"
    cmd_migrate || warn "迁移失败，可能已经是最新版本（可稍后手动执行: ./deploy.sh --migrate）"
    echo ""

    # ---- Step 7: 收集静态文件 ----
    info "Step 7/7: 收集静态文件"
    cmd_collect_static || warn "静态文件收集失败（可稍后手动执行: ./deploy.sh --collect-static）"
    echo ""

    # ---- 部署完成 ----
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║          🎉 部署完成！                   ║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║                                          ║${NC}"
    echo -e "${GREEN}║  主页:    http://localhost               ║${NC}"
    echo -e "${GREEN}║  Admin:   http://localhost/admin         ║${NC}"
    echo -e "${GREEN}║  Nacos:   http://localhost:${NACOS_PORT}/nacos  ║${NC}"
    echo -e "${GREEN}║  API:     http://localhost:8888/api       ║${NC}"
    echo -e "${GREEN}║                                          ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""

    # 显示最终状态
    cmd_status
}

# 显示帮助
cmd_help() {
    echo ""
    echo "动环安全评估管理系统 — 一键部署脚本"
    echo ""
    echo "用法: ./deploy.sh [选项]"
    echo ""
    echo "选项:"
    echo "  (无参数)          完整部署流程（检查环境 → 启动Nacos → 推送配置 →"
    echo "                    构建镜像 → 启动服务 → migrate → collectstatic）"
    echo "  --build           重新构建镜像后完整部署"
    echo "  --push-config     仅推送 nacos.yaml 配置到 Nacos"
    echo "  --migrate         仅运行数据库迁移 (python manage.py migrate)"
    echo "  --collect-static  仅收集静态文件 (python manage.py collectstatic)"
    echo "  --status          查看所有服务运行状态"
    echo "  --down            停止并清理所有服务"
    echo "  --help            显示本帮助信息"
    echo ""
    echo "示例:"
    echo "  ./deploy.sh                  # 首次部署或日常重启"
    echo "  ./deploy.sh --build          # 修改代码后重新构建部署"
    echo "  ./deploy.sh --push-config    # 修改 nacos.yaml 后推送配置"
    echo "  ./deploy.sh --migrate        # 数据库模型变更后执行迁移"
    echo "  ./deploy.sh --down           # 停止所有服务"
    echo ""
}

# ====================== 主入口 ======================

main() {
    case "${1:-}" in
        --build)
            cmd_deploy --build
            ;;
        --push-config)
            check_prerequisites
            cmd_push_config
            ;;
        --migrate)
            cmd_migrate
            ;;
        --collect-static)
            cmd_collect_static
            ;;
        --status)
            cmd_status
            ;;
        --down)
            cmd_down
            ;;
        --help|-h|help)
            cmd_help
            ;;
        "")
            cmd_deploy
            ;;
        *)
            error "未知选项: $1"
            cmd_help
            exit 1
            ;;
    esac
}

main "${@}"
