from django.contrib import admin

from regional_competitions.factories import RAdminFactory
from regional_competitions.models import (CHqRejectingLog, ExpertRole, RegionalR1, RegionalR18, RegionalR18Link, RegionalR18Project, RegionalR2,
                                          RegionalR4, RegionalR4Event,
                                          RegionalR4Link, RegionalR5,
                                          RegionalR5Event, RegionalR5Link,
                                          RegionalR11, RegionalR12,
                                          RegionalR13, RegionalR14,
                                          RegionalR16, RegionalR16Link,
                                          RegionalR16Project, RegionalR17,
                                          RegionalR19, RegionalR101,
                                          RegionalR101Link, RegionalR102,
                                          RegionalR102Link, RVerificationLog,
                                          StatisticalRegionalReport,
                                          r6_models_factory,
                                          r7_models_factory, r9_models_factory)
from regional_competitions.r_calculations import calculate_r13_score, calculate_r2_score


@admin.register(StatisticalRegionalReport)
class StatisticalRegionalReportAdmin(admin.ModelAdmin):
    list_display = (
        'regional_headquarter',
        'participants_number',
        'employed_sso',
        'employed_spo',
        'employed_sop',
        'employed_smo',
        'employed_sservo',
        'employed_ssho',
        'employed_specialized_detachments',
        'employed_production_detachments',
        'employed_top',
    )
    search_fields = (
        'regional_headquarter__name',
        'regional_headquarter__id',
    )


@admin.register(RVerificationLog)
class RVerificationLogAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'district_headquarter',
        'central_headquarter',
        'regional_headquarter',
        'is_regional_data',
        'is_district_data',
        'is_central_data',
        'report_number',
        'report_id',
        'created_at'
    )
    search_fields = (
        'user__last_name',
        'user__username',
        'district_headquarter__name',
        'central_headquarter__name',
        'regional_headquarter__name',
    )
    list_filter = (
        'district_headquarter',
        'central_headquarter',
        'report_number',
        'is_regional_data',
        'is_district_data',
        'is_central_data',
    )
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': (
                'user',
                'central_headquarter',
                'district_headquarter',
                'regional_headquarter',
                'is_regional_data',
                'is_district_data',
                'is_central_data',
                'report_number',
                'report_id',
                'data'
            )
        }),
        ('Время', {
            'fields': ('created_at',),
        }),
    )


@admin.register(CHqRejectingLog)
class CHqRejectingLogAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'report_number',
        'report_id',
        'created_at'
    )
    search_fields = (
        'user__username',
        'user__last_name',
        'report_number',
        'report_id'
    )
    list_filter = (
        'report_number',
        'created_at'
    )
    readonly_fields = ('created_at',)
    fieldsets = (
        (None, {
            'fields': (
                'user',
                'report_number',
                'report_id',
                'reasons'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at',),
        }),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.select_related('user')
        return queryset


@admin.register(RegionalR1)
class RegionalR1Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'score',
        'amount_of_money',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    list_filter = ('verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RegionalR2)
class RegionalR2Admin(admin.ModelAdmin):

    list_display = (
        'id',
        'regional_headquarter',
        'score',
        'created_at',
        'updated_at'
    )
    search_fields = ('regional_headquarter__name',)
    readonly_fields = ('created_at', 'updated_at')

    actions = ['get_ro_score',]

    def get_ro_score(self, request, queryset):
        for obj in queryset:
            calculate_r2_score(obj)

    get_ro_score.short_description = 'Вычислить очки по показателю'


class RegionalR4LinkInline(admin.TabularInline):
    model = RegionalR4Link
    extra = 0


class RegionalR4EventAdminInline(admin.StackedInline):
    model = RegionalR4Event
    extra = 0

    class RegionalR4LinkInline(admin.TabularInline):
        model = RegionalR4Link
        extra = 0

    inlines = [RegionalR4LinkInline]


@admin.register(RegionalR4Event)
class RegionalR4EventAdmin(admin.ModelAdmin):
    list_display = ('id', 'regional_r4', 'participants_number', 'start_date', 'end_date', 'is_interregional')
    search_fields = ('regional_r4__id',)
    list_filter = ('is_interregional', 'start_date', 'end_date', 'regional_r4')
    inlines = [RegionalR4LinkInline]


@admin.register(RegionalR4)
class RegionalR4Admin(admin.ModelAdmin):
    list_display = (
        'regional_headquarter',
        'id',
        'is_sent',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at',
        'score',
    )
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('regional_headquarter__name', 'comment')
    list_filter = ('is_sent', 'verified_by_chq', 'verified_by_dhq')
    inlines = [RegionalR4EventAdminInline]


class RegionalR5LinkInline(admin.TabularInline):
    model = RegionalR5Link
    extra = 0


class RegionalR5EventAdminInline(admin.StackedInline):
    model = RegionalR5Event
    extra = 0

    class RegionalR5LinkInline(admin.TabularInline):
        model = RegionalR5Link
        extra = 0

    inlines = [RegionalR5LinkInline]


@admin.register(RegionalR5Event)
class RegionalR5EventAdmin(admin.ModelAdmin):
    list_display = ('id', 'regional_r5', 'participants_number', 'ro_participants_number', 'start_date', 'end_date',)
    search_fields = ('regional_r5__id',)
    list_filter = ('start_date', 'end_date', 'regional_r5')
    inlines = [RegionalR5LinkInline]


@admin.register(RegionalR5)
class RegionalR5Admin(admin.ModelAdmin):
    list_display = (
        'regional_headquarter',
        'id',
        'is_sent',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at',
        'score',
    )
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('regional_headquarter__name', 'comment')
    list_filter = ('is_sent', 'verified_by_chq', 'verified_by_dhq')
    inlines = [RegionalR5EventAdminInline]


r6_list_display = (
    'regional_headquarter',
    'id',
    'number_of_members',
    'verified_by_chq',
    'verified_by_dhq',
    'score',
    'created_at',
    'updated_at'
)

r6_list_filter = (
    'verified_by_chq',
    'verified_by_dhq'
)

r6_search_fields = ('comment', 'regional_headquarter__name')

r6_readonly_fields = ('created_at', 'updated_at')

r6_admin_factory = RAdminFactory(
    models=r6_models_factory.models,
    list_display=r6_list_display,
    list_filter=r6_list_filter,
    search_fields=r6_search_fields,
    readonly_fields=r6_readonly_fields
)
r6_admin_factory.create_admin_classes()


r7_list_display = (
    'regional_headquarter',
    'id',
    'prize_place',
    'document',
    'verified_by_chq',
    'verified_by_dhq',
    'score',
    'created_at',
    'updated_at'
)

r7_list_filter = (
    'prize_place',
    'verified_by_chq',
    'verified_by_dhq'
)

r7_search_fields = ('comment', 'regional_headquarter__name')

r7_readonly_fields = ('created_at', 'updated_at')

r7_admin_factory = RAdminFactory(
    models=r7_models_factory.models,
    list_display=r7_list_display,
    list_filter=r7_list_filter,
    search_fields=r7_search_fields,
    readonly_fields=r7_readonly_fields
)
r7_admin_factory.create_admin_classes()


r9_list_display = (
    'regional_headquarter',
    'id',
    'event_happened',
    'document',
    'verified_by_chq',
    'verified_by_dhq',
    'score',
    'created_at',
    'updated_at'
)
r9_list_filter = ('event_happened', 'verified_by_chq', 'verified_by_dhq')
r9_search_fields = ('comment',)
r9_readonly_fields = ('created_at', 'updated_at')

r9_admin_factory = RAdminFactory(
    models=r9_models_factory.models,
    list_display=r9_list_display,
    list_filter=r9_list_filter,
    search_fields=r9_search_fields,
    readonly_fields=r9_readonly_fields
)
r9_admin_factory.create_admin_classes()


class RegionalR101LinkInline(admin.TabularInline):
    model = RegionalR101Link
    extra = 0


@admin.register(RegionalR101)
class RegionalR101Admin(admin.ModelAdmin):
    list_display = (
        'id', 'event_happened', 'document', 'verified_by_chq', 'verified_by_dhq', 'score', 'created_at', 'updated_at'
    )
    search_fields = ('comment',)
    list_filter = ('event_happened', 'verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RegionalR101LinkInline]


class RegionalR102LinkInline(admin.TabularInline):
    model = RegionalR102Link
    extra = 0


@admin.register(RegionalR102)
class RegionalR102Admin(admin.ModelAdmin):
    list_display = (
        'id', 'event_happened', 'document', 'verified_by_chq', 'verified_by_dhq', 'score', 'created_at', 'updated_at'
    )
    search_fields = ('comment',)
    list_filter = ('event_happened', 'verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RegionalR102LinkInline]


@admin.register(RegionalR11)
class RegionalR11Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'score',
        'participants_number',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    list_filter = ('verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RegionalR12)
class RegionalR12Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'score',
        'amount_of_money',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    list_filter = ('verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RegionalR13)
class RegionalR13Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'score',
        'number_of_members',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    list_filter = ('verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['get_ro_score',]

    @admin.action(description='Вычислить очки по показателю')
    def get_ro_score(self, request, queryset):
        calculate_r13_score()

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('regional_headquarter')


@admin.register(RegionalR14)
class RegionalR14Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'report_12',
        'report_13',
        'score'
    )
    search_fields = ('id', 'report_12__regional_headquarter__name')


class RegionalR16LinkInline(admin.TabularInline):
    model = RegionalR16Link
    extra = 0


class RegionalR16ProjectInline(admin.TabularInline):
    model = RegionalR16Project
    extra = 0


@admin.register(RegionalR16Project)
class RegionalR16ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_r16',
        'name',
        'project_scale',
        'regulations'
    )
    search_fields = ('name',)
    list_filter = ('project_scale',)
    inlines = [RegionalR16LinkInline]


@admin.register(RegionalR16)
class RegionalR16Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'is_project',
        'score',
        'verified_by_chq',
        'verified_by_dhq',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment',)
    list_filter = ('is_project', 'verified_by_chq', 'verified_by_dhq')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RegionalR16ProjectInline]


@admin.register(RegionalR17)
class RegionalR17Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    readonly_fields = ('created_at', 'updated_at')


class RegionalR18LinkInline(admin.TabularInline):
    model = RegionalR18Link
    extra = 0


class RegionalR18ProjectInline(admin.TabularInline):
    model = RegionalR18Project
    extra = 0


@admin.register(RegionalR18Project)
class RegionalR18ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_r18',
        'file',
    )
    search_fields = ('name',)
    inlines = [RegionalR18LinkInline]


@admin.register(RegionalR18)
class RegionalR18Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment',)
    readonly_fields = ('created_at', 'updated_at')
    inlines = [RegionalR18ProjectInline]


@admin.register(RegionalR19)
class RegionalR19Admin(admin.ModelAdmin):
    list_display = (
        'id',
        'regional_headquarter',
        'created_at',
        'updated_at'
    )
    search_fields = ('comment', 'regional_headquarter__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ExpertRole)
class ExpertRoleAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'central_headquarter',
        'district_headquarter',
        'created_at',
    )
    search_fields = (
        'user__username',
        'central_headquarter__name',
        'district_headquarter__name'
    )
