import os
from io import StringIO
from django.core.wsgi import get_wsgi_application

# 固定写法：启动Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room.settings')
application = get_wsgi_application()

# ==============================================
# Nacos 配置加载：拉不到也不报错，项目正常运行
# ==============================================
try:
    # 延迟导入：防止Django未启动完成报错
    from nacos import NacosClient
    from django.conf import settings

    # 连接Nacos
    client = NacosClient(
        server_addresses="nacos:8848",
        namespace="public",
        username="nacos",
        password="nacos",
        # 关键：超时时间，防止卡住
        timeout=3
    )

    # 尝试拉取配置（没有也不会崩溃！）
    try:
        content = client.get_config("drf-room-config", "DEFAULT_GROUP")
        # 解析配置
        for line in StringIO(content):
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # 动态覆盖配置
                if hasattr(settings, key):
                    setattr(settings, key, value)
        print("✅ Nacos 配置加载成功")
    except Exception:
        # 没有配置 → 用本地默认配置，不报错！
        print("ℹ Nacos 未找到配置，使用本地默认配置")

except Exception as e:
    # Nacos 未启动/连接失败 → 正常运行
    print(f"ℹ Nacos 未连接：{str(e)}，使用本地配置")