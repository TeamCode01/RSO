from django.db import models


class StatisticalRegionalReport(models.Model):
    regional_headquarter = models.OneToOneField(
        'headquarters.RegionalHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='Региональный штаб'
    )
    participants_number = models.PositiveIntegerField(
        verbose_name='Количество членов регионального отделения'
    )
    employed_sso = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных ССО'
    )
    employed_spo = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных СПО'
    )
    employed_sop = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных СОП'
    )
    employed_smo = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных СМО'
    )
    employed_sservo = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных ССервО'
    )
    employed_ssho = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных ССхО'
    )
    employed_specialized_detachments = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных, профильные отряды'
    )
    employed_production_detachments = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных, производственные отряды'
    )
    employed_top = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных, ТОП'
    )

    class Meta:
        verbose_name_plural = 'Статистические отчеты РШ'
        verbose_name = 'Статистический отчет РШ'

    def __str__(self):
        return f'Отчет {self.regional_headquarter.name}'
