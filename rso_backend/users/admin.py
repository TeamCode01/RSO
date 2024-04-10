from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django_celery_beat.models import (ClockedSchedule, CrontabSchedule,
                                       IntervalSchedule, PeriodicTask,
                                       SolarSchedule)
from import_export.admin import ImportExportModelAdmin
from rest_framework.authtoken.models import TokenProxy

from headquarters.models import UserDetachmentPosition
from users.forms import RSOUserForm
from users.models import (AdditionalForeignDocs, RSOUser, UserDocuments, UserEducation, UserForeignDocuments, UserForeignParentDocs, UserMedia,
                          UserMemberCertLogs, UserMembershipLogs, UserParent,
                          UserPrivacySettings, UserRegion,
                          UserStatementDocuments, UserVerificationLogs)
from users.resources import RSOUserResource


class UserRegionInline(admin.StackedInline):
    model = UserRegion
    extra = 0


class UserMediaInline(admin.StackedInline):
    model = UserMedia
    extra = 0


class UserEducationInline(admin.StackedInline):
    model = UserEducation
    extra = 0


class UserDocumentsInline(admin.StackedInline):
    model = UserDocuments
    extra = 0


class UserPrivacySettingsInline(admin.StackedInline):
    model = UserPrivacySettings
    extra = 0


class UsersParentInline(admin.StackedInline):
    model = UserParent
    extra = 0


class UserStatementDocumentsInLine(admin.StackedInline):
    model = UserStatementDocuments
    extra = 0


class UserForeignDocumentsInline(admin.StackedInline):
    model = UserForeignDocuments
    extra = 0


class UserForeignParentDocsInline(admin.StackedInline):
    model = UserForeignParentDocs
    extra = 0


@admin.register(RSOUser)
class UserAdmin(ImportExportModelAdmin, BaseUserAdmin):

    def detachment_name(self, obj):
        """
        Return the name of the detachment the user belongs to.
        """
        try:
            return obj.userdetachmentposition.headquarter.name
        except UserDetachmentPosition.DoesNotExist:
            return None

    detachment_name.short_description = 'Отряд'

    resource_class = RSOUserResource
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'first_name',
                'last_name',
                'patronymic_name',
                'gender',
                'region',
                'password1',
                'password2'
            ),
        }),
    )
    inlines = [
        UserRegionInline,
        UserMediaInline,
        UserEducationInline,
        UserDocumentsInline,
        UserPrivacySettingsInline,
        UsersParentInline,
        UserStatementDocumentsInLine,
        UserForeignDocumentsInline,
        UserForeignParentDocsInline,
    ]

    list_display = (
        'username',
        'id',
        'email',
        'first_name',
        'last_name',
        'patronymic_name',
        'is_verified',
        'membership_fee',
        'is_staff',
        'region',
        'detachment_name',
        'date_joined',
        'last_login',
    )
    search_fields = (
        'username',
        'first_name',
        'last_name',
        'patronymic_name',
        'email',
    )
    readonly_fields = ('date_joined', 'last_login')
    list_filter = (
        'date_joined',
        'last_login',
        'is_verified',
        'membership_fee',
        'is_staff',
        'region',
    )

    filter_horizontal = ()
    fieldsets = ()


@admin.register(UserMembershipLogs)
class UserMembershipLogsAdmin(admin.ModelAdmin):
    list_display = ('user', 'status_changed_by', 'date', 'period', 'status',)
    readonly_fields = (
        'user', 'status_changed_by', 'date', 'period', 'status', 'description'
    )
    list_filter = ('date', 'period', 'status')

    def has_add_permission(self, request, obj=None):
        """Запрещаем добавление записи через админку."""
        return False


@admin.register(UserMemberCertLogs)
class UserMemberCertLogsAdmin(admin.ModelAdmin):
    list_display = ('user', 'cert_issued_by', 'date', 'cert_type')
    readonly_fields = (
        'user', 'cert_issued_by', 'date', 'cert_type', 'description'
    )
    list_filter = ('date', 'cert_type')

    def has_add_permission(self, request, obj=None):
        """Запрещаем добавление записи через админку."""
        return False


@admin.register(UserVerificationLogs)
class UserVerificationLogsAdmin(admin.ModelAdmin):
    """Таблица логов верификации пользователей."""

    list_display = ('user', 'date', 'description', 'verification_by')
    readonly_fields = ('user', 'date', 'description', 'verification_by')
    list_filter = ('date', 'description')

    def has_add_permission(self, request, obj=None):
        """Запрещаем добавление записи через админку."""
        return False


admin.site.unregister(Group)
admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(ClockedSchedule)
admin.site.unregister(SolarSchedule)

if not settings.DEBUG:
    admin.site.unregister(TokenProxy)
