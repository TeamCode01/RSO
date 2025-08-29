from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.constraints import CheckConstraint
from regional_competitions_2025.constants import MEMBER_FEE, R6_DATA, R9_EVENTS_NAMES, REPORT_EXISTS_MESSAGE
from regional_competitions_2025.factories import RModelFactory
from regional_competitions_2025.utils import (
    get_current_year, get_last_rcompetition_id,
    regional_supporting_docs_files_path
)


class RCompetition(models.Model):
    """Список конкурсов региональных штабов"""
    year = models.PositiveSmallIntegerField(
        verbose_name='Год проведения',
        default=get_current_year
    )

    class Meta:
        verbose_name = 'Рейтинг РО'
        verbose_name_plural = 'Рейтинги РО'
        ordering = ['-year']
        constraints = [
            models.UniqueConstraint(fields=['year'], name='unique_year')
        ]

    def __str__(self):
        return f'Рейтинг РО {self.year}'


class DumpStatisticalRegionalReport(models.Model):
    """
    Дамп статистического отчета РШ, 1-я часть отчёта РО.

    Сохраненная версия до редактирования во второй части отчёта.
    """

    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s'
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
    employed_so_poo = models.PositiveIntegerField(
        verbose_name='Количество работников штабов СО ПОО',
        blank=True,
        null=True
    )
    employed_so_oovo = models.PositiveIntegerField(
        verbose_name='Количество работников штабов СО ООВО',
        blank=True,
        null=True
    )
    employed_ro_rso = models.PositiveIntegerField(
        verbose_name='Количество работников штабов РО РСО',
        blank=True,
        null=True
    )
    learned_sso = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные ССО',
        blank=True,
        null=True
    )
    learned_spo = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные СПО',
        blank=True,
        null=True
    )
    learned_sop = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные СОП',
        blank=True,
        null=True
    )
    learned_smo = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные СМО',
        blank=True,
        null=True
    )
    learned_sservo = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные ССервО',
        blank=True,
        null=True
    )
    learned_ssho = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные ССхО',
        blank=True,
        null=True
    )
    learned_specialized_detachments = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные, профильные отряды',
        blank=True,
        null=True
    )
    learned_production_detachments = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные, производственные отряды',
        blank=True,
        null=True
    )
    learned_top = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные, ТОП',
        blank=True,
        null=True
    )
    supporting_documents = models.FileField(
        upload_to=regional_supporting_docs_files_path,
        verbose_name='Документы, подтверждающие факт трудоустройства, по каждому направлению',
        blank=True,
        null=True,
        max_length=255,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )

    class Meta:
        verbose_name_plural = 'Дампы статистических отчетов РШ (1 сентября)'
        verbose_name = 'Дамп статистического отчета РШ (1 сентября)'
        constraints = [
            models.UniqueConstraint(
                fields=['r_competition', 'regional_headquarter'], name='unique_rcompetition_rhq_dump'
            )
        ]

    def __str__(self):
        return f'Дамп статистического отчет отряда {self.regional_headquarter.name}'


class AdditionalStatistic(models.Model):
    statistical_report = models.ForeignKey(
        'StatisticalRegionalReport',
        on_delete=models.CASCADE,
        related_name='additional_statistics',
        verbose_name='Статистический отчет'
    )
    name = models.CharField(verbose_name='Наименование', max_length=255)
    value = models.PositiveIntegerField(verbose_name='Значение')
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )

    class Meta:
        verbose_name_plural = 'Свои варианты - статистические отчеты'
        verbose_name = 'Свои варианты - статистический отчет'

    def __str__(self):
        return f'{self.name}: {self.value}'


class BaseRegionalR(models.Model):
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s'
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

    class Meta:
        abstract = True

    def __str__(self):
        return f'Отчет отряда {self.regional_headquarter.name}'


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


class BaseLink(models.Model):
    link = models.URLField(
        verbose_name='URL-адрес',
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


class BaseEventProjectR(BaseRegionalR, BaseScore, BaseVerified, BaseComment):
    class Meta:
        abstract = True


class BaseEventOrProject(models.Model):
    name = models.TextField(
        verbose_name='Наименование мероприятия',
        blank=True,
        null=True
    )
    start_date = models.DateField(
        verbose_name='Дата начала проведения мероприятия',
        blank=True,
        null=True
    )
    end_date = models.DateField(
        verbose_name='Дата окончания проведения мероприятия',
        blank=True,
        null=True
    )
    regulations = models.FileField(
        verbose_name='Положение о мероприятии',
        upload_to=regional_supporting_docs_files_path,
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


class StatisticalRegionalReport(BaseRegionalR, BaseVerified, BaseComment, BaseScore):
    """Статистический отчет РШ, 1-я часть отчёта РО."""

    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s'
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
    employed_so_poo = models.PositiveIntegerField(
        verbose_name='Количество работников штабов СО ПОО',
        blank=True,
        null=True
    )
    employed_so_oovo = models.PositiveIntegerField(
        verbose_name='Количество работников штабов СО ООВО',
        blank=True,
        null=True
    )
    employed_ro_rso = models.PositiveIntegerField(
        verbose_name='Количество работников штабов РО РСО',
        blank=True,
        null=True
    )
    learned_sso = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные ССО',
        blank=True,
        null=True
    )
    learned_spo = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные СПО',
        blank=True,
        null=True
    )
    learned_sop = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные СОП',
        blank=True,
        null=True
    )
    learned_smo = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные СМО',
        blank=True,
        null=True
    )
    learned_sservo = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные ССервО',
        blank=True,
        null=True
    )
    learned_ssho = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные ССхО',
        blank=True,
        null=True
    )
    learned_specialized_detachments = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные, профильные отряды',
        blank=True,
        null=True
    )
    learned_production_detachments = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные, производственные отряды',
        blank=True,
        null=True
    )
    learned_top = models.PositiveIntegerField(
        verbose_name='Прошедшие обучение ЦШ и трудоустроенные, ТОП',
        blank=True,
        null=True
    )
    supporting_documents = models.FileField(
        upload_to=regional_supporting_docs_files_path,
        verbose_name='Документы, подтверждающие факт трудоустройства, по каждому направлению',
        blank=True,
        null=True,
        max_length=255,
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )

    class Meta:
        verbose_name_plural = 'Статистические отчеты РШ'
        verbose_name = 'Статистический отчет РШ'
        constraints = [
            models.UniqueConstraint(fields=['r_competition', 'regional_headquarter'], name='unique_rcompetition_rhq')
        ]

    def __str__(self):
        return f'Отчет отряда {self.regional_headquarter.name}'



class RVerificationLog(models.Model):
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    user = models.ForeignKey(
        'users.RSOUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Верифицирующее лицо',
        related_name='%(app_label)s_r_verification_logs'
    )
    district_headquarter = models.ForeignKey(
        'headquarters.DistrictHeadquarter',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name='Верифицирующий ОШ',
        related_name='%(app_label)s_r_verification_logs'
    )
    central_headquarter = models.ForeignKey(
        'headquarters.CentralHeadquarter',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name='Верифицирующий ЦШ',
        related_name='%(app_label)s_r_verification_logs'
    )
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_r_verification_logs'
    )
    is_regional_data = models.BooleanField(default=False, verbose_name='Данные РШ')
    is_district_data = models.BooleanField(default=False, verbose_name='Данные ОШ')
    is_central_data = models.BooleanField(default=False, verbose_name='Данные ЦШ')
    report_number = models.BigIntegerField(verbose_name='Номер показателя')
    report_id = models.BigIntegerField(verbose_name='ID отчета')
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
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    user = models.ForeignKey(
        'users.RSOUser',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name='Отклонившее лицо',
        related_name='%(app_label)s_chq_rejecting_logs'
    )
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_r_rejecting_reasons'
    )
    report_number = models.BigIntegerField(verbose_name='Номер показателя')
    report_id = models.BigIntegerField(verbose_name='Айди показателя')
    reasons = models.JSONField(verbose_name='Причины отклонения')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата изменений')

    class Meta:
        verbose_name = 'Причины отклонений ЦШ по отчету'
        verbose_name_plural = 'Причины отклонений ЦШ по отчетам'

    def __str__(self):
        return (
            f'{self.user} отклонил отчет {self.report_id} по показателю {self.report_number}'
        )


class RegionalR1(BaseEventProjectR):
    """
    Численность членов РО РСО.
    """

    amount_of_money = models.FloatField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Сумма уплаченных членских взносов')
    participants_with_payment = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество членов РО РСО с уплаченными членскими взносами',
        help_text='Считается автоматически, если заполнено поле "Сумма уплаченных членских взносов"'
    )
    employed_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество трудоустроенных членов РО РСО'
    )
    foreign_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Численность иностранных граждан'
    )
    foreign_must_pay = models.BooleanField(
        default=False,
        verbose_name='Иностранные граждане освобождены от оплаты членских взносов в данном РО',
        help_text=('Если выбрано, то иностранные граждане не будут учитываться при расчете количества участников'
                   ' с уплаченными членскими взносами')
    )
    top_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Численность участников из ТОП',
        help_text=('Участники из ТОП - это участники из Трудовых Отрядов Подростков')
    )
    top_must_pay = models.BooleanField(
        default=False,
        verbose_name='ТОП освобождены от оплаты членских взносов в данном РО',
        help_text=('Если выбрано, то участники из ТОП не будут учитываться при расчете количества участников'
                   ' с уплаченными членскими взносами')
    )
    scan_file = models.FileField(
        upload_to=regional_supporting_docs_files_path,
        blank=True,
        null=True,
        verbose_name='Скан подтверждающего документа'
    )
    detachment_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество отрядов'
    )
    sso_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество отрядов ССО'
    )
    sso_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество участников ССО'
    )
    spo_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество отрядов СПО'
    )
    spo_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество участников СПО'
    )
    sop_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество отрядов СОП'
    )
    sop_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество участников СОП'
    )
    smo_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество отрядов СМО'
    )
    smo_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество участников СМО'
    )
    sservo_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество отрядов ССервО'
    )
    sservo_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество участников ССервО'
    )
    ssho_number = models.PositiveSmallIntegerField( 
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество отрядов ССхО'
    )
    ssho_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество участников ССхО'
    )
    specialized_detachment_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество профильных отрядов'
    )
    specialized_detachment_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество участников профильных отрядов'
    )
    production_detachment_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество производственных отрядов'
    )
    production_detachment_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество участников производственных отрядов'
    )
    top_detachment_number = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество отрядов ТОП'
    )
    top_detachment_participants = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Количество участников ТОП'
    )

    class Meta:
        verbose_name = '1 показатель, отчет РШ'
        verbose_name_plural = '1 показатель, отчеты РШ'

    def save(self, *args, **kwargs):
        """Автоматически рассчитываем количество участников с уплаченными взносами."""
        if self.amount_of_money is not None:
            self.participants_with_payment = round(self.amount_of_money / MEMBER_FEE, 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Отчет по 1 показателю РШ {self.regional_headquarter}'


class RegionalR2(BaseScore, models.Model):
    """
    Отношение численности членов РО РСО к численности студентов очной формы обучения субъекта Российской Федерации,
    обучающихся в профессиональных образовательных организациях и образовательных организациях высшего образования
    в государственных, муниципальных и частных образовательных организациях, включая филиалы
    (исключения – учебные заведения специальных ведомств, проводящих обучение на казарменном положении).
    """
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )
    full_time_students = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Количество студентов очной формы обучения'
    )

    class Meta:
        verbose_name = '2 показатель, отчет РШ'
        verbose_name_plural = '2 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 2 показателю РШ {self.regional_headquarter}'


class RegionalR3(BaseScore):
    """Отношение количества трудоустроенных членов РО РСО к общей численности членов РО РСО"""
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s'
    )
    employed_members = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных членов РО РСО',
        null=True,
        blank=True
    )
    r3_place = models.PositiveIntegerField(
        verbose_name='Место в рейтинге P3',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = '3 показатель, отчет РШ'
        verbose_name_plural = '3 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 3 показателю РШ — {self.regional_headquarter}'


class RegionalR4(BaseEventProjectR):
    class Meta:
        verbose_name = '4 показатель, отчет РШ'
        verbose_name_plural = '4 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 4 показателю РШ {self.regional_headquarter}'


class RegionalR4Event(BaseEventOrProject):
    regional_r4 = models.ForeignKey(
        'RegionalR4',
        on_delete=models.CASCADE,
        verbose_name='Отчет',
        related_name='events'
    )
    is_interregional = models.BooleanField(
        verbose_name='Межрегиональное',
        default=False
    )
    participants_number = models.PositiveIntegerField(
        verbose_name='Количество участников',
        default=0,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = '4 показатель, мероприятие РШ'
        verbose_name_plural = '4 показатель, мероприятия РШ'

    def __str__(self):
        return f'ID {self.id}'


class RegionalR4Link(BaseLink):
    regional_r4_event = models.ForeignKey(
        'RegionalR4Event',
        on_delete=models.CASCADE,
        verbose_name='Мероприятие',
        related_name='links',
    )


class RegionalR5(BaseEventProjectR):
    """

    Организация всероссийских (международных) (организатор – региональное отделение РСО),
    окружных и межрегиональных трудовых проектов в соответствии с Положением об организации
    трудовых проектов РСО.
    """
    class Meta:
        verbose_name = '5 показатель, отчет РШ'
        verbose_name_plural = '5 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 5 показателю РШ {self.regional_headquarter}'


class RegionalR5Event(BaseEventOrProject):
    regional_r5 = models.ForeignKey(
        'RegionalR5',
        on_delete=models.CASCADE,
        verbose_name='Отчет',
        related_name='events'
    )
    participants_number = models.PositiveIntegerField(
        verbose_name='Общее количество участников',
        default=0,
        blank=True,
        null=True
    )
    ro_participants_number = models.PositiveIntegerField(
        verbose_name=(
            'Количество человек из своего региона, '
            'принявших участие в трудовом проекте'
        ),
        default=0,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = '5 показатель, проект РШ'
        verbose_name_plural = '5 показатель, проекты РШ'

    def __str__(self):
        return f'ID {self.id}'


class RegionalR5Link(BaseLink):
    regional_r5_event = models.ForeignKey(
        'RegionalR5Event',
        on_delete=models.CASCADE,
        verbose_name='Мероприятие',
        related_name='links',
    )


class BaseRegionalR6(BaseEventProjectR):
    """
    Участие бойцов студенческих отрядов РО РСО во всероссийских
    (международных) мероприятиях и проектах (в том числе и трудовых) «К».
    """
    is_project = models.BooleanField(
        verbose_name='Наличие',
        default=False
    )
    number_of_members = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Количество человек принявших участие'
    )
    is_hq_member = models.BooleanField(
        verbose_name='Члены РО являлись членами Штаба всероссийского трудового проекта',
        default=False
    )
    hq_members_count = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Количество членов Штаба всероссийского трудового проекта от РО'
    )

    def __str__(self):
        return f'Отчет по 6 показателю РШ {self.regional_headquarter}'


r6_models_factory = RModelFactory(
    r_number=6,
    base_r_model=BaseRegionalR6,
    base_link_model=BaseLink,
    event_names={id: name for tup in R6_DATA for id, name in tup[0].items()},
)
r6_models_factory.create_models()


class RegionalR7(models.Model):
    """Показатель 7 с данными, предоставленными Центральным штабом"""
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_regional_r7'
    )
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    first_place_events = models.PositiveIntegerField(
        verbose_name='Кол-во 1-ых мест (мероприятия)',
        blank=True,
        null=True
    )
    second_place_events = models.PositiveIntegerField(
        verbose_name='Кол-во 2-ых мест (мероприятия)',
        blank=True,
        null=True
    )
    third_place_events = models.PositiveIntegerField(
        verbose_name='Кол-во 3-их мест (мероприятия)',
        blank=True,
        null=True
    )
    first_place_projects = models.PositiveIntegerField(
        verbose_name='Кол-во 1-ых мест (трудовые проекты)',
        blank=True,
        null=True
    )
    second_place_projects = models.PositiveIntegerField(
        verbose_name='Кол-во 2-ых мест (трудовые проекты)',
        blank=True,
        null=True
    )
    third_place_projects = models.PositiveIntegerField(
        verbose_name='Кол-во 3-их мест (трудовые проекты)',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = '7 показатель, отчет РШ'
        verbose_name_plural = '7 показатель, отчеты РШ'
        ordering = ['regional_headquarter']

    def __str__(self):
        return f'Отчет по 7 показателю РШ {self.regional_headquarter}'


class RegionalR8(BaseScore):
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s'
    )
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )

    class Meta:
        verbose_name = '8 показатель, отчет РШ'
        verbose_name_plural = '8 показатель, отчеты РШ'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['regional_headquarter'],
                name='unique_regional_hq')
        ]

    def save(self, *args, **kwargs):
        ranking_entry, _ = self.regional_headquarter.regional_competitions_rankings.get_or_create(
            regional_headquarter=self.regional_headquarter
        )
        ranking_entry.r8_score = self.score
        ranking_entry.r8_place = self.score
        ranking_entry.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Отчет по 8 показателю РШ {self.regional_headquarter}'


class BaseRegionalR9(BaseRegionalR, BaseScore, BaseVerified, BaseComment):
    event_happened = models.BooleanField(
        verbose_name='Проведение акции',
        default=False,
    )
    document = models.FileField(
        upload_to=regional_supporting_docs_files_path,
        verbose_name='Скан документа, подтверждающего проведение мероприятия',
        blank=True,
        null=True
    )

    class Meta:
        abstract = True

    def __str__(self):
        return f'Отчет по 9 показателю РШ {self.regional_headquarter}'


r9_models_factory = RModelFactory(
    base_r_model=BaseRegionalR9,
    base_link_model=BaseLink,
    r_number=9,
    event_names=R9_EVENTS_NAMES
)
r9_models_factory.create_models()


class BaseRegionalR10(models.Model):
    event_happened = models.BooleanField(
        verbose_name='Проведение акции',
    )
    document = models.FileField(
        upload_to=regional_supporting_docs_files_path,
        verbose_name='Скан документа, подтверждающего проведение акции',
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


class RegionalR101(BaseRegionalR10, BaseRegionalR, BaseScore, BaseVerified, BaseComment):
    class Meta:
        verbose_name = '10 показатель, отчет РШ - "Снежный Десант"'
        verbose_name_plural = '10 показатель, отчеты РШ - "Снежный Десант"'

    def __str__(self):
        return f'Отчет по 10 показателю РШ {self.regional_headquarter}'


class RegionalR101Link(models.Model):
    regional_r101 = models.ForeignKey(
        'RegionalR101',
        on_delete=models.CASCADE,
        verbose_name='Отчет',
        related_name='links'
    )
    link = models.URLField(
        verbose_name='Ссылка на социальные сети/электронные СМИ, подтверждающие проведение акции',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Ссылка по 10 показателю - "Снежный Десант"'
        verbose_name_plural = 'Ссылки по 10 показателю - "Снежный Десант"'

    def __str__(self):
        return f'ID {self.id}'


class RegionalR102(BaseRegionalR10, BaseRegionalR, BaseScore, BaseVerified, BaseComment):
    class Meta:
        verbose_name = '10 показатель, отчет РШ - "Поклонимся великим тем годам"'
        verbose_name_plural = '10 показатель, отчеты РШ - "Поклонимся великим тем годам"'

    def __str__(self):
        return f'Отчет по 10 показателю РШ {self.regional_headquarter}'


class RegionalR102Link(models.Model):
    regional_r102 = models.ForeignKey(
        'RegionalR102',
        on_delete=models.CASCADE,
        verbose_name='Отчет',
        related_name='links'
    )
    link = models.URLField(
        verbose_name='Ссылка на социальные сети/электронные СМИ, подтверждающие проведение акции',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Ссылка по 10 показателю - "Поклонимся великим тем годам"'
        verbose_name_plural = 'Ссылки по 10 показателю - "Поклонимся великим тем годам'

    def __str__(self):
        return f'ID {self.id}'


class RegionalR11(BaseEventProjectR):
    """Активность РО РСО в социальных сетях 'К'"""

    participants_number = models.PositiveIntegerField(
        verbose_name='Количество человек, входящих в группу РО РСО в социальной сети "ВКонтакте"',
        blank=True,
        null=True
    )
    scan_file = models.FileField(
        upload_to=regional_supporting_docs_files_path,
        verbose_name='Скриншот численности группы РО РСО',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = '11 показатель, отчет РШ'
        verbose_name_plural = '11 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 11 показателю РШ {self.regional_headquarter}'


class RegionalR12(BaseEventProjectR):
    """
    Показатель участия во Всероссийском дне ударного труда
    """
    amount_of_money = models.FloatField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Объем средств собранных бойцами РО РСО',
        help_text='Очки в данном показателе это занятое место'
    )
    number_of_members = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Количество членов РО РСО, принявших участие'
    )
    scan_file = models.FileField(
        upload_to=regional_supporting_docs_files_path,
        blank=True,
        null=True,
        verbose_name='Скан подтверждающего документа'
    )

    class Meta:
        verbose_name = '12 показатель, отчет РШ'
        verbose_name_plural = '12 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 12 показателю РШ {self.regional_headquarter}'


class RegionalR13(models.Model):
    """Показатель с данными, предоставленными ЦШ"""
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s',
    )
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    xp = models.PositiveSmallIntegerField(
        verbose_name='Xп'
    )
    yp = models.PositiveSmallIntegerField(
        verbose_name='Yп'
    )
    x3 = models.PositiveSmallIntegerField(
        verbose_name='X3'
    )
    y3 = models.PositiveSmallIntegerField(
        verbose_name='Y3'
    )
    p15 = models.FloatField(
        verbose_name='P15'
    )

    class Meta:
        verbose_name = '13 показатель, отчет РШ'
        verbose_name_plural = '13 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 13 показателю РШ {self.regional_headquarter}'


class RegionalR14(BaseRegionalR, BaseScore, BaseVerified, BaseComment):
    is_project = models.BooleanField(
        verbose_name='Наличие трудового проекта, в котором ЛО РСО одержал победу',
        default=False
    )

    class Meta:
        verbose_name = '14 показатель, отчет РШ'
        verbose_name_plural = '14 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 14 показателю РШ {self.regional_headquarter}'


class RegionalR14Project(models.Model):

    class ProjectScale(models.TextChoices):
        all_russian = 'Всероссийский', 'Всероссийский'
        district = 'Окружной', 'Окружной'
        interregional = 'Межрегиональный', 'Межрегиональный'

    regional_r14 = models.ForeignKey(
        'RegionalR14',
        on_delete=models.CASCADE,
        verbose_name='Отчет',
        related_name='projects'
    )
    name = models.TextField(
        verbose_name='Наименование проекта, в котором ЛСО РО одержал победу',
        blank=True,
        null=True
    )
    project_scale = models.CharField(
        max_length=30,
        choices=ProjectScale.choices,
        verbose_name='Масштаб проекта',
        blank=True,
        null=True
    )
    regulations = models.FileField(
        upload_to=regional_supporting_docs_files_path,
        verbose_name='Положение о проекте',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Проект по 14 показателю'
        verbose_name_plural = 'Проекты по 14 показателю'


class RegionalR14Link(models.Model):
    regional_r14_project = models.ForeignKey(
        'RegionalR14Project',
        on_delete=models.CASCADE,
        verbose_name='Проект',
        related_name='links',
    )
    link = models.URLField(
        verbose_name='Ссылка на группу проекта в социальных сетях',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Ссылка по 14 показателю'
        verbose_name_plural = 'Ссылки по 14 показателю'

    def __str__(self):
        return f'ID {self.id}'


class RegionalR15(models.Model):
    """Отношение количества трудоустроенных и прошедших профобучение членов РО РСО по
       соответствующему основному направлению ЛСО к общей запланированной квоте
       профобучения на текущий период"""
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s',
    )
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    trained_members = models.PositiveIntegerField(
        verbose_name='Количество трудоустроенных и прошедших профобучение членов РО',
        blank=True,
        null=True
    )
    training_quota = models.PositiveIntegerField(
        verbose_name='Общая квота профобучения на 1 сентября 2025',
        blank=True,
        null=True
    )
    score = models.FloatField(
        verbose_name='P15',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = '15 показатель, отчет РШ'
        verbose_name_plural = '15 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 15 показателю РШ {self.regional_headquarter}'


class RegionalR16(BaseComment, models.Model):
    """Дислокация студенческих отрядов РО РСО"""

    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s'
    )
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )
    scan_file = models.FileField(
        upload_to=regional_supporting_docs_files_path,
        verbose_name='Документ',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = '16 показатель, отчет РШ'
        verbose_name_plural = '16 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 16 показателю РШ {self.regional_headquarter}'


class RegionalR17(models.Model):
    """Количество научных работ и публикаций по теме СО, выпущенных в текущем году."""
    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s'
    )
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )
    comment = models.TextField(
        verbose_name='Комментарий',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = '17 показатель, отчет РШ'
        verbose_name_plural = '17 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 17 показателю РШ {self.regional_headquarter}'


class RegionalR17Project(models.Model):
    regional_r17 = models.ForeignKey(
        'RegionalR17',
        on_delete=models.CASCADE,
        verbose_name='Отчет',
        related_name='projects'
    )
    file = models.FileField(
        upload_to=regional_supporting_docs_files_path,
        verbose_name='Файл',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Проект по 17 показателю'
        verbose_name_plural = 'Проекты по 17 показателю'

    def __str__(self):
        return f'ID {self.id}'


class RegionalR17Link(models.Model):
    regional_r17_project = models.ForeignKey(
        'RegionalR17Project',
        on_delete=models.CASCADE,
        verbose_name='Проект',
        related_name='links',
    )
    link = models.URLField(
        verbose_name='Ссылка на публикацию',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Ссылка по 17 показателю'
        verbose_name_plural = 'Ссылки по 17 показателю'

    def __str__(self):
        return f'Ссылка ID {self.id}'


class RegionalR18(BaseComment, models.Model):
    """Трудоустройство."""

    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s'
    )
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )
    employed_student_start = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=(
            'Фактическое количество трудоустроенных студентов '
            'в третий трудовой семестр'
        )
    )
    employed_student_end = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name=(
            'Фактическое количество трудоустроенных в штат '
            'принимающей организации по итогам третьего '
            'трудового семестра'
        )
    )

    class Meta:
        verbose_name = '18 показатель, отчет РШ'
        verbose_name_plural = '18 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 18 показателю РШ {self.regional_headquarter}'


class RegionalR19Employee(models.Model):
    regional_r19 = models.ForeignKey(
        'RegionalR19',
        on_delete=models.CASCADE,
        verbose_name='Отчет',
        related_name='employees'
    )
    job_title = models.CharField(
        max_length=255,
        verbose_name='Должность',
        blank=True,
        null=True
    )
    salary = models.PositiveIntegerField(
        verbose_name='Заработная плата',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Зарплата сотрудника РО РСО'
        verbose_name_plural = 'Зарплаты сотрудников РО РСО'

    def __str__(self):
        return f'Зарплата сотрудника {self.job_title} в РО РСО {self.regional_r19.regional_headquarter}'


class RegionalR19(BaseComment, models.Model):
    """Количество и трудоустройство сотрудников РО РСО."""

    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s'
    )
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )
    employees_number = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name='Фактическое количество сотрудников РО РСО'
    )
    officially_employed_number = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name='Количество сотрудников, официально трудоустроенных в РО РСО'
    )
    officially_employed = models.BooleanField(
        verbose_name='Официальное трудоустройство сотрудников в РО РСО',
        default=False,
        help_text='Селект больше не используется.',
        blank=True,
        null=True
    )
    average_salary = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Средняя заработная плата сотрудников РО РСО, руб.'
    )

    class Meta:
        verbose_name = '19 показатель, отчет РШ'
        verbose_name_plural = '19 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 19 показателю РШ {self.regional_headquarter}'


class RegionalR20(BaseComment, models.Model):
    """Количество и трудоустройство сотрудников РО РСО."""

    regional_headquarter = models.ForeignKey(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_%(class)s'
    )
    r_competition = models.ForeignKey(
        RCompetition,
        verbose_name='Рейтинг РО',
        on_delete=models.CASCADE,
        default=get_last_rcompetition_id,
        related_name='%(app_label)s_%(class)s'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )
    premises_available = models.BooleanField(
        verbose_name='Наличие помещения',
        default=False,
        help_text='Выбрано - есть, пусто - нет',
        blank=True,
        null=True
    )
    equipped_workplaces = models.BooleanField(
        verbose_name='Наличие оборудованных рабочих мест',
        default=False,
        help_text='Выбрано - есть, пусто - нет',
        blank=True,
        null=True
    )
    event_spaces = models.BooleanField(
        verbose_name='Наличие доступа к помещениям для совместной работы и проведения мероприятий различного уровня',
        default=False,
        help_text='Выбрано - есть, пусто - нет',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = '20 показатель, отчет РШ'
        verbose_name_plural = '20 показатель, отчеты РШ'

    def __str__(self):
        return f'Отчет по 20 показателю РШ {self.regional_headquarter}'


REPORTS_IS_SENT_MODELS = [
    StatisticalRegionalReport,
    RegionalR1,
    RegionalR4,
    RegionalR5,
    RegionalR101,
    RegionalR102,
    RegionalR11,
    RegionalR12,
    RegionalR13,
]
# REPORTS_IS_SENT_MODELS.extend(
#     [model_class for model_name, model_class in r6_models_factory.models.items() if not model_name.endswith('Link')]
# )
REPORTS_IS_SENT_MODELS.extend(
    [model_class for model_name, model_class in r9_models_factory.models.items() if not model_name.endswith('Link')]
)


class ExpertRole(models.Model):
    """Роль эксперта."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='%(app_label)s_regional_expert',
    )
    central_headquarter = models.ForeignKey(
        'headquarters.CentralHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Центральный штаб',
        related_name='%(app_label)s_regional_experts',
        blank=True,
        null=True
    )
    district_headquarter = models.ForeignKey(
        'headquarters.DistrictHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Окружной штаб',
        related_name='%(app_label)s_regional_experts',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата последнего обновления'
    )

    class Meta:
        verbose_name = 'Роль эксперта'
        verbose_name_plural = 'Роли экспертов'
        constraints = [
            CheckConstraint(
                check=Q(central_headquarter__isnull=False) | Q(district_headquarter__isnull=False),
                name='only_one_headquarter'
            ),
            CheckConstraint(
                check=~Q(central_headquarter__isnull=False, district_headquarter__isnull=False),
                name='not_central_and_district_headquarters'
            )
        ]


class Ranking(models.Model):
    """Места участников по показателям."""

    regional_headquarter = models.OneToOneField(
        'headquarters.RegionalHeadquarter',
        on_delete=models.PROTECT,
        verbose_name='Региональный штаб',
        related_name='%(app_label)s_regional_competitions_rankings'
    )
    overall_place = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Лучшее региональное отделение по итогам года'
    )
    k_place = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Лучшее региональное отделение по комиссарской деятельности'
    )
    sum_overall_place = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Сумма мест по итогам года'
    )
    sum_k_place = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Сумма мест по комиссарской деятельности'
    )

    @classmethod
    def add_fields(cls):
        for i in range(1, 17):
            field = models.PositiveSmallIntegerField(
                verbose_name=f'Место участника по {i} показателю',
                blank=True,
                null=True
            )
            field_score = models.FloatField(
                verbose_name=f'Очки участника по {i} показателю',
                blank=True,
                null=True
            )
            cls.add_to_class(f'r{i}_place', field)
            cls.add_to_class(f'r{i}_score', field_score)

    class Meta:
        verbose_name = 'Место участника по показателю'
        verbose_name_plural = 'Места участников по показателям'


Ranking.add_fields()
