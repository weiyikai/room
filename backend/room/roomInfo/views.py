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
from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from io import BytesIO
from datetime import datetime
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


# ====================== 机房巡检轨迹管理接口 ======================
from datetime import datetime
from .models import InspectionSession, InspectionTrackPoint
from .serializers import (
    InspectionSessionListSerializer,
    InspectionSessionDetailSerializer,
    InspectionLocationUploadSerializer,
    InspectionBatchLocationUploadSerializer,
    InspectionSessionStartSerializer,
    InspectionSessionEndSerializer,
)
from login.models import RoomAdminUser


class InspectionSessionStartView(APIView):
    """开始巡检：创建巡检会话"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InspectionSessionStartSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": 400, "msg": "参数错误", "errors": serializer.errors})

        station_id = serializer.validated_data['station_id']
        admin_id = serializer.validated_data['admin_id']

        # 校验管理员是否存在
        try:
            admin_user = RoomAdminUser.objects.get(id=admin_id)
        except RoomAdminUser.DoesNotExist:
            return Response({"code": 400, "msg": "管理员不存在"})

        # 校验局站是否存在
        try:
            station = DictItem.objects.get(id=station_id, type__code="STATION")
        except DictItem.DoesNotExist:
            return Response({"code": 400, "msg": "局站不存在"})

        # 检查是否有未结束的巡检会话
        active_session = InspectionSession.objects.filter(
            admin_user=admin_user, status='active'
        ).first()
        if active_session:
            return Response({
                "code": 400,
                "msg": "当前已有进行中的巡检会话，请先结束再开始新巡检",
                "data": {"session_id": active_session.id}
            })

        # 创建巡检会话
        session = InspectionSession.objects.create(
            admin_user=admin_user,
            station=station,
            start_time=datetime.now(),
            status='active'
        )

        return Response({
            "code": 200,
            "msg": "巡检开始",
            "data": {
                "session_id": session.id,
                "start_time": session.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        })


class InspectionSessionEndView(APIView):
    """结束巡检"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InspectionSessionEndSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": 400, "msg": "参数错误"})

        session_id = serializer.validated_data['session_id']

        try:
            session = InspectionSession.objects.get(id=session_id)
        except InspectionSession.DoesNotExist:
            return Response({"code": 400, "msg": "巡检会话不存在"})

        if session.status == 'completed':
            return Response({"code": 400, "msg": "该巡检已结束"})

        session.status = 'completed'
        session.end_time = datetime.now()
        session.save()

        return Response({
            "code": 200,
            "msg": "巡检结束",
            "data": {
                "session_id": session.id,
                "point_count": session.track_points.count(),
                "start_time": session.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": session.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        })


class InspectionLocationUploadView(APIView):
    """上报单个定位点"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InspectionLocationUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": 400, "msg": "参数错误", "errors": serializer.errors})

        data = serializer.validated_data

        try:
            session = InspectionSession.objects.get(id=data['session_id'])
        except InspectionSession.DoesNotExist:
            return Response({"code": 400, "msg": "巡检会话不存在"})

        if session.status != 'active':
            return Response({"code": 400, "msg": "巡检会话已结束，无法上报位置"})

        point = InspectionTrackPoint.objects.create(
            session=session,
            latitude=data['latitude'],
            longitude=data['longitude'],
            accuracy=data.get('accuracy'),
            altitude=data.get('altitude'),
            timestamp=data['timestamp']
        )

        return Response({
            "code": 200,
            "msg": "位置已上报",
            "data": {"point_id": point.id}
        })


class InspectionBatchLocationUploadView(APIView):
    """批量上报定位点（小程序端积累一批后一次性提交）"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = InspectionBatchLocationUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": 400, "msg": "参数错误", "errors": serializer.errors})

        data = serializer.validated_data

        try:
            session = InspectionSession.objects.get(id=data['session_id'])
        except InspectionSession.DoesNotExist:
            return Response({"code": 400, "msg": "巡检会话不存在"})

        if session.status != 'active':
            return Response({"code": 400, "msg": "巡检会话已结束，无法上报位置"})

        created_count = 0
        for pt in data['points']:
            try:
                InspectionTrackPoint.objects.create(
                    session=session,
                    latitude=pt['latitude'],
                    longitude=pt['longitude'],
                    accuracy=pt.get('accuracy'),
                    altitude=pt.get('altitude'),
                    timestamp=pt.get('timestamp', datetime.now())
                )
                created_count += 1
            except Exception:
                continue

        return Response({
            "code": 200,
            "msg": f"已上报 {created_count} 个定位点",
            "data": {"count": created_count}
        })


class InspectionSessionListView(APIView):
    """查询巡检会话列表"""
    permission_classes = [AllowAny]

    def get(self, request):
        admin_id = request.query_params.get('admin_id')
        station_id = request.query_params.get('station_id')
        status = request.query_params.get('status', '')

        queryset = InspectionSession.objects.all()

        if admin_id:
            queryset = queryset.filter(admin_user_id=admin_id)
        if station_id:
            queryset = queryset.filter(station_id=station_id)
        if status:
            queryset = queryset.filter(status=status)

        queryset = queryset.order_by('-start_time')
        serializer = InspectionSessionListSerializer(queryset, many=True)
        return Response({"code": 200, "data": serializer.data})


class InspectionSessionDetailView(APIView):
    """查询巡检会话详情（含完整轨迹点）"""
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            session = InspectionSession.objects.get(id=session_id)
        except InspectionSession.DoesNotExist:
            return Response({"code": 400, "msg": "巡检会话不存在"})

        serializer = InspectionSessionDetailSerializer(session)
        return Response({"code": 200, "data": serializer.data})


class InspectionSessionExportView(APIView):
    """导出巡检轨迹为 Excel"""
    permission_classes = [AllowAny]

    def get(self, request, session_id):
        try:
            session = InspectionSession.objects.get(id=session_id)
        except InspectionSession.DoesNotExist:
            return Response({"code": 400, "msg": "巡检会话不存在"})

        track_points = session.track_points.all()

        # 创建工作簿
        wb = Workbook()
        ws = wb.active
        ws.title = "巡检轨迹"

        # 表头信息
        ws.append(["巡检轨迹报表"])
        ws.append(["管理员", f"{session.admin_user.name or ''} ({session.admin_user.phone})"])
        ws.append(["巡检局站", session.station.label if session.station else ""])
        ws.append(["开始时间", session.start_time.strftime("%Y-%m-%d %H:%M:%S") if session.start_time else ""])
        ws.append(["结束时间", session.end_time.strftime("%Y-%m-%d %H:%M:%S") if session.end_time else "进行中"])
        ws.append(["轨迹点数", len(track_points)])
        ws.append([])  # 空行

        # 轨迹点表头
        headers = ["序号", "纬度", "经度", "定位精度(m)", "海拔(m)", "定位时间"]
        ws.append(headers)

        # 写入轨迹点
        for idx, pt in enumerate(track_points, 1):
            ws.append([
                idx,
                pt.latitude,
                pt.longitude,
                pt.accuracy or "",
                pt.altitude or "",
                pt.timestamp.strftime("%Y-%m-%d %H:%M:%S") if pt.timestamp else "",
            ])

        # 列宽
        col_widths = [8, 18, 18, 16, 14, 24]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        # 输出
        output = BytesIO()
        wb.save(output)
        output.seek(0)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        station_name = session.station.label if session.station else "unknown"
        filename = f"巡检轨迹_{station_name}_{timestamp}.xlsx"

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response