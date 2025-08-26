# ServiceRequest/admin.py

from django.contrib import admin
from django import forms
from django.utils.safestring import mark_safe
from .models import ServiceRequest, IssueOption, Tag


# ===========================
# Форма для TagAdmin — с цветовым пикером
# ===========================

class TagAdminForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = '__all__'
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color'}),  # HTML5 color picker
        }


# ===========================
# Админка: Теги (Tag)
# ===========================

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """
    Админка для тегов с поддержкой цвета.
    Позволяет выбирать цвет в интерфейсе.
    """
    form = TagAdminForm

    list_display = ('colored_name', 'code', 'color', 'color_preview')
    list_editable = ('code', 'color')
    search_fields = ('name', 'code')
    ordering = ('name',)

    @admin.display(description="Название")
    def colored_name(self, obj):
        return mark_safe(
            f'<span style="color: {obj.color}; font-weight: 500;">{obj.name}</span>'
        )

    @admin.display(description="Цвет")
    def color_preview(self, obj):
        return mark_safe(
            f'<span style="display:inline-block; width:16px; height:16px; '
            f'border-radius: 50%; background-color:{obj.color};"></span>'
        )


# ===========================
# Админка: Симптомы (IssueOption)
# ===========================

@admin.register(IssueOption)
class IssueOptionAdmin(admin.ModelAdmin):
    """
    Админка для симптомов неисправности.
    """
    list_display = ('get_code_display', 'description', 'code')
    list_display_links = ('get_code_display',)
    search_fields = ('description', 'code')
    ordering = ('code',)

    def get_code_display(self, obj):
        return obj.get_code_display()
    get_code_display.short_description = 'Симптом'


# ===========================
# Админка: Заявки (ServiceRequest)
# ===========================

@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    """
    Админка для заявок в сервисный центр.
    Полный контроль: фильтры, поиск, цветные теги, редактирование.
    """
    list_display = (
        'id',
        'full_name',
        'customer_type',
        'get_device_type_display',
        'phone_number',
        'status',
        'display_tags',
        'created_at',
    )
    list_display_links = ('id', 'full_name')
    list_editable = ('status',)
    list_filter = (
        'status',
        'customer_type',
        'device_type',
        'tags',
        'created_at',
    )
    search_fields = (
        'full_name',
        'phone_number',
        'email',
        'address',
        'organization_name',
        'inn',
    )
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    autocomplete_fields = ('tags', 'issues')
    ordering = ['-created_at']
    list_per_page = 25

    fieldsets = (
        ('Заказчик', {
            'fields': ('customer_type', 'full_name', 'organization_name', 'inn', 'email')
        }),
        ('Контакты', {
            'fields': ('phone_number', 'address', 'external_links')
        }),
        ('Устройство', {
            'fields': ('device_type', 'issues', 'issues_other', 'description')
        }),
        ('Статус и теги', {
            'fields': ('status', 'tags'),
            'classes': ('wide',)
        }),
        ('Системная информация', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # при создании
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description='Теги')
    def display_tags(self, obj):
        if not obj.tags.exists():
            return mark_safe('<span style="color: #6b7280; font-size: 12px;">—</span>')

        tags = []
        for tag in obj.tags.all():
            tags.append(
                f'<span style="'
                f'color: {tag.color}; '
                f'background-color: {tag.color}22; '
                f'border: 1px solid {tag.color}; '
                f'padding: 2px 6px; '
                f'border-radius: 4px; '
                f'font-size: 12px; '
                f'font-weight: 500; '
                f'white-space: nowrap;">'
                f'{tag.name}'
                f'</span>'
            )
        return mark_safe(' '.join(tags))