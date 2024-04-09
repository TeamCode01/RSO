from django.utils.safestring import mark_safe
from django.contrib import admin
from questions.models import Question, AnswerOption, Attempt, UserAnswer
from import_export.admin import ExportActionModelAdmin


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
class AttemptAdmin(ExportActionModelAdmin, admin.ModelAdmin):
    list_display = ('id', 'user', 'timestamp', 'category', 'score', 'is_valid', 'get_user_region', 'get_user_position')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'category', 'user__region', 'user__userdetachmentposition__headquarter__name')
    list_filter = ('timestamp', 'category')
    readonly_fields = ('user', 'timestamp', 'score', 'category', 'questions')

    def get_user_region(self, obj):
        return obj.user.region
    get_user_region.admin_order_field = 'user__region'
    get_user_region.short_description = 'Регион'

    def get_user_position(self, obj):
        detachment_position = getattr(obj.user, 'userdetachmentposition', None)
        return detachment_position.headquarter.name if detachment_position and getattr(detachment_position, 'headquarter', None) else None
    get_user_position.admin_order_field = 'user__userdetachmentposition__headquarter__name'
    get_user_position.short_description = 'Должность'

    # def has_add_permission(self, request, obj=None):
    #     return False

    # def has_change_permission(self, request, obj=None):
    #     return False


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
