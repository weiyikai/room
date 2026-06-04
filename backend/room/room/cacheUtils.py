from django.core.cache import cache
from django.conf import settings  # 导入配置
from roomInfo.models import DictType, DictItem
from roomInfo.serializers import DictItemSerializer

# Redis Key 前缀
DICT_CACHE_KEY = "dict:{}:{}"


# 1. 获取字典数据（支持 类型编码 + 父级ID 筛选 + 自动缓存）
def get_dict_data(type_code, parent_id=None):
    cache_key = DICT_CACHE_KEY.format(type_code, parent_id or 0)
    data = cache.get(cache_key)
    if data is not None:
        return data

    try:
        dict_type = DictType.objects.get(code=type_code)
        items = DictItem.objects.filter(type=dict_type, status=True).order_by("sort")

        if parent_id:
            items = items.filter(parent_id=parent_id)


        data = DictItemSerializer(items, many=True).data
        cache.set(cache_key, data, timeout=None)
        return data
    except Exception as e:
        return []


# 2. 刷新单个字典缓存（根据 DEBUG 自动切换方式）
def refresh_dict_cache(type_code):
    pattern = f"dict:{type_code}:*"

    # ====================== 核心：根据 DEBUG 区分 ======================
    if settings.DEBUG:
        # 开发环境 - 本地内存缓存：直接清空（安全无报错）
        cache.clear()
    else:
        # 生产环境 - Redis：通配符精准删除（不影响其他缓存）
        try:
            keys = cache.keys(pattern)
            if keys:
                cache.delete_many(keys)
        except Exception:
            pass


# 3. 刷新所有字典缓存
def refresh_all_dict_cache():
    types = DictType.objects.values_list("code", flat=True)
    for code in types:
        refresh_dict_cache(code)
    return True