from rest_framework import serializers
from .models import DictType, DictItem, RoomInfo

class DictTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DictType
        fields = "__all__"

class DictItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = DictItem
        fields = "__all__"

# 前端级联选择专用序列化器
class DictItemTreeSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source="label")
    id = serializers.IntegerField(source="id")
    children = serializers.SerializerMethodField()

    class Meta:
        model = DictItem
        fields = ["id", "text", "value", "extend", "children"]

    def get_children(self, obj):
        children = obj.items.filter(status=True).order_by("sort")
        return DictItemTreeSerializer(children, many=True).data

class RoomInfoSerializer(serializers.ModelSerializer):
    # 格式化字典数据，返回名称给前端
    province_name = serializers.CharField(source='province.label', read_only=True)
    city_name = serializers.CharField(source='city.label', read_only=True)
    area_name = serializers.CharField(source='area.label', read_only=True)
    station_name = serializers.CharField(source='station.label', read_only=True)
    station_level_name = serializers.CharField(source='station_level.label', read_only=True)

    class Meta:
        model = RoomInfo
        fields = '__all__'
#20260421 2122 新增图片上传
# 图片上传专用序列化器
class ImageUploadSerializer(serializers.Serializer):
    file = serializers.ImageField(required=True)


# ====================== 巡检轨迹序列化器 ======================
from .models import InspectionSession, InspectionTrackPoint


class InspectionTrackPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = InspectionTrackPoint
        fields = ['id', 'latitude', 'longitude', 'accuracy', 'altitude', 'timestamp']


class InspectionSessionListSerializer(serializers.ModelSerializer):
    """巡检会话列表（不含轨迹点详情）"""
    admin_name = serializers.CharField(source='admin_user.name', read_only=True)
    admin_phone = serializers.CharField(source='admin_user.phone', read_only=True)
    station_name = serializers.CharField(source='station.label', read_only=True)
    point_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = InspectionSession
        fields = [
            'id', 'admin_name', 'admin_phone', 'station_name',
            'station', 'start_time', 'end_time', 'status',
            'point_count', 'notes', 'created_at'
        ]


class InspectionSessionDetailSerializer(serializers.ModelSerializer):
    """巡检会话详情（含完整轨迹点）"""
    admin_name = serializers.CharField(source='admin_user.name', read_only=True)
    admin_phone = serializers.CharField(source='admin_user.phone', read_only=True)
    station_name = serializers.CharField(source='station.label', read_only=True)
    track_points = InspectionTrackPointSerializer(many=True, read_only=True)
    point_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = InspectionSession
        fields = [
            'id', 'admin_name', 'admin_phone', 'station_name',
            'station', 'start_time', 'end_time', 'status',
            'point_count', 'notes', 'track_points', 'created_at'
        ]


class InspectionLocationUploadSerializer(serializers.Serializer):
    """位置上报参数校验"""
    session_id = serializers.IntegerField(required=True, help_text="巡检会话ID")
    latitude = serializers.FloatField(required=True, help_text="纬度")
    longitude = serializers.FloatField(required=True, help_text="经度")
    accuracy = serializers.FloatField(required=False, allow_null=True, help_text="精度(m)")
    altitude = serializers.FloatField(required=False, allow_null=True, help_text="海拔(m)")
    timestamp = serializers.DateTimeField(required=True, help_text="定位时间(ISO格式)")


class InspectionBatchLocationUploadSerializer(serializers.Serializer):
    """批量位置上报"""
    session_id = serializers.IntegerField(required=True)
    points = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        help_text="点位列表 [{\"latitude\": xx, \"longitude\": xx, \"timestamp\": \"...\", ...}]"
    )


class InspectionSessionStartSerializer(serializers.Serializer):
    """开始巡检参数"""
    station_id = serializers.IntegerField(required=True, help_text="局站ID")
    admin_id = serializers.IntegerField(required=True, help_text="管理员ID")


class InspectionSessionEndSerializer(serializers.Serializer):
    """结束巡检参数"""
    session_id = serializers.IntegerField(required=True, help_text="巡检会话ID")