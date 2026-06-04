# models.py
# 导入级联外键（已安装过插件，直接用）
from smart_selects.db_fields import ChainedForeignKey
# 顶部导入这个包（已导入就不用加）
#20260413 1343 动环评估小程序-数据字典
from django.db import models
# ====================== 通用数据字典 - 分类 ======================
class DictType(models.Model):
    """
    字典类别：如 city(地市), area(区县), station_level(局站等级), station(局站名称)
    """
    name = models.CharField(max_length=50, verbose_name="分类名称")
    code = models.CharField(max_length=50, unique=True, verbose_name="分类编码(英文)")
    remark = models.CharField(max_length=200, blank=True, null=True, verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "字典分类"
        verbose_name_plural = "字典分类"

    def __str__(self):
        return self.name

# ====================== 通用数据字典 - 项 ======================
class DictItem(models.Model):
    """
    字典具体数据：支持自由配置 key/value/扩展字段
    """
    type = models.ForeignKey(DictType, on_delete=models.CASCADE, related_name="items", verbose_name="所属分类")
    label = models.CharField(max_length=100, verbose_name="显示名称")  # 石圪台交换点
    value = models.CharField(max_length=100, verbose_name="存储值")    # 01
    # 扩展字段1：父级（用于地市→区县→局站 级联）
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, verbose_name="父级项")
    # 扩展字段2：自由配置（存JSON，支持任意字段）
    extend = models.JSONField(default=dict, blank=True, null=True, verbose_name="扩展配置")
    sort = models.IntegerField(default=1, verbose_name="排序")
    status = models.BooleanField(default=True, verbose_name="启用")

    class Meta:
        verbose_name = "字典数据"
        verbose_name_plural = "字典数据"

    def __str__(self):
        return self.label


class RoomInfo(models.Model):
    # ====================== 【统一级联顺序：和管理员表完全一致】 ======================
    # 1. 省份
    province = models.ForeignKey(
        DictItem, on_delete=models.PROTECT,
        limit_choices_to={"type__code": "PROVINCE"},
        related_name="room_province",
        verbose_name="省份",
        null=True, blank=True
    )
    # 2. 地市（级联省份）
    city = ChainedForeignKey(
        DictItem, on_delete=models.PROTECT,
        chained_field="province",
        chained_model_field="parent",
        limit_choices_to={"type__code": "CITY"},
        related_name="room_city",
        verbose_name="地市",
        auto_choose=True, show_all=False,
        null=True, blank=True
    )
    # 3. 区县（级联地市）
    area = ChainedForeignKey(
        DictItem, on_delete=models.PROTECT,
        chained_field="city",
        chained_model_field="parent",
        limit_choices_to={"type__code": "AREA"},
        related_name="room_area",
        verbose_name="区县",
        auto_choose=True, show_all=False,
        null=True, blank=True
    )
    # 4. 局站等级（先选等级！和管理员表顺序一致）
    station_level = models.ForeignKey(
        DictItem, on_delete=models.PROTECT,
        limit_choices_to={"type__code": "STATION_LEVEL"},
        related_name="room_level",
        verbose_name="局站等级",
        null=True, blank=True
    )
    # 5. 局站名称（双级联：区县 + 局站等级 ✅ 核心修正）
    station = ChainedForeignKey(
        DictItem, on_delete=models.PROTECT,
        chained_field="area",
        chained_model_field="parent",
        limit_choices_to={"type__code": "STATION"},
        related_name="room_station",
        verbose_name="局站名称",
        auto_choose=True, show_all=False,
        null=True, blank=True
    )

    # ====================== 【你原有所有字段：完全保留，不动分毫】 ======================
    # 机房基础参数
    room_name = models.CharField(max_length=100, verbose_name="机房名称")
    room_name_img = models.ImageField(upload_to="room/name/", blank=True, null=True, verbose_name="机房全貌图片")
    room_length = models.FloatField(blank=True, null=True, verbose_name="机房长度(m)")
    room_length_img = models.ImageField(upload_to="room/length/", blank=True, null=True, verbose_name="机房长度图片")
    room_width = models.FloatField(blank=True, null=True, verbose_name="机房宽度(m)")
    room_width_img = models.ImageField(upload_to="room/width/", blank=True, null=True, verbose_name="机房宽度图片")
    room_height = models.FloatField(blank=True, null=True, verbose_name="机房高度(m)")
    room_height_img = models.ImageField(upload_to="room/height/", blank=True, null=True, verbose_name="机房高度图片")

    # 网络设备
    cabinet_count = models.IntegerField(blank=True, null=True, verbose_name="网络机柜数")
    cabinet_count_img = models.ImageField(upload_to="room/cabinet/", blank=True, null=True, verbose_name="网络机柜数量图片")
    odf_count = models.IntegerField(blank=True, null=True, verbose_name="ODF/MODF数量")
    odf_count_img = models.ImageField(upload_to="room/odf/", blank=True, null=True, verbose_name="ODF/MODF数量图片")

    # 开关电源（你原有所有字段...全部保留）
    power_cabinet_count = models.IntegerField(blank=True, null=True, verbose_name="电源列头柜数量")
    power_cabinet_count_img = models.ImageField(upload_to="room/power_cabinet/", blank=True, null=True, verbose_name="电源列头柜数量图片")
    switch_power_count = models.IntegerField(blank=True, null=True, verbose_name="开关电源数量")
    switch_power_count_img = models.ImageField(upload_to="room/switch_power/", blank=True, null=True, verbose_name="开关电源数量图片")
    switch_power_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="开关电源型号")
    switch_power_model_img = models.ImageField(upload_to="room/switch_power/", blank=True, null=True, verbose_name="开关电源型号图片")
    switch_power_capacity = models.CharField(max_length=100, blank=True, null=True, verbose_name="开关电源容量")
    switch_power_capacity_img = models.ImageField(upload_to="room/switch_power/", blank=True, null=True, verbose_name="开关电源容量图片")
    switch_power_factory = models.CharField(max_length=100, blank=True, null=True, verbose_name="开关电源厂家")
    switch_power_factory_img = models.ImageField(upload_to="room/switch_power/", blank=True, null=True, verbose_name="开关电源厂家图片")
    switch_power_date = models.DateField(blank=True, null=True, verbose_name="开关电源出厂日期")
    switch_power_date_img = models.ImageField(upload_to="room/switch_power/", blank=True, null=True, verbose_name="开关电源出厂日期图片")

    # 电池设备
    switch_module_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="开关电源模块型号")
    switch_module_model_img = models.ImageField(upload_to="room/module/", blank=True, null=True, verbose_name="开关电源模块型号图片")
    switch_module_capacity = models.CharField(max_length=100, blank=True, null=True, verbose_name="开关电源模块容量")
    switch_module_capacity_img = models.ImageField(upload_to="room/module/", blank=True, null=True, verbose_name="开关电源模块容量图片")
    switch_module_count = models.IntegerField(blank=True, null=True, verbose_name="开关电源模块数量")
    switch_module_count_img = models.ImageField(upload_to="room/module/", blank=True, null=True, verbose_name="开关电源模块数量图片")
    battery_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="电池型号")
    battery_model_img = models.ImageField(upload_to="room/battery/", blank=True, null=True, verbose_name="电池型号图片")
    battery_capacity = models.CharField(max_length=100, blank=True, null=True, verbose_name="电池容量")
    battery_capacity_img = models.ImageField(upload_to="room/battery/", blank=True, null=True, verbose_name="电池容量图片")
    battery_factory = models.CharField(max_length=100, blank=True, null=True, verbose_name="电池厂家")
    battery_factory_img = models.ImageField(upload_to="room/battery/", blank=True, null=True, verbose_name="电池厂家图片")
    battery_group_count = models.IntegerField(blank=True, null=True, verbose_name="电池组数")
    battery_group_count_img = models.ImageField(upload_to="room/battery/", blank=True, null=True, verbose_name="电池组数图片")

    # 空调
    ac_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="空调型号")
    ac_model_img = models.ImageField(upload_to="room/ac/", blank=True, null=True, verbose_name="空调型号图片")
    ac_capacity = models.CharField(max_length=100, blank=True, null=True, verbose_name="空调容量")
    ac_capacity_img = models.ImageField(upload_to="room/ac/", blank=True, null=True, verbose_name="空调容量图片")
    ac_factory = models.CharField(max_length=100, blank=True, null=True, verbose_name="空调厂家")
    ac_factory_img = models.ImageField(upload_to="room/ac/", blank=True, null=True, verbose_name="空调厂家图片")
    ac_count = models.IntegerField(blank=True, null=True, verbose_name="空调数量")
    ac_count_img = models.ImageField(upload_to="room/ac/", blank=True, null=True, verbose_name="空调数量图片")

    # 油机
    generator_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="油机型号")
    generator_model_img = models.ImageField(upload_to="room/generator/", blank=True, null=True, verbose_name="油机型号图片")
    generator_capacity = models.CharField(max_length=100, blank=True, null=True, verbose_name="油机容量")
    generator_capacity_img = models.ImageField(upload_to="room/generator/", blank=True, null=True, verbose_name="油机容量图片")
    generator_factory = models.CharField(max_length=100, blank=True, null=True, verbose_name="油机厂家")
    generator_factory_img = models.ImageField(upload_to="room/generator/", blank=True, null=True, verbose_name="油机厂家图片")
    generator_count = models.IntegerField(blank=True, null=True, verbose_name="油机数量")
    generator_count_img = models.ImageField(upload_to="room/generator/", blank=True, null=True, verbose_name="油机数量图片")

    # 交流配电箱
    ac_box_model = models.CharField(max_length=100, blank=True, null=True, verbose_name="交流配电箱型号")
    ac_box_model_img = models.ImageField(upload_to="room/ac_box/", blank=True, null=True, verbose_name="交流配电室型号图片")
    ac_box_capacity = models.CharField(max_length=100, blank=True, null=True, verbose_name="配电箱容量")
    ac_box_capacity_img = models.ImageField(upload_to="room/ac_box/", blank=True, null=True, verbose_name="配电箱容量图片")
    ac_box_factory = models.CharField(max_length=100, blank=True, null=True, verbose_name="配电箱厂家")
    ac_box_factory_img = models.ImageField(upload_to="room/ac_box/", blank=True, null=True, verbose_name="配电箱厂家图片")
    ac_box_count = models.IntegerField(blank=True, null=True, verbose_name="配电箱数量")
    ac_box_count_img = models.ImageField(upload_to="room/ac_box/", blank=True, null=True, verbose_name="配电箱数量图片")

    # 时间
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "机房信息"
        verbose_name_plural = "机房信息列表"
        ordering = ["-id"]

    def __str__(self):
        return self.room_name