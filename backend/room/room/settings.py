"""
Django settings for room project.
"""
# ====================== 1. 初始化 Nacos 客户端（最终修复版） ======================
from dotenv import load_dotenv
load_dotenv()

import os
import yaml
from pathlib import Path

# 全局配置对象，默认空
NACOS_CONFIG = {}

try:
    from nacos.client import NacosClient

    # 配置
    NACOS_SERVER_ADDR = os.environ.get("NACOS_SERVER_ADDR")
    NACOS_NAMESPACE = os.environ.get("NACOS_NAMESPACE", "public")
    NACOS_DATA_ID = "django-room-settings.yaml"
    NACOS_GROUP = os.environ.get("NACOS_GROUP", "DEFAULT_GROUP")    # 🔥 可动态切换的分组
    NACOS_USERNAME = os.environ.get("NACOS_USERNAME", "").strip()
    NACOS_PASSWORD = os.environ.get("NACOS_PASSWORD", "").strip()

    # 构建参数（无多余参数，彻底删除 timeout）
    client_kwargs = {
        "server_addresses": NACOS_SERVER_ADDR,
        "namespace": NACOS_NAMESPACE,
    }
    # 只有用户名密码都存在时才传递
    if NACOS_USERNAME and NACOS_PASSWORD:
        client_kwargs["username"] = NACOS_USERNAME
        client_kwargs["password"] = NACOS_PASSWORD

    # 初始化客户端
    client = NacosClient(**client_kwargs)

    # 拉取配置（核心：捕获get_config的异常）
    try:
        nacos_config_str = client.get_config(NACOS_DATA_ID,
                                             NACOS_GROUP,
                                             no_snapshot=True  # 这才是2.0.9版本的正确写法！
                                             )
    except Exception as e:
        # 拉取配置失败（连不上、端口错、Nacos没启动）
        print(f"⚠️ Nacos 拉取配置失败：{str(e)}，使用本地默认配置")
        nacos_config_str = None

    # 只有真的获取到配置内容，才赋值
    if nacos_config_str and nacos_config_str.strip():
        NACOS_CONFIG = yaml.safe_load(nacos_config_str) or {}
        print(f"✅ 成功拉取 Nacos 动态配置 | 分组：{NACOS_GROUP}")
    else:
        print("⚠️ Nacos 未获取到有效配置，使用本地默认配置")

# 全局兜底：任何Nacos错误都不影响启动
except Exception as e:
    print(f"⚠️ Nacos 初始化失败：{str(e)}，使用本地默认配置")
    NACOS_CONFIG = {}

# ====================== 2. 配置读取函数（无BUG版） ======================
def get_conf(key, default=None):
    if key in NACOS_CONFIG:
        val = NACOS_CONFIG[key]
    elif key in os.environ:
        val = os.environ[key]
    else:
        return default

    # 自动转换字符串布尔/数字
    if isinstance(val, str):
        lower_val = val.strip().lower()
        if lower_val in ["true", "1"]:
            return True
        elif lower_val in ["false", "0"]:
            return False
    if isinstance(val, str) and val.isdigit():
        return int(val)
    return val

# ====================== 2. 基础路径 ======================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# ====================== 3. 核心配置（从 Nacos 读取） ======================
SECRET_KEY = get_conf("SECRET_KEY", 'django-insecure-z!-t31+1i1mv+19i@tnkgi&#hd3f7=^6&7lepc%-6dbe@iz26d')
DEBUG = get_conf("DEBUG", "true")
MAIN_HOST = get_conf("MAIN_HOST", "http://localhost")
HOSTS = get_conf("HOSTS", "http://localhost,http://127.0.0.1").split(",")
TIME_ZONE = get_conf("TIME_ZONE", "Asia/Shanghai")

print(f'Debug modus is turned {"on" if DEBUG else "off"}')

# ====================== 4. 跨域/域名配置 ======================
CSRF_TRUSTED_ORIGINS = HOSTS
ALLOWED_HOSTS = get_conf("ALLOWED_HOSTS", ["*"])
CORS_ALLOWED_ORIGINS = HOSTS
CORS_ALLOW_ALL_ORIGINS = get_conf("CORS_ALLOW_ALL_ORIGINS", True)
CORS_ALLOW_CREDENTIALS = get_conf("CORS_ALLOW_CREDENTIALS", True)

# ====================== 5. 应用/中间件 ======================
INSTALLED_APPS = [
    'import_export',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'login',
    'roomInfo',
    'smart_selects',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'room.urls'

MIGRATION_MODULES = {
    "login": "data.db_migrations.login",
    "roomInfo": "data.db_migrations.roomInfo"
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'room.wsgi.application'

# ====================== 6. 数据库（Nacos 动态切换） ======================
POSTGRES_HOST = get_conf("POSTGRES_HOST")
if POSTGRES_HOST:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": get_conf("POSTGRES_DB", "postgres"),
            "USER": get_conf("POSTGRES_USER", "postgres"),
            "PASSWORD": get_conf("POSTGRES_PASSWORD", ""),
            "HOST": POSTGRES_HOST,
            "PORT": "",
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            "NAME": DATA_DIR / 'db.sqlite3',
            "OPTIONS": {"timeout": 20},
        }
    }

# ====================== 7. 密码验证 ======================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ====================== 8. 国际化 ======================
LANGUAGE_CODE = 'zh-hans'
USE_I18N = True
USE_TZ = False

# ====================== 9. 媒体文件 ======================
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR,'media')

# ====================== 10. 缓存（Redis/本地缓存 动态切换） ======================
REDIS_ENABLE = get_conf("REDIS_ENABLE", False)
if REDIS_ENABLE and not DEBUG:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": get_conf("REDIS_LOCATION", "redis://0.0.0.0:6379/1"),
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {"max_connections": 100,"retry_on_timeout": True},
                "SOCKET_CONNECT_TIMEOUT": 5,
                "SOCKET_TIMEOUT": 5,
            }
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    }

# ====================== 11. 静态文件 ======================
STATIC_URL = '/static/'
STATIC_ROOT = '/app/static_collect'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ====================== 12. SimpleUI（Nacos 配置） ======================
SIMPLEUI_LOGIN_PC = get_conf("SIMPLEUI_LOGIN_PC", False)
SIMPLEUI_HOME_INFO = get_conf("SIMPLEUI_HOME_INFO", False)
SIMPLEUI_HOME_ANALYSIS = get_conf("SIMPLEUI_HOME_ANALYSIS", False)
SIMPLEUI_DEFAULT_TITLE = get_conf("SIMPLEUI_DEFAULT_TITLE", "动环安全评估管理系统")
SIMPLEUI_DEFAULT_HEADER = get_conf("SIMPLEUI_DEFAULT_HEADER", "动环安全评估管理系统")
SIMPLEUI_THEME = get_conf("SIMPLEUI_THEME", 'blue')

# ====================== 13. 文件上传大小 ======================
DATA_UPLOAD_MAX_MEMORY_SIZE = get_conf("DATA_UPLOAD_MAX_MEMORY_SIZE", 52428800)
FILE_UPLOAD_MAX_MEMORY_SIZE = get_conf("FILE_UPLOAD_MAX_MEMORY_SIZE", 52428800)