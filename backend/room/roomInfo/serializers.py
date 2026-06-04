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