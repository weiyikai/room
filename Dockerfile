FROM python:3.10-slim
WORKDIR /app

# 复制依赖
COPY requirements.txt .
# 🔥 核心修改：安装 uv，并用 uv 安装依赖（替代原 pip）
RUN pip install --no-cache-dir uv && uv pip install --no-cache-dir --system -r requirements.txt

# 复制项目代码
COPY ./backend/room .

# 🔥 新增：构建镜像时自动收集所有静态文件（Admin+DRF样式）
RUN python manage.py collectstatic --noinput

# 启动命令
CMD ["python", "-m", "gunicorn", "room.wsgi:application", "--bind", "0.0.0.0:8888", "--workers", "2"]