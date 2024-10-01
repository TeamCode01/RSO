from io import BytesIO
from api.utils import count_sql_queries
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Prefetch
from django.http import HttpResponse
from django_celery_beat.models import (ClockedSchedule, CrontabSchedule,
                                       IntervalSchedule, PeriodicTask,
                                       SolarSchedule)
from headquarters.utils import create_central_hq_member
from import_export.admin import ImportExportModelAdmin
from openpyxl import Workbook
from users.constants import REGION_USERS_DATA_HEADERS
from rest_framework.authtoken.models import TokenProxy

from headquarters.models import Detachment
from users.models import (RSOUser, UserDocuments,
                          UserEducation, UserForeignDocuments,
                          UserForeignParentDocs, UserMedia, UserMemberCertLogs,
                          UserMembershipLogs, UserParent, UserPrivacySettings,
                          UserRegion, UserStatementDocuments,
                          UserVerificationLogs)
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

    actions = [
        'add_to_central_headquarter_position',
        'get_users_data'
    ]

    def add_to_central_headquarter_position(self, request, queryset):
        """

        Добавление юзера в члены ЦШ через action в разделе таблицы
        "Пользователи".
        """

        for user in queryset:
            create_central_hq_member(
                headquarter_id=settings.CENTRAL_HQ_ID,
                user_id=user.id
            )

    def prepared_users_data(self, request, queryset):
        user_ids = queryset.values_list('id', flat=True)
        all_users_data = (
            RSOUser.objects.select_related(
                'documents',
                'education',
                'user_region__reg_region',
                'user_region__fact_region__fact_region',
                'detachment_commander',
                'detachment_commander__area',
            ).prefetch_related(
                'usercentralheadquarterposition__position',
                'userdistrictheadquarterposition__headquarter',
                'userdistrictheadquarterposition__position',
                'userregionalheadquarterposition__position',
                'userregionalheadquarterposition__headquarter',
                'usereducationalheadquarterposition__position',
                'usereducationalheadquarterposition__headquarter',
                'userdetachmentposition__position',
                'userdetachmentposition__headquarter',
                'userdetachmentposition__headquarter__area',
                'districtheadquarter_commander',
                'regionalheadquarter_commander',
                'localheadquarter_commander',
                'educationalheadquarter_commander',
            ).filter(
                id__in=user_ids
            ).values_list(
                'user_region__reg_region__code',
                'user_region__reg_region__name',
                'id',
                'first_name',
                'last_name',
                'patronymic_name',
                'username',
                'date_of_birth',
                'documents__russian_passport',
                'documents__pass_ser_num',
                'documents__pass_whom',
                'documents__pass_date',
                'documents__pass_code',
                'documents__inn',
                'documents__snils',
                'user_region__reg_town',
                'user_region__reg_house',
                'user_region__reg_fact_same_address',
                'user_region__fact_region_id',
                'user_region__fact_region__fact_region__reg_region',
                'user_region__fact_town',
                'user_region__fact_house',
                'education__study_institution',
                'education__study_faculty',
                'education__study_specialty',
                'education__study_year',
                'phone_number',
                'email',
                'social_vk',
                'social_tg',
                'is_rso_member',
                'is_verified',
                'membership_fee',
                'usercentralheadquarterposition__position__name',
                'userdistrictheadquarterposition__headquarter__name',
                'userdistrictheadquarterposition__position__name',
                'districtheadquarter_commander',
                'userregionalheadquarterposition__headquarter__name',
                'userregionalheadquarterposition__position__name',
                'regionalheadquarter_commander',
                'userlocalheadquarterposition__headquarter__name',
                'userlocalheadquarterposition__position__name',
                'localheadquarter_commander',
                'usereducationalheadquarterposition__headquarter__name',
                'usereducationalheadquarterposition__position__name',
                'educationalheadquarter_commander',
                'userdetachmentposition__position__name',
                'userdetachmentposition__headquarter__area__name',
                'detachment_commander',
                'detachment_commander__area__name',
            ).distinct()
        )
        return all_users_data

    @count_sql_queries
    def get_users_data(self, request, queryset):
        workbook = Workbook()
        worksheet = workbook.active
        worksheet.title = 'Пользователи'
        worksheet.append(REGION_USERS_DATA_HEADERS[1:])

        for _, row in enumerate(
            self.prepared_users_data(request, queryset), start=1
        ):
            worksheet.append(row)

        file_content = BytesIO()
        workbook.save(file_content)
        file_content.seek(0)

        response = HttpResponse(
            file_content.read(),
            content_type=(
                'application/vnd.openxmlformats-officedocument'
                '.spreadsheetml.sheet'
            )
        )
        response['Content-Disposition'] = (
            'attachment; filename=users_data.xlsx'
        )
        return response

    add_to_central_headquarter_position.short_description = (
        'Добавить юзера в ЦШ'
    )
    get_users_data.short_description = 'Выгрузить данные пользователей'

    def detachment_name(self, obj):
        """
        Return the name of the detachment the user belongs to.
        """
        detachment = Detachment.objects.filter(commander=obj).first()
        if detachment:
            return detachment.name
        else:
            detachment_position = getattr(obj, 'userdetachmentposition', None)
            return detachment_position.headquarter.name if detachment_position and hasattr(
                detachment_position,
                'headquarter'
            ) else None

    def get_user_position(self, obj):
        if Detachment.objects.filter(commander=obj).exists():
            return "Командир"
        else:
            user_detachment_position = getattr(obj, 'userdetachmentposition', None)
            return user_detachment_position.position.name if user_detachment_position and hasattr(
                user_detachment_position, 'position'
            ) else "-"

    get_user_position.admin_order_field = 'user__userdetachmentposition'
    get_user_position.short_description = 'Должность'

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
        'reports_access',
        'region',
        'detachment_name',
        'get_user_position',
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
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

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
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

    def has_add_permission(self, request, obj=None):
        """Запрещаем добавление записи через админку."""
        return False


@admin.register(UserVerificationLogs)
class UserVerificationLogsAdmin(admin.ModelAdmin):
    """Таблица логов верификации пользователей."""

    list_display = ('user', 'date', 'description', 'verification_by')
    readonly_fields = ('user', 'date', 'description', 'verification_by')
    list_filter = ('date', 'description')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

    def has_add_permission(self, request, obj=None):
        """Запрещаем добавление записи через админку."""
        return False


admin.site.site_header = 'Российские Студенческие Отряды'
admin.site.index_title = 'Администрирование ЛК РСО'


admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(ClockedSchedule)
admin.site.unregister(SolarSchedule)

if not settings.DEBUG:
    admin.site.unregister(TokenProxy)
