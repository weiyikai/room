from rest_framework.permissions import AllowAny
from rest_framework.response import Response

#20260421 1605 登录
from rest_framework.views import APIView
from .models import RoomAdminUser
from .serializers import RoomAdminLoginSerializer, RoomAdminUserSerializer


class LogoutStatusView(APIView):
    """
    退出登录：将login_status置为0
    """

    def post(self, request):
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"code": 400, "msg": "用户ID不能为空"})

        try:
            user = RoomAdminUser.objects.get(id=user_id)
            user.login_status = 0  # 置为未登录
            user.save()
            return Response({"code": 200, "msg": "状态已重置为未登录"})
        except RoomAdminUser.DoesNotExist:
            return Response({"code": 404, "msg": "用户不存在"})

class RoomAdminLoginView(APIView):
    """
    机房管理员登录接口
    uni-app 调用：POST /api/room/admin/login/
    参数：{"phone":"13800138000", "password":"123456"}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        # 1. 校验参数
        serializer = RoomAdminLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"code": 400, "msg": "参数错误", "errors": serializer.errors})

        phone = serializer.validated_data["phone"]
        password = serializer.validated_data["password"]

        # 2. 查询用户
        try:
            user = RoomAdminUser.objects.get(phone=phone)
        except RoomAdminUser.DoesNotExist:
            return Response({"code": 400, "msg": "账号不存在"})

        # 3. 验证密码
        if not user.check_password(password):
            return Response({"code": 400, "msg": "密码错误"})

        # ====================
        # 🔥 核心：登录前校验状态（原子操作，绝对安全）
        # ====================
        if user.login_status == 1:
            return Response({
                "code": 400,
                "msg": "该账号已在其他设备登录，请先登出！"
            })

        # 3. 校验通过 → 更新为已登录状态
        user.login_status = 1
        user.save()

        # 5. 返回用户信息
        return Response({
            "code": 200,
            "msg": "登录成功",
            "data": RoomAdminUserSerializer(user).data
        })

#20260421 1606 退出登录
# views.py 新增
class RoomAdminLogoutView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        phone = request.data.get("phone")
        if not phone:
            return Response({"code":400,"msg":"请传入手机号"})
        try:
            user = RoomAdminUser.objects.get(phone=phone)
            user.login_status = 0
            user.save()
            return Response({"code":200,"msg":"退出成功"})
        except RoomAdminUser.DoesNotExist:
            return Response({"code":400,"msg":"账号不存在"})