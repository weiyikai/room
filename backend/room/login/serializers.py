from rest_framework import serializers
from .models import RoomAdminUser

class RoomAdminLoginSerializer(serializers.Serializer):
    """登录参数校验"""
    phone = serializers.CharField(max_length=11, required=True, help_text="手机号/账号")
    password = serializers.CharField(max_length=20, required=True, help_text="密码，默认123456")

class RoomAdminUserSerializer(serializers.ModelSerializer):
    """返回用户信息（含登录状态）"""
    province_name = serializers.CharField(source="province.label", read_only=True)
    city_name = serializers.CharField(source="city.label", read_only=True)
    area_name = serializers.CharField(source="area.label", read_only=True)
    station_name = serializers.CharField(source="station.label", read_only=True)
    station_level_name = serializers.CharField(source="station_level.label", read_only=True)

    class Meta:
        model = RoomAdminUser
        fields = [
            "id", "phone", "name", "login_status",
            # 🔥 必须加这5个ID！自动填充全靠它
            "province", "city", "area", "station_level", "station",
            "province_name", "city_name", "area_name",
            "station_level_name", "station_name"
        ]