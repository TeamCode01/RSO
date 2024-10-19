from django.conf import settings
from django.contrib import admin
from django.utils.safestring import mark_safe

from questions.models import AnswerOption, Attempt, Question, UserAnswer
from headquarters.models import Detachment
import io
from openpyxl import Workbook
from django.http.response import HttpResponse


class AnswerOptionInline(admin.TabularInline):
    model = AnswerOption
    extra = 0
    can_delete = True
    fields = ('text', 'image', 'is_correct')


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'block', 'image_tag')
    search_fields = ('title', 'block')
    list_filter = ('block',)
    inlines = [AnswerOptionInline]

    def image_tag(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="150" height="auto" />')
        return "No Image"

    image_tag.short_description = 'Image'


@admin.register(AnswerOption)
class AnswerOptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'text', 'question_id', 'is_correct', 'image_tag')
    search_fields = ('text', 'question__title')
    list_filter = ('is_correct', 'question__block')

    def image_tag(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" width="150" height="auto" />')
        return "No Image"

    image_tag.short_description = 'Image'


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    FIRST_ROW = 1
    FIRST_ROW_HEIGHT = 55
    ROW_FILTER_CELLS = 'A1:BZ1'
    FREEZE_HEADERS_ROW = 'D2'
    ZOOM_SCALE = 80
    EXCEL_HEADERS = [
        'ID',
        'Пользователь',
        'Время',
        'Категория',
        'Баллы',
        'Валидность',
        'Регион',
        'Должность',
        'Отряд',
    ]
    actions = ['download_xlsx_users_data']
    list_display = (
        'id', 'user', 'timestamp', 'category', 'score', 'is_valid', 'get_user_region', 'get_user_position', 'get_user_detachment'
        )
    search_fields = ('user__last_name', 'user__first_name', 'category')
    list_filter = ('timestamp', 'category', 'user__region')
    readonly_fields = ('user', 'timestamp', 'score', 'category', 'questions')
    list_per_page = 25

    def get_user_region(self, obj):
        return obj.user.region

    get_user_region.admin_order_field = 'user__region'
    get_user_region.short_description = 'Регион'

    def get_user_detachment(self, obj):
        detachment = Detachment.objects.filter(commander=obj.user).first()
        if detachment:
            return detachment.name
        else:
            detachment_position = getattr(obj.user, 'userdetachmentposition', None)
            return detachment_position.headquarter.name if detachment_position and hasattr(
                detachment_position,
                'headquarter'
            ) else None

    get_user_detachment.admin_order_field = 'user__userdetachmentposition__headquarter__name'
    get_user_detachment.short_description = 'Отряд'

    def get_user_position(self, obj):
        if Detachment.objects.filter(commander=obj.user).exists():
            return "Командир"
        else:
            user_detachment_position = getattr(obj.user, 'userdetachmentposition', None)
            return user_detachment_position.position.name if user_detachment_position and hasattr(
                user_detachment_position, 'position'
            ) else "-"

    get_user_position.admin_order_field = 'user__userdetachmentposition'
    get_user_position.short_description = 'Должность'

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

        for obj in queryset:
            region_name = obj.user.region.name if obj.user.region else None
            worksheet.append([
                obj.id,
                obj.user.get_full_name(),
                obj.timestamp,
                obj.category,
                obj.score,
                obj.is_valid,
                region_name,
                self.get_user_position(obj),
                self.get_user_detachment(obj)
            ])

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
        'Скачать попытки пользователей в формате xlsx'
    )

    def has_add_permission(self, request, obj=None):
        return settings.DEBUG

    def has_change_permission(self, request, obj=None):
        return settings.DEBUG

    def has_delete_permission(self, request, obj=None):
        return settings.DEBUG


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = (
        'attempt_id', 'get_username', 'get_user_id', 'question_id', 'answer_option_id', 'answer_option_is_correct'
    )
    search_fields = ('attempt__user__username', 'question__title', 'answer_option__text')
    list_filter = ('attempt__category', 'question__block')
    readonly_fields = ('attempt', 'question', 'answer_option')

    def get_username(self, obj):
        return obj.attempt.user.username

    get_username.admin_order_field = 'attempt__user__username'
    get_username.short_description = 'Username'

    def answer_option_is_correct(self, obj):
        return obj.answer_option.is_correct

    answer_option_is_correct.boolean = True
    answer_option_is_correct.admin_order_field = 'answer_option__is_correct'
    answer_option_is_correct.short_description = 'Is Correct'

    def get_user_id(self, obj):
        return obj.attempt.user.id

    get_user_id.admin_order_field = 'attempt__user__id'
    get_user_id.short_description = 'User ID'

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
