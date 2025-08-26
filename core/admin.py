from django.contrib import admin

# Register your models here.
from django.contrib import admin
from core.models import Computer, ComputerImage

class ComputerImageInline(admin.TabularInline):
    model = ComputerImage
    extra = 1

@admin.register(Computer)
class ComputerAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'is_available']
    list_filter = ['category', 'is_available', 'created_at']
    search_fields = ['name', 'short_description']
    inlines = [ComputerImageInline]

@admin.register(ComputerImage)
class ComputerImageAdmin(admin.ModelAdmin):
    list_display = ['computer', 'is_main', 'order']
    list_editable = ['is_main', 'order']