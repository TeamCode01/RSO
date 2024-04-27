import io
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from django_celery_beat.models import (ClockedSchedule, CrontabSchedule,
                                       IntervalSchedule, PeriodicTask,
                                       SolarSchedule)
from django.http.response import HttpResponse
from import_export.admin import ImportExportModelAdmin
from rest_framework.authtoken.models import TokenProxy
from openpyxl import Workbook
from headquarters.models import UserDetachmentPosition, Detachment
from users.serializers import UserIdRegionSerializer
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


class UserRegionAdmin(admin.ModelAdmin):

    """
    Добавлен action с выгрузкойтаблицы с личной информацией всех пользователей
    в формате xlsx.
    """

    FIRST_ROW = 1
    FIRST_ROW_HEIGHT = 55
    ROW_FILTER_CELLS = 'A1:BZ1'
    FREEZE_HEADERS_ROW = 'D2'
    ZOOM_SCALE = 80
    EXCEL_HEADERS = [
            # 'Код региона прописки',
            # 'Регион прописки',
            'ID юзера',
            'Имя',
            'Фамилия',
            'Отчество',
            'Username',
            'Дата рождения',
            'Наличие паспорта РФ',
            'Серия и номер паспорта',
            'Кем выдан паспорт',
            'Дата выдачи паспорта',
            'Код подразделения',
            'ИНН',
            'СНИЛС',
            'Город прописки',
            'Адрес прописки',
            'Совпадает с фактическим адресом проживания',
            'Фактический регион ID',
            'Регион фактического проживания',
            'Город фактического проживания',
            'Адрес фактического проживания',
            'Название ОО',
            'Факультет',
            'Специальность',
            'Курс',
            'Телефон',
            'Email',
            'Ссылка на ВК',
            'Ссылка на Telegram',
            'Статус членства в РСО',
            'Статус верификации',
            'Статус оплаты членского взноса',
            # 'Член ЦШ',
            'Должность в ЦШ',
            'Командир ЦШ',
            # 'Член окружного штаба',
            'Должность в окр. штабе',
            'Командир окр.штаба',
            # 'Член регионального штаба',
            'Должность в рег. штабе',
            'Командир рег.штаба',
            # 'Член местного штаба',
            'Должность в мест. штабе',
            'Командир местного штаба',
            # 'Член образ. штаба',
            'Должность в образ. штабе',
            'Командир образ. штаба',
            # 'Член отряда',
            'Направление отряда(участник)',
            'Должность в отряде',
            'Командир отряда',
            'Направление отряда(командир)',
        ]

    actions = ['download_xlsx_users_data']
    list_display = ('user_id', 'user', 'reg_region', 'fact_region',)
    readonly_fields = (
        'user_id', 'user', 'reg_region', 'fact_region',
    )
    list_filter = ('reg_region', 'fact_region')

    @staticmethod
    def get_objects_data(cls, request):
        """Отсортированный кверисет для вывода на лист Excel."""

        queryset = UserRegion.objects.all()
        queryset = queryset.order_by('reg_region')
        serializer = UserIdRegionSerializer(queryset, many=True)
        return serializer.data

    def download_xlsx_users_data(self, request, queryset):
        file_stream = io.BytesIO()
        workbook = Workbook()
        worksheet = workbook.active

        """Настройка формата отображения листа."""

        worksheet.auto_filter.ref = self.ROW_FILTER_CELLS
        worksheet.append(self.EXCEL_HEADERS)
        worksheet.row_dimensions[self.FIRST_ROW].height = self.FIRST_ROW_HEIGHT
        worksheet.sheet_view.zoomScale = self.ZOOM_SCALE
        worksheet.freeze_panes = self.FREEZE_HEADERS_ROW

        data_for_excel = self.get_objects_data(
            self, request
        )
        for item in data_for_excel:
            worksheet.append(list(dict(item).values()))

        workbook.save(file_stream)

        file_stream.seek(0)
        response = HttpResponse(
            file_stream.getvalue(),
            content_type=(
                'application/'
                'vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        )
        response['Content-Disposition'] = (
            'attachment; filename="%s.xlsx"' % 'users_data'
        )

        return response

    download_xlsx_users_data.short_description = (
        'Скачать персональные данные пользователей в формате xlsx'
        ' (рекомендуется выгружать до 10 000 строк. Используйте фильтры.)'
    )


admin.site.register(UserRegion, UserRegionAdmin)


admin.site.unregister(Group)
admin.site.unregister(PeriodicTask)
admin.site.unregister(IntervalSchedule)
admin.site.unregister(CrontabSchedule)
admin.site.unregister(ClockedSchedule)
admin.site.unregister(SolarSchedule)

if not settings.DEBUG:
    admin.site.unregister(TokenProxy)
