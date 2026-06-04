# models.py
from django.contrib.auth.hashers import make_password
# 导入级联外键（已安装过插件，直接用）
from smart_selects.db_fields import ChainedForeignKey
# 顶部导入这个包（已导入就不用加）
from django.contrib.auth.hashers import check_password
#20260413 1343 动环评估小程序-数据字典
from django.db import models
from roomInfo.models import DictItem


class RoomAdminUser(models.Model):
    """机房管理员账户（级联选择版）"""
    phone = models.CharField(max_length=11, unique=True, verbose_name="手机号(账号)")
    name = models.CharField(max_length=20, blank=True, null=True, verbose_name="姓名")
    password = models.CharField(max_length=128, verbose_name="密码", blank=True)

    # ====================== 核心新增：登录状态 ======================
    login_status = models.SmallIntegerField(
        verbose_name="登录状态",
        choices=((0, "未登录"), (1, "已登录")),
        default=0,  # 新增账户默认：未登录
        help_text="0-未登录 1-已登录"
    )

    # ====================== 级联选择配置 ======================
    # 1. 省份（基础）
    province = models.ForeignKey(
        DictItem, on_delete=models.PROTECT,
        limit_choices_to={"type__code": "PROVINCE"},
        related_name="admin_province",
        verbose_name="省份"
    )

    # 2. 地市 → 级联省份（根据省份筛选）
    city = ChainedForeignKey(
        DictItem, on_delete=models.PROTECT,
        chained_field="province",  # 关联上级字段
        chained_model_field="parent",  # 字典表的父级字段
        limit_choices_to={"type__code": "CITY"},
        related_name="admin_city",
        verbose_name="地市",
        auto_choose=True,  # 自动匹配
        show_all=False
    )

    # 3. 区县 → 级联地市
    area = ChainedForeignKey(
        DictItem, on_delete=models.PROTECT,
        chained_field="city",
        chained_model_field="parent",
        limit_choices_to={"type__code": "AREA"},
        related_name="admin_area",
        verbose_name="区县",
        auto_choose=True,
        show_all=False
    )

    # 4. 局站等级（基础）
    station_level = models.ForeignKey(
        DictItem, on_delete=models.PROTECT,
        limit_choices_to={"type__code": "STATION_LEVEL"},
        related_name="admin_level",
        verbose_name="局站等级"
    )

    # 5. 局站 → 级联区县 + 局站等级（核心双级联）
    station = ChainedForeignKey(
        DictItem, on_delete=models.PROTECT,
        chained_field="area",        # 第一关联：区县
        chained_model_field="parent",
        limit_choices_to={"type__code": "STATION"},
        related_name="admin_station",
        verbose_name="负责局站",
        unique=True,  # 一个局站只配一个管理员
        auto_choose=True,
        show_all=False
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "机房管理员"
        verbose_name_plural = "机房管理员列表"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name}({self.phone})"

    # ===================== 🔥 修复：手动添加密码校验方法 =====================
    def check_password(self, raw_password):
        """验证密码（解决无check_password错误）"""
        return check_password(raw_password, self.password)

    # 自动生成默认密码 123456
    def save(self, *args, **kwargs):
        if not self.pk:
            self.password = make_password("123456")
        super().save(*args, **kwargs)