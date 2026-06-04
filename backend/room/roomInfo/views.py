from rest_framework.permissions import AllowAny
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import DictType, DictItem
from .serializers import DictTypeSerializer, DictItemSerializer, DictItemTreeSerializer
from room.cacheUtils import get_dict_data, refresh_dict_cache, refresh_all_dict_cache

from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser


import os
from django.conf import settings
from .models import RoomInfo
from .serializers import RoomInfoSerializer


# ====================== 字典分类接口 ======================
class DictTypeViewSet(ModelViewSet):
    queryset = DictType.objects.all()
    serializer_class = DictTypeSerializer

# ====================== 字典项接口 ======================
class DictItemViewSet(ModelViewSet):
    permission_classes = [AllowAny]

    queryset = DictItem.objects.filter(status=True).order_by("sort")
    serializer_class = DictItemSerializer

    # 根据分类编码 + 父级ID 获取字典（带缓存）
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        # ====================== 新增：获取 parent_id ======================
        type_code = request.query_params.get("code")
        parent_id = request.query_params.get("parent_id")  # 接收父级ID

        # 传入工具类
        data = get_dict_data(type_code, parent_id)
        return Response(data)

    # 获取级联树形数据
    @action(detail=False, methods=['get'])
    def tree(self, request):
        type_code = request.query_params.get("code")
        dict_type = DictType.objects.get(code=type_code)
        items = DictItem.objects.filter(type=dict_type, parent=None, status=True)
        return Response(DictItemTreeSerializer(items, many=True).data)

# ====================== 缓存刷新接口（前端专用） ======================
class DictCacheViewSet(ViewSet):
    permission_classes = [AllowAny]

    # 一键刷新所有字典缓存
    @action(detail=False, methods=['post'])
    def refresh_all(self, request):
        refresh_all_dict_cache()
        return Response({"msg": "缓存刷新成功！"})

    # 刷新单个字典缓存
    @action(detail=False, methods=['post'])
    def refresh_one(self, request):
        type_code = request.data.get("code")
        refresh_dict_cache(type_code)
        return Response({"msg": f"{type_code} 缓存刷新成功！"})



# 机房信息查询接口（根据局站ID查询）
class RoomInfoView(APIView):
    # 开放权限，无需登录
    permission_classes = [AllowAny]

    def get(self, request):
        # 获取前端传递的 局站ID
        station_id = request.query_params.get('station_id')

        if not station_id:
            return Response({})

        # 查询该局站对应的机房信息（一个局站对应一个机房）
        try:
            room = RoomInfo.objects.get(station_id=station_id)
            serializer = RoomInfoSerializer(room, context={'request': request})
            return Response(serializer.data)
        except RoomInfo.DoesNotExist:
            # 无数据返回空对象，前端显示「暂无数据」
            return Response({})



class RoomImageUploadView(APIView):
    permission_classes = [AllowAny]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        # 1. 获取前端传参（必传）
        file = request.FILES.get('file')
        img_field = request.data.get('img_field')    # 如 odf_count_img
        old_url = request.data.get('old_url', '').strip() # 旧图片路径
        final_name = request.data.get('final_name')  # 前端生成的完整文件名
        admin_account = request.data.get('admin_account')  # 管理员账号 18710629721

        if not file or not img_field or not admin_account or not final_name:
            return Response({"code": 400, "msg": "参数缺失"}, status=400)

        # ==============================================
        # 🔥 规则1：自动生成子目录（odf_count_img → odf → room/odf/）
        # ==============================================
        if "_count_img" in img_field:
            # 格式：xxx_count_img → 取 xxx
            sub_dir = img_field.replace("_count_img", "")
        elif img_field.endswith("_img"):
            # 兼容其他：xxx_img → 取 xxx
            sub_dir = img_field.replace("_img", "")
        else:
            sub_dir = "other"

        # 最终目录：media/room/odf/
        base_dir = "room"
        save_dir = os.path.join(settings.MEDIA_ROOT, base_dir, sub_dir)
        os.makedirs(save_dir, exist_ok=True)

        # ==============================================
        # 🔥 最新规则：删除当前目录下 所有以 管理员账号_ 开头的图片
        # ==============================================
        prefix = f"{admin_account}_"  # 匹配前缀：18710629721_
        if os.path.exists(save_dir):
            for filename in os.listdir(save_dir):
                # 判断文件是否以管理员账号开头
                if filename.startswith(prefix):
                    file_path = os.path.join(save_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                    except Exception:
                        pass

        # 完整保存路径
        save_path = os.path.join(save_dir, final_name)

        # 保存文件
        with open(save_path, 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)

        # ==============================================
        # 🔥 返回标准路径：/media/room/odf/18710629721_xxx.jpg
        # ==============================================
        # file_url = f"{settings.MEDIA_URL}{base_dir}/{sub_dir}/{final_name}"
        #20260522 1615 只返回这种格式：/room/odf/18710629721_xxx.jpg，这样前端不用再格式化了
        file_url = f"{base_dir}/{sub_dir}/{final_name}"

        return Response({
            "code": 200,
            "msg": "上传成功",
            "url": file_url
        })


# ========================
# 2. 机房信息 保存/更新 接口（支持重复提交）
# ========================
class RoomInfoSaveView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        # 1. 获取局站ID（核心关联字段）
        station_id = request.data.get('station')
        if not station_id:
            return Response({"code": 400, "msg": "未选择局站"}, status=400)

        # 2. 修复核心：处理外键字段 → 自动转为 xxx_id 格式（解决报错！）
        data = request.data.copy()

        print("data:", data)
        # 所有外键字段，统一加 _id 后缀
        foreign_keys = ['province', 'city', 'area', 'station_level', 'station']
        for key in foreign_keys:
            if key in data and data[key]:
                data[f'{key}_id'] = data[key]
                del data[key]

        # 3. 更新或创建（自动处理外键ID）
        instance, created = RoomInfo.objects.update_or_create(
            station_id=station_id,
            defaults=data
        )

        # 4. 返回数据
        serializer = RoomInfoSerializer(instance)
        return Response({
            "code": 200,
            "msg": "保存成功",
            "data": serializer.data
        })