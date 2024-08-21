from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import PositiveSmallIntegerField

from regional_competitions.constants import (R6_EVENT_NAMES, R7_EVENT_NAMES, R9_EVENTS_NAMES,
                                             REPORT_EXISTS_MESSAGE,
                                             REPORT_SENT_MESSAGE)
from regional_competitions.factories import RModelFactory

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
        return f'Отчет отряда {self.regional_headquarter.name}'


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
        upload_to=regional_comp_regulations_files_path,
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


class RegionalR1(BaseEventProjectR):
    """
    Численность членов РО РСО в соответствии с объемом уплаченных членских взносов.
    """
    amount_of_money = models.FloatField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Сумма уплаченных членских взносов')
    scan_file = models.FileField(
        upload_to=regional_comp_regulations_files_path,
        blank=True,
        null=True,
        verbose_name='Скан подтверждающего документа'
    )

    class Meta:
        verbose_name = 'Отчет по 1 показателю'
        verbose_name_plural = 'Отчеты по 1 показателю'


class RegionalR4(BaseEventProjectR):
    class Meta:
        verbose_name = 'Отчет по 4 показателю'
        verbose_name_plural = 'Отчеты по 4 показателю'


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
    participants_number = PositiveSmallIntegerField(
        verbose_name='Количество участников',
        default=0,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Мероприятие по 4 показателю'
        verbose_name_plural = 'Мероприятия по 4 показателю'

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
        verbose_name = 'Отчет по 5 показателю'
        verbose_name_plural = 'Отчеты по 5 показателю'


class RegionalR5Event(BaseEventOrProject):
    regional_r5 = models.ForeignKey(
        'RegionalR5',
        on_delete=models.CASCADE,
        verbose_name='Отчет',
        related_name='events'
    )
    participants_number = PositiveSmallIntegerField(
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
        verbose_name = 'Проект  5-го показателя'
        verbose_name_plural = 'Проекты 5-го показателя'

    def __str__(self):
        return f'ID {self.id}'


class RegionalR5Link(BaseLink):
    regional_r5_event = models.ForeignKey(
        'RegionalR5Event',
        on_delete=models.CASCADE,
        verbose_name='Мероприятие',
        related_name='links',
    )


# class BaseRegionalR6(BaseEventProjectR):
#     """
#     Участие бойцов студенческих отрядов РО РСО во всероссийских
#     (международных) мероприятиях и проектах (в том числе и трудовых) «К».
#     """
#     number_of_members = models.PositiveSmallIntegerField(
#         blank=True,
#         null=True,
#         verbose_name='Количество человек принявших участие'
#     )

# r6_models_factory = RModelFactory(
#     r_number=6,
#     base_r_model=BaseRegionalR6,
#     base_link_model=BaseLink,
#     event_names=R6_EVENT_NAMES,
# )
# r6_models_factory.create_models()


class BaseRegionalR7(BaseRegionalR, BaseScore, BaseVerified, BaseComment):
    PRIZE_PLACE_CHOICES = [
        ('1', '1'),
        ('2', '2'),
        ('3', '3'),
        ('Нет', 'Нет'),
    ]

    prize_place = models.CharField(
        max_length=3,
        choices=PRIZE_PLACE_CHOICES,
        default='Нет',
        verbose_name='Призовое место'
    )
    document = models.FileField(
        upload_to=regional_comp_regulations_files_path,
        verbose_name='Скан подтверждающего документа',
        blank=True,
        null=True
    )
    event_date = models.DateField(
        verbose_name='Дата проведения',
        blank=True,
        null=True
    )
    event_location = models.CharField(
        max_length=255,
        verbose_name='Место проведения',
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


r7_models_factory = RModelFactory(
    r_number=7,
    base_r_model=BaseRegionalR7,
    base_link_model=BaseLink,
    event_names=R7_EVENT_NAMES,
)
r7_models_factory.create_models()


class BaseRegionalR9(BaseRegionalR, BaseScore, BaseVerified, BaseComment):
    event_happened = models.BooleanField(
        verbose_name='Проведение акции',
        default=False,
    )
    document = models.FileField(
        upload_to=regional_comp_regulations_files_path,
        verbose_name='Скан документа, подтверждающего проведение мероприятия',
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


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
        upload_to=regional_comp_regulations_files_path,
        verbose_name='Скан документа, подтверждающего проведение акции',
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


class RegionalR101(BaseRegionalR10, BaseRegionalR, BaseScore, BaseVerified, BaseComment):
    class Meta:
        verbose_name = 'Отчет по 10 показателю - "Снежный Десант"'
        verbose_name_plural = 'Отчеты по 10 показателю - "Снежный Десант'


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
        verbose_name = 'Отчет по 10 показателю - "Поклонимся Великим годам"'
        verbose_name_plural = 'Отчеты по 10 показателю - "Поклонимся Великим годам"'


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
        verbose_name = 'Ссылка по 10 показателю - "Поклонимся Великим годам"'
        verbose_name_plural = 'Ссылки по 10 показателю - "Поклонимся Великим годам'

    def __str__(self):
        return f'ID {self.id}'


class RegionalR11(BaseEventProjectR):
    """Активность РО РСО в социальных сетях 'К'"""

    participants_number = models.PositiveIntegerField(
        verbose_name=(
            'Количество человек, входящих в группу '
            'РО РСО в социальной сети "ВКонтакте"'
        ),
        blank=True,
        null=True
    )
    scan_file = models.FileField(
        upload_to=regional_comp_regulations_files_path,
        verbose_name='Скриншот численности группы РО РСО',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Отчет по 11 показателю'
        verbose_name_plural = 'Отчеты по 11 показателю'


class RegionalR12(BaseEventProjectR):
    """
    Объем средств, собранных бойцами РО РСО во Всероссийском дне ударного труда.
    """
    amount_of_money = models.FloatField(
        validators=[MinValueValidator(0)],
        blank=True,
        null=True,
        verbose_name='Объем средств собранных бойцами РО РСО')
    scan_file = models.FileField(
        upload_to=regional_comp_regulations_files_path,
        blank=True,
        null=True,
        verbose_name='Скан подтверждающего документа'
    )

    class Meta:
        verbose_name = 'Отчет по 12 показателю'
        verbose_name_plural = 'Отчеты по 12 показателю'

    def __str__(self):
        return f'Отчет по 12 показателю ID {self.id}'


class RegionalR13(BaseEventProjectR):
    """
    Охват членов РО РСО, принявших участие во Всероссийском дне ударного труда «К».
    """
    number_of_members = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name='Количество членов РО РСО, принявших участие'
    )
    scan_file = models.FileField(
        upload_to=regional_comp_regulations_files_path,
        blank=True,
        null=True,
        verbose_name='Скан подтверждающего документа'
    )

    class Meta:
        verbose_name = 'Отчет по 13 показателю'
        verbose_name_plural = 'Отчеты по 13 показателю'

    def __str__(self):
        return f'Отчет по 13 показателю ID {self.id}'


class RegionalR14(BaseScore):
    """
    Этот показатель считается на основании верифицированных 12 и 13 показателей.
    Заполняется таской.

    Заполняется один раз, без периодического пересчета,
    т.к. нет редактирования верифицированных отчетов.
    """
    report_12 = models.ForeignKey(
        'RegionalR12',
        on_delete=models.CASCADE,
        verbose_name='Отчет 12',
        related_name='report_14'
    )
    report_13 = models.ForeignKey(
        'RegionalR13',
        on_delete=models.CASCADE,
        verbose_name='Отчет 13',
        related_name='report_14'
    )

    class Meta:
        verbose_name = 'Отчет по 14 показателю'
        verbose_name_plural = 'Отчеты по 14 показателю'


class RegionalR16(BaseRegionalR, BaseScore, BaseVerified, BaseComment):
    is_project = models.BooleanField(
        verbose_name='Наличие трудового проекта, в котором ЛО РСО одержал победу',
        default=False
    )

    class Meta:
        verbose_name = 'Отчет по 16 показателю'
        verbose_name_plural = 'Отчеты по 16 показателю'


class RegionalR16Project(models.Model):

    class ProjectScale(models.TextChoices):
        all_russian = 'Всероссийский', 'Всероссийский'
        district = 'Окружной', 'Окружной'
        interregional = 'Межрегиональный', 'Межрегиональный'

    regional_r16 = models.ForeignKey(
        'RegionalR16',
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
        upload_to=regional_comp_regulations_files_path,
        verbose_name='Положение о проекте',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Проект по 16 показателю'
        verbose_name_plural = 'Проекты по 16 показателю'

    def __str__(self):
        return f'ID {self.id}'


class RegionalR16Link(models.Model):
    regional_r16_project = models.ForeignKey(
        'RegionalR16Project',
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
        verbose_name = 'Ссылка по 16 показателю'
        verbose_name_plural = 'Ссылки по 16 показателю'

    def __str__(self):
        return f'ID {self.id}'


class RegionalR17(BaseEventProjectR):
    """Дислокация студенческих отрядов РО РСО"""

    scan_file = models.FileField(
        upload_to=regional_comp_regulations_files_path,
        verbose_name='Документ',
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Отчет по 17 показателю'
        verbose_name_plural = 'Отчеты по 17 показателю'


class RegionalR19(BaseEventProjectR):
    """Трудоустройство"""

    employed_student_start = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name=(
            'Фактическое количество трудоустроенных студентов '
            'в третий трудовой семестр'
        )
    )
    employed_student_end = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name=(
            'Фактическое количество трудоустроенных в штат '
            'принимающей организации по итогам третьего '
            'трудового семестра'
        )
    )

    class Meta:
        verbose_name = 'Отчет по 19 показателю'
        verbose_name_plural = 'Отчеты по 19 показателю'


REPORTS_IS_SENT_MODELS = [
    RegionalR1,
    RegionalR4,
    RegionalR5,
    RegionalR101,
    RegionalR102,
    RegionalR11,
    RegionalR12,
    RegionalR13,
    RegionalR16,
]
# REPORTS_IS_SENT_MODELS.extend(r6_models_factory.models)
REPORTS_IS_SENT_MODELS.extend(
    [model_class for model_name, model_class in r7_models_factory.models.items() if not model_name.endswith('Link')]
)
REPORTS_IS_SENT_MODELS.extend(
    [model_class for model_name, model_class in r9_models_factory.models.items() if not model_name.endswith('Link')]
)
