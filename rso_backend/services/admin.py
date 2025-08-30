from django.conf import settings
from django.contrib import admin

from services.models import Blocklist, FrontError


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


@admin.register(Blocklist)
class BlocklistAdmin(admin.ModelAdmin):
    list_display = ('ip_addr', 'created_at')
    search_fields = ('ip_addr',)

    def has_add_permission(self, request, obj=None):
        """Запрещаем добавление записи через админку на продакшене."""
        return settings.DEBUG
