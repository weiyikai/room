from login.models import RoomAdminUser
from django.contrib import admin

#202604421 1004新增机房管理员账户信息表
@admin.register(RoomAdminUser)
class RoomAdminUserAdmin(admin.ModelAdmin):
    list_display = ("phone", "name", "get_login_status",
                    "get_province", "get_city", "get_area", "get_station_level","get_station","created_at")
    search_fields = ("phone", "name", "station__label")
    list_filter = ("province", "city", "area", "station_level")

    # 只读字段：密码自动生成，禁止手动修改
    readonly_fields = ("password", "created_at", "updated_at")

    # 后台显示关联的字典名称（自动同步最新值）
    def get_province(self, obj):
        return obj.province.label

    def get_city(self, obj):
        return obj.city.label

    def get_area(self, obj):
        return obj.area.label

    def get_station(self, obj):
        return obj.station.label

    def get_station_level(self, obj):
        return obj.station_level.label

    get_province.short_description = "省份"
    get_city.short_description = "地市"
    get_area.short_description = "区县"
    get_station_level.short_description = "负责局站等级"
    get_station.short_description = "负责局站"

    # 编辑页面字段布局
    fieldsets = (
        ("账户信息", {"fields": ("phone", "name", "password","login_status")}),
        ("负责区域（关联字典表）", {"fields": ("province", "city", "area", "station_level", "station")}),
        ("系统信息", {"fields": ("created_at", "updated_at")}),
    )

    # 🔥 显示【登录状态】中文（未登录/已登录）
    def get_login_status(self, obj):
        if obj.login_status == 1:
            return '已登录'
        return '未登录'

    get_login_status.short_description = '登录状态'
    get_login_status.allow_tags = True  # 允许HTML样式