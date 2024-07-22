from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import PositiveSmallIntegerField

from regional_competitions.constants import (REPORT_EXISTS_MESSAGE,
                                             REPORT_SENT_MESSAGE)
from regional_competitions.utils import regional_comp_regulations_files_path


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
    employed_oop = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных ООП'
    )
    employed_smo = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных СМО'
    )
    employed_sservo = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных ССервО'
    )
    employed_sses = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных ССэС'
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


class BaseRegionalR(models.Model):
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='Региональный штаб',
        related_name='%(class)s'
    )
    is_sent = models.BooleanField(
        default=False,
        verbose_name='Отправлен на верификацию'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )

    def clean(self):
        report = self.__class__.objects.filter(regional_headquarter=self.regional_headquarter).last()
        if not self.pk:  # создание нового объекта
            if report and hasattr(report, 'verified_by_chq') and hasattr(report, 'verified_by_dhq'):
                if report.verified_by_chq is False:
                    return
                else:
                    raise ValidationError(REPORT_EXISTS_MESSAGE)
        else:  # редактирование существующего объекта
            if report.is_sent is True:
                raise ValidationError(REPORT_SENT_MESSAGE)

    class Meta:
        abstract = True


class BaseScore(models.Model):
    score = models.FloatField(
        default=0,
        verbose_name='Очки'
    )

    class Meta:
        abstract = True


class BaseVerified(models.Model):
    verified_by_chq = models.BooleanField(
        verbose_name='Верифицирован ЦШ',
        null=True
    )
    verified_by_dhq = models.BooleanField(
        verbose_name='Верифицирован ОШ',
        default=False
    )

    class Meta:
        abstract = True


class BaseComment(models.Model):
    comment = models.TextField(
        verbose_name='Комментарий',
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


class RVerificationLog(models.Model):
    user = models.ForeignKey(
        'users.RSOUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Верифицирующее лицо',
        related_name='r_verification_logs'
    )
    district_headquarter = models.ForeignKey(
        'headquarters.DistrictHeadquarter',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name='Верифицирующий ОШ',
        related_name='r_verification_logs'
    )
    central_headquarter = models.ForeignKey(
        'headquarters.CentralHeadquarter',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name='Верифицирующий ЦШ',
        related_name='r_verification_logs'
    )
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name='Региональный штаб',
        related_name='r_verification_logs'
    )
    is_regional_data = models.BooleanField(default=False, verbose_name='Данные РШ')
    is_district_data = models.BooleanField(default=False, verbose_name='Данные ОШ')
    is_central_data = models.BooleanField(default=False, verbose_name='Данные ЦШ')
    report_number = PositiveSmallIntegerField(verbose_name='Номер показателя')
    report_id = PositiveSmallIntegerField(verbose_name='ID отчета')
    data = models.JSONField(verbose_name='Изменения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата изменений')

    class Meta:
        verbose_name = 'Логи изменений отчета РШ'
        verbose_name_plural = 'Логи изменений отчетов РШ'

    def __str__(self):
        headquarter = self.district_headquarter or self.central_headquarter or self.regional_headquarter
        headquarter_name = headquarter.__class__.__name__ if headquarter else 'No Headquarter'
        return f'Отчет ID: {self.report_id}, данные от: {headquarter_name}, дата: {self.created_at}'

    def clean(self):
        filled_headquarters = [
            hq for hq in [
                self.district_headquarter,
                self.central_headquarter,
                self.regional_headquarter
            ] if hq is not None
        ]

        if len(filled_headquarters) != 1:
            raise ValidationError('Может быть заполнен только один штаб')


class CHqRejectingLog(models.Model):
    user = models.ForeignKey(
        'users.RSOUser',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Отклонившее лицо'
    )
    report_number = PositiveSmallIntegerField(verbose_name='Номер показателя')
    report_id = PositiveSmallIntegerField(verbose_name='Айди показателя')
    reasons = models.JSONField(verbose_name='Причины отклонения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата изменений')

    class Meta:
        verbose_name = 'Причины отклонений ЦШ по отчету'
        verbose_name_plural = 'Причины отклонений ЦШ по отчетам'

    def __str__(self):
        return (
            f'{self.user} отклонил отчет {self.report_id} по показателю {self.report_number}'
        )


class RegionalR4(BaseRegionalR, BaseScore, BaseVerified, BaseComment):
    class Meta:
        verbose_name = 'Отчет по 4 показателю'
        verbose_name_plural = 'Отчеты по 4 показателю'

    def __str__(self):
        return f'Отчет отряда {self.regional_headquarter.name}'


class RegionalR4Event(models.Model):
    regional_r4 = models.ForeignKey(
        'RegionalR4',
        on_delete=models.CASCADE,
        verbose_name='Отчет',
        related_name='events'
    )
    participants_number = models.PositiveIntegerField(
        verbose_name='Количество человек, принявших участие в мероприятии'
    )
    start_date = models.DateField(
        verbose_name='Дата начала проведения мероприятия'
    )
    end_date = models.DateField(
        verbose_name='Дата окончания проведения мероприятия'
    )
    regulations = models.FileField(
        verbose_name='Положение о мероприятии',
        upload_to=regional_comp_regulations_files_path,
        blank=True,
        null=True
    )
    is_interregional = models.BooleanField(
        verbose_name='Межрегиональное',
        default=False
    )

    class Meta:
        verbose_name = 'Мероприятие по 4 показателю'
        verbose_name_plural = 'Мероприятия по 4 показателю'

    def __str__(self):
        return f'ID {self.id}'


class RegionalR4Link(models.Model):
    regional_r4_event = models.ForeignKey(
        'RegionalR4Event',
        on_delete=models.CASCADE,
        verbose_name='Мероприятие',
        related_name='links',
    )
    link = models.URLField(
        verbose_name='Ссылка на группу мероприятия в социальных сетях'
    )


class RegionalR7(BaseRegionalR, BaseScore, BaseVerified, BaseComment):
    class Meta:
        verbose_name = 'Отчет по 7 показателю'
        verbose_name_plural = 'Отчеты по 7 показателю'

    def __str__(self):
        return f'Отчет отряда {self.regional_headquarter.name}'


class RegionalR7Place(models.Model):
    regional_r7 = models.ForeignKey(
        'RegionalR7',
        on_delete=models.CASCADE,
        verbose_name='Отчет',
        related_name='places'
    )
    place = models.PositiveSmallIntegerField(verbose_name='Призовое место')
