from django.contrib import admin
from .models import (Category, TestGroup, TestParameter,
                     COA, COAResult, COACustomField, COALabel,
                     ItemMaster, Customer)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display  = ['name', 'code']
    search_fields = ['name']


@admin.register(TestGroup)
class TestGroupAdmin(admin.ModelAdmin):
    list_display  = ['name', 'category', 'order']
    list_filter   = ['category']


@admin.register(TestParameter)
class TestParameterAdmin(admin.ModelAdmin):
    list_display  = ['name', 'category', 'group', 'specification', 'order']
    list_filter   = ['category']
    search_fields = ['name']


class COAResultInline(admin.TabularInline):
    model  = COAResult
    extra  = 0
    fields = ['parameter', 'result', 'standard_override']


class COACustomFieldInline(admin.TabularInline):
    model  = COACustomField
    extra  = 0
    fields = ['field_name', 'specification', 'result', 'order']


@admin.register(COA)
class COAAdmin(admin.ModelAdmin):
    list_display   = ['product_name', 'batch_no', 'category', 'customer_name',
                      'manufacturing_date', 'expiry_date', 'status', 'created_at']
    list_filter    = ['category', 'status']
    search_fields  = ['product_name', 'batch_no', 'customer_name', 'botanical_name']
    readonly_fields = ['batch_no', 'expiry_date', 'created_at']
    inlines        = [COAResultInline, COACustomFieldInline]


@admin.register(COALabel)
class COALabelAdmin(admin.ModelAdmin):
    list_display  = ['coa', 'invoice_no', 'gross_weight', 'net_weight', 'created_at']
    search_fields = ['invoice_no', 'coa__product_name']


@admin.register(ItemMaster)
class ItemMasterAdmin(admin.ModelAdmin):
    list_display   = ['item_name', 'item_category', 'botanical_name', 'plant_part']
    list_filter    = ['item_category']
    search_fields  = ['item_name', 'botanical_name']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display  = ['name']
    search_fields = ['name']


from .models import ProductStandard

@admin.register(ProductStandard)
class ProductStandardAdmin(admin.ModelAdmin):
    list_display  = ['product_name', 'updated_at']
    search_fields = ['product_name']
    readonly_fields = ['updated_at']


from .models import OldCOA

@admin.register(OldCOA)
class OldCOAAdmin(admin.ModelAdmin):
    list_display  = ['file_name', 'product', 'customer', 'batch', 'mfg_date']
    search_fields = ['file_name', 'product', 'customer', 'batch']
    readonly_fields = ['file_name', 'customer', 'product', 'batch', 'mfg_date',
                       'botanical', 'part_used', 'fields']