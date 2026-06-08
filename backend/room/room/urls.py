"""
URL configuration for room project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter


from django.views.static import serve
from django.conf import settings
from roomInfo.views import (
    RoomInfoView, RoomImageUploadView, RoomInfoSaveView,
    InspectionSessionStartView, InspectionSessionEndView,
    InspectionLocationUploadView, InspectionBatchLocationUploadView,
    InspectionSessionListView, InspectionSessionDetailView,
    InspectionSessionExportView,
)
from login.views import RoomAdminLoginView,RoomAdminLogoutView,LogoutStatusView

router = DefaultRouter()

#20260413 1405 动环小程序数据字典
from roomInfo.views import DictTypeViewSet, DictItemViewSet, DictCacheViewSet
router.register(r'dict/type', DictTypeViewSet, basename='dict-type')
router.register(r'dict/item', DictItemViewSet, basename='dict-item')
router.register(r'dict/cache', DictCacheViewSet,basename='dict-cache')

urlpatterns = [
    path('api/', include([
        path('', include(router.urls)),
        #机房信息查询接口
        path('room/info/', RoomInfoView.as_view(), name='room-info'),
        # 机房管理员登录
        path("room/admin/login/", RoomAdminLoginView.as_view(), name="admin-login"),
        #登出
        path("room/admin/logout/", RoomAdminLogoutView.as_view(), name="admin-logout"),
        #图片上传
        path('room/upload/image/', RoomImageUploadView.as_view(), name='room-upload'),
        #机房信息保存
        path('room/info/save/', RoomInfoSaveView.as_view(), name='room-save'),
        # 新增：退出重置状态接口
        path("room/admin/logout/status/", LogoutStatusView.as_view(), name="logout-status"),
        # ====================== 巡检轨迹管理接口 ======================
        path("track/session/start/", InspectionSessionStartView.as_view(), name="track-session-start"),
        path("track/session/end/", InspectionSessionEndView.as_view(), name="track-session-end"),
        path("track/location/upload/", InspectionLocationUploadView.as_view(), name="track-location-upload"),
        path("track/location/batch/", InspectionBatchLocationUploadView.as_view(), name="track-location-batch"),
        path("track/sessions/", InspectionSessionListView.as_view(), name="track-session-list"),
        path("track/session/<int:session_id>/", InspectionSessionDetailView.as_view(), name="track-session-detail"),
        path("track/session/<int:session_id>/export/", InspectionSessionExportView.as_view(), name="track-session-export"),
    ])),
    #20260421 1403 新增：级联插件路由
    path('chaining/', include('smart_selects.urls')),
    path('admin/', admin.site.urls),
    # 以后访问 http://127.0.0.1:5000/static/imgs/mini_dashboard_qrcode.png
    # 就会去 media 文件夹下的 imgs 下去找 mini_dashboard_qrcode.png --》找到就前端显示
    path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
]


admin.site.site_header = '局站动环安全后台管理端'
admin.site.site_title = '局站动环安全后台管理端'
admin.site.index_title = '欢迎来到局站动环安全后台管理端'
