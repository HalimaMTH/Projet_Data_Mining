from django.contrib import admin
from .models import Product, SearchHistory

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price_mad', 'site', 'cluster', 'created_at']
    list_filter = ['site', 'cluster', 'anomaly']
    search_fields = ['name']

@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    list_display = ['query', 'site', 'result_count', 'created_at']
    list_filter = ['site', 'created_at']