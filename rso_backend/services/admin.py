from django.contrib import admin

from services.models import FrontError

@admin.register(FrontError)
class FrontErrorAdmin(admin.ModelAdmin):
    list_display = (
        'method',
        'url',
        'error_code',
        'error_description',
        'created_at',
        'user'
    )
    list_filter = ('created_at', 'method', 'error_code')
    search_fields = ('user__id',)
    readonly_fields = ('created_at', 'user')

    def has_add_permission(self, request, obj=None):
        """Запрещаем добавление записи через админку."""
        return False
