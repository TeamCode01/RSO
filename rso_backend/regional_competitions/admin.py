from django.contrib import admin

from regional_competitions.models import (CHqRejectingLog, RegionalR4,
                                          RegionalR4Event, RegionalR4Link,
                                          RVerificationLog,
                                          StatisticalRegionalReport)


@admin.register(StatisticalRegionalReport)
class StatisticalRegionalReportAdmin(admin.ModelAdmin):
    list_display = (
        'regional_headquarter',
        'participants_number',
        'employed_sso',
        'employed_spo',
        'employed_oop',
        'employed_smo',
        'employed_sservo',
        'employed_sses',
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
