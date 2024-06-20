from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction

from headquarters.utils import image_path


class EducationalInstitution(models.Model):
    short_name = models.CharField(
        max_length=100,
        verbose_name='Короткое название образовательной '
                     'организации (например, РГГУ)'
    )
    name = models.CharField(
        max_length=300,
        unique=True,
        verbose_name='Полное название образовательной организации',
    )
    rector = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        verbose_name='ФИО ректора образовательной организации'
    )
    rector_email = models.EmailField(
        blank=True,
        null=True,
        verbose_name='Электронная почта ректора'
    )
    region = models.ForeignKey(
        'Region',
        related_name='institutions',
        on_delete=models.PROTECT,
        verbose_name='Регион'
    )

    class Meta:
        verbose_name_plural = 'Образовательные организации'
        verbose_name = 'Образовательная организация'

    def __str__(self):
        return self.name


class Region(models.Model):
    name = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='Название'
    )
    code = models.SmallIntegerField(
        blank=True,
        null=True,
        verbose_name='Код региона'
    )

    class Meta:
        verbose_name_plural = 'Регионы'
        verbose_name = 'Регион'

    def __str__(self):
        return self.name or "unknown region"


class Area(models.Model):
    name = models.CharField(
        max_length=50,
        blank=False,
        verbose_name='Название направления'
    )

    class Meta:
        verbose_name_plural = 'направления'
        verbose_name = 'Направление'

    def __str__(self):
        return self.name


class Unit(models.Model):
    """Базовая модель структурной единицы."""

    name = models.CharField(
        max_length=100,
        verbose_name='Название'
    )
    commander = models.OneToOneField(
        'users.RSOUser',
        on_delete=models.PROTECT,
        verbose_name='Командир',
        related_name="%(class)s_commander"
    )
    about = models.CharField(
        max_length=500,
        verbose_name='Описание',
        null=True,
        blank=True,
    )
    emblem = models.ImageField(
        upload_to=image_path,
        verbose_name='Эмблема',
        blank=True,
        null=True
    )
    social_vk = models.CharField(
        max_length=50,
        verbose_name='Ссылка ВК',
        null=True,
        blank=True,
    )
    social_tg = models.CharField(
        max_length=50,
        verbose_name='Ссылка Телеграм',
        null=True,
        blank=True,
    )
    city = models.CharField(
        max_length=100,
        verbose_name='Город (нас. пункт)',
        blank=True,
        null=True,
    )
    banner = models.ImageField(
        upload_to=image_path,
        blank=True,
        null=True,
        verbose_name='Баннер'
    )
    slogan = models.CharField(
        max_length=250,
        verbose_name='Девиз',
        null=True,
        blank=True,
    )

    def clean(self):
        if not self.commander:
            raise ValidationError('Отряд должен иметь командира.')

    class Meta:
        abstract = True

    def __str__(self):
        return self.name or 'Структурная единица'


class CentralHeadquarter(Unit):
    detachments_appearance_year = models.SmallIntegerField(
        verbose_name='Дата появления студенческих отрядов в России (год)',
        validators=[
            MinValueValidator(settings.MIN_FOUNDING_DATE),
            MaxValueValidator(settings.MAX_FOUNDING_DATE)
        ]
    )
    rso_founding_congress_date = models.DateField(
        verbose_name='Дата первого учредительного съезда РСО'
    )

    class Meta:
        verbose_name_plural = 'Центральные штабы'
        verbose_name = 'Центральный штаб'


class DistrictHeadquarter(Unit):
    central_headquarter = models.ForeignKey(
        'CentralHeadquarter',
        related_name='district_headquarters',
        on_delete=models.PROTECT,
        verbose_name='Привязка к ЦШ',
        blank=True,
        null=True
    )
    founding_date = models.DateField(
        verbose_name='Дата начала функционирования ОШ',
    )

    class Meta:
        verbose_name_plural = 'Окружные штабы'
        verbose_name = 'Окружной штаб'

    def save(self, *args, **kwargs):
        if not self.central_headquarter:
            self.central_headquarter = CentralHeadquarter.objects.first()
        super().save(*args, **kwargs)

    def get_related_units(self) -> dict:
        regional_headquarters = self.regional_headquarters.all()
        educational_headquarters = EducationalHeadquarter.objects.filter(
            regional_headquarter__in=regional_headquarters
        )
        local_headquarters = LocalHeadquarter.objects.filter(
            regional_headquarter__in=regional_headquarters
        )
        detachments = Detachment.objects.filter(
            regional_headquarter__in=regional_headquarters
        )

        return {
            'regional_headquarters': regional_headquarters,
            'educational_headquarters': educational_headquarters,
            'local_headquarters': local_headquarters,
            'detachments': detachments
        }


class RegionalHeadquarter(Unit):
    region = models.ForeignKey(
        'Region',
        related_name='headquarters',
        on_delete=models.PROTECT,
        verbose_name='Регион'
    )
    district_headquarter = models.ForeignKey(
        'DistrictHeadquarter',
        related_name='regional_headquarters',
        on_delete=models.PROTECT,
        verbose_name='Привязка к ОШ'
    )
    name_for_certificates = models.CharField(
        max_length=250,
        verbose_name='Наименование штаба в Им. падеже (для справок)',
        blank=True,
        null=True,
    )
    conference_date = models.DateField(
        verbose_name='Дата учр. конференции регионального штаба',
    )
    registry_date = models.DateField(
        verbose_name='Дата регистрации в реестре молодежных и детских '
                     'общественных объединений...',
        null=True,
        blank=True,
    )
    registry_number = models.CharField(
        max_length=250,
        verbose_name='Регистрационный номер в реестре молодежных и детских '
                     'общественных объединений...',
        null=True,
        blank=True,
    )
    case_name = models.CharField(
        max_length=250,
        verbose_name='Наименование штаба в Предложном падеже (для справок)',
        blank=True,
        null=True,
    )
    legal_address = models.CharField(
        max_length=250,
        verbose_name='Юридический адрес (для справок)',
        blank=True,
        null=True,
    )
    requisites = models.CharField(
        max_length=1000,
        verbose_name='Реквизиты (для справок)',
        blank=True,
        null=True,
    )
    founding_date = models.SmallIntegerField(
        verbose_name='Год основания',
        validators=[
            MinValueValidator(settings.MIN_FOUNDING_DATE),
            MaxValueValidator(settings.MAX_FOUNDING_DATE)
        ]
    )

    class Meta:
        verbose_name_plural = 'Региональные штабы'
        verbose_name = 'Региональный штаб'

    def get_related_units(self) -> dict:
        return {
            'educational_headquarters': self.educational_headquarters.all(),
            'local_headquarters': self.educational_headquarters.all(),
            'detachments': self.detachments.all()
        }


class LocalHeadquarter(Unit):
    regional_headquarter = models.ForeignKey(
        'RegionalHeadquarter',
        related_name='local_headquarters',
        on_delete=models.PROTECT,
        verbose_name='Привязка к РШ'
    )
    founding_date = models.DateField(
        verbose_name='Дата начала функционирования ОШ'
    )

    class Meta:
        verbose_name_plural = 'Местные штабы'
        verbose_name = 'Местный штаб'

    def get_related_units(self) -> dict:
        return {
            'educational_headquarters': self.educational_headquarters.all(),
            'detachments': self.detachments.all()
        }


class EducationalHeadquarter(Unit):
    local_headquarter = models.ForeignKey(
        'LocalHeadquarter',
        related_name='educational_headquarters',
        on_delete=models.PROTECT,
        verbose_name='Привязка к МШ',
        blank=True,
        null=True,
    )
    regional_headquarter = models.ForeignKey(
        'RegionalHeadquarter',
        related_name='educational_headquarters',
        on_delete=models.PROTECT,
        verbose_name='Привязка к РШ',
    )
    educational_institution = models.ForeignKey(
        'EducationalInstitution',
        related_name='headquarters',
        on_delete=models.PROTECT,
        verbose_name='Образовательная организация',
    )
    founding_date = models.DateField(
        verbose_name='Дата основания',
    )

    class Meta:
        verbose_name_plural = 'Образовательные штабы'
        verbose_name = 'Образовательный штаб'

    def get_related_units(self) -> dict:
        return {'detachments': self.detachments.all()}

    def check_headquarters_relations(self) -> None:
        """
        Проверяет, что местный штаб (local_headquarter) связан с тем же
        региональным штабом (regional_headquarter),
        что и образовательный штаб (EducationalHeadquarter).
        """
        if self.local_headquarter and self.regional_headquarter:
            if (
                    self.local_headquarter.regional_headquarter !=
                    self.regional_headquarter
            ):
                raise ValidationError({
                    'local_headquarter': 'Этот местный штаб связан '
                                         'с другим региональным штабом.'
                })

    def save(self, *args, **kwargs):
        self.check_headquarters_relations()
        super().save(*args, **kwargs)


class Detachment(Unit):
    educational_headquarter = models.ForeignKey(
        'EducationalHeadquarter',
        related_name='detachments',
        on_delete=models.PROTECT,
        verbose_name='Привязка к ШОО',
        blank=True,
        null=True,
    )
    local_headquarter = models.ForeignKey(
        'LocalHeadquarter',
        related_name='detachments',
        on_delete=models.PROTECT,
        verbose_name='Привязка к МШ',
        blank=True,
        null=True,
    )
    regional_headquarter = models.ForeignKey(
        'RegionalHeadquarter',
        related_name='detachments',
        on_delete=models.PROTECT,
        verbose_name='Привязка к РШ',
        blank=True,
        null=True,
    )
    region = models.ForeignKey(
        'Region',
        related_name='detachments',
        on_delete=models.PROTECT,
        verbose_name='Привязка к региону'
    )
    educational_institution = models.ForeignKey(
        'EducationalInstitution',
        related_name='detachments',
        on_delete=models.PROTECT,
        verbose_name='Привязка к учебному заведению',
        blank=True,
        null=True,
    )
    area = models.ForeignKey(
        'Area',
        null=False,
        blank=False,
        on_delete=models.PROTECT,
        verbose_name='Направление'
    )
    photo1 = models.ImageField(
        upload_to=image_path,
        blank=True,
        null=True,
        verbose_name='Фото 1'
    )
    photo2 = models.ImageField(
        upload_to=image_path,
        blank=True,
        null=True,
        verbose_name='Фото 2'
    )
    photo3 = models.ImageField(
        upload_to=image_path,
        blank=True,
        null=True,
        verbose_name='Фото 3'
    )
    photo4 = models.ImageField(
        upload_to=image_path,
        blank=True,
        null=True,
        verbose_name='Фото 4'
    )
    founding_date = models.DateField(
        verbose_name='Дата основания',
    )

    class Meta:
        verbose_name_plural = 'Отряды'
        verbose_name = 'Отряд'

    def check_headquarters_relations(self) -> None:
        """
        Проверяет согласованность между
        образовательным штабом (educational_headquarter),
        местным штабом (local_headquarter)
        и региональным штабом (regional_headquarter).
        """
        if (
                not self.regional_headquarter and
                not RegionalHeadquarter.objects.filter(
                    region=self.region
                ).exists()
        ):
            raise ValidationError({
                'region': 'В базе данных не найден РШ '
                          'с данным регионом. '
                          'Обратитесь в тех. поддержку или '
                          'руководство регионального штаба '
                          'Вашего региона.'
            })

        regional_headquarter = (
            self.regional_headquarter if self.regional_headquarter
            else self.region.headquarters.first()
        )

        if self.educational_headquarter and self.local_headquarter:
            if (
                    self.educational_headquarter.local_headquarter !=
                    self.local_headquarter
            ):
                raise ValidationError({
                    'educational_headquarter': 'Выбранный образовательный '
                                               'штаб связан с другим местным '
                                               'штабом.'
                })

        if self.local_headquarter and regional_headquarter:
            if (
                    self.local_headquarter.regional_headquarter !=
                    regional_headquarter
            ):
                raise ValidationError({
                    'local_headquarter': 'Выбранный местный штаб связан с '
                                         'другим региональным штабом.'
                })

        if self.educational_headquarter:
            if (
                    self.educational_headquarter.regional_headquarter !=
                    regional_headquarter
            ):
                raise ValidationError({
                    'educational_headquarter': 'Выбранный образовательный '
                                               'штаб связан с другим '
                                               'региональным  штабом.'
                })
        if self.regional_headquarter:
            if self.region != regional_headquarter.region:
                raise ValidationError({
                    'region': 'Выбранный регион не совпадает с регионом '
                              'выбранного регионального штаба.'
                })
        if self.educational_headquarter and self.educational_institution:
            if (
                    self.educational_headquarter.educational_institution !=
                    self.educational_institution
            ):
                raise ValidationError({
                    'educational_institution': 'Выбранное учебное заведение '
                                               'не совпадает с учебным '
                                               'заведением выбранного '
                                               'образовательного штаба.'
                })

    def handle_headquarter_removals(self, original):
        if self.educational_headquarter is None and original.educational_headquarter is not None:
            UserEducationalHeadquarterPosition.objects.filter(
                headquarter=original.educational_headquarter
            ).delete()

        if self.local_headquarter is None and original.local_headquarter is not None:
            UserLocalHeadquarterPosition.objects.filter(
                headquarter=original.local_headquarter
            ).delete()

    def handle_headquarter_changes(self, original):
        if self.educational_headquarter != original.educational_headquarter:
            if original.educational_headquarter and self.educational_headquarter:
                for user_position in UserEducationalHeadquarterPosition.objects.filter(
                        headquarter=original.educational_headquarter
                ):
                    user_position.headquarter = self.educational_headquarter
                    user_position.save()

        if self.local_headquarter != original.local_headquarter:
            if original.local_headquarter and self.local_headquarter:
                for user_position in UserLocalHeadquarterPosition.objects.filter(
                        headquarter=original.local_headquarter
                ):
                    user_position.headquarter = self.local_headquarter
                    user_position.save()

    def handle_new_headquarters(self, original):
        default_position, _ = Position.objects.get_or_create(
            name=settings.DEFAULT_POSITION_NAME
        )

        if self.educational_headquarter and not original.educational_headquarter:
            self.create_positions_for_users(self.educational_headquarter, UserEducationalHeadquarterPosition,
                                            default_position)

        if self.local_headquarter and not original.local_headquarter:
            self.create_positions_for_users(self.local_headquarter, UserLocalHeadquarterPosition, default_position)

    def create_positions_for_users(self, headquarter, position_class, default_position):
        default_position, created = Position.objects.get_or_create(
            name=settings.DEFAULT_POSITION_NAME
        )
        user_ids = UserDetachmentPosition.objects.filter(headquarter=self).values_list('user_id', flat=True)
        for user_id in user_ids:
            position_class.objects.create(
                user_id=user_id,
                headquarter=headquarter,
                position=default_position,
                is_trusted=False
            )

    def save(self, *args, **kwargs):
        """Автоматически заполняет региональный штаб по региону."""
        self.check_headquarters_relations()
        if not self.regional_headquarter:
            self.regional_headquarter = self.region.headquarters.first()
        if not self.educational_institution and self.educational_headquarter:
            self.educational_institution = (
                self.educational_headquarter.educational_institution
            )

        if self.pk:
            original = Detachment.objects.get(pk=self.pk)

            if original.regional_headquarter != self.regional_headquarter:
                raise ValidationError('Нельзя изменить региональный штаб отряда.')

            with transaction.atomic():
                self.handle_headquarter_removals(original)
                self.handle_headquarter_changes(original)
                self.handle_new_headquarters(original)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Position(models.Model):
    """Хранение наименований должностей для членов отрядов и штабов."""

    name = models.CharField(
        verbose_name='Должность',
        max_length=150,
        unique=True,
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Должности'
        verbose_name = 'Должность'


class UserUnitPosition(models.Model):
    """
    Абстрактная базовая модель для представления пользователя в качестве
    члена тех или иных структурных единиц.

    Эта модель определяет общие атрибуты для хранения информации о
    пользователе, его должности и статусе доверенности в конкретной структурной
    единице.
    """
    user = models.OneToOneField(
        'users.RSOUser',
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name="%(class)s",
        blank=True,
        null=True,
    )
    position = models.ForeignKey(
        'Position',
        on_delete=models.CASCADE,
        verbose_name='Должность',
        null=True,
        blank=True,
    )
    is_trusted = models.BooleanField(default=False, verbose_name='Доверенный')

    skip_central_creation = False

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """
        Родительский метод хранит логику добавления пользователя в качестве
        участника во все структурные единицы, стоящие выше по иерархии того
        отряда, в который он был добавлен.

        Принимает параметры 'headquarter' и 'class_above', переданные в kwargs,
        которые указывают на структурную единицу и связанную модель выше по
        иерархии соответственно.

        Исключения:
        - ValueError: выбрасывается, если в дочернем классе не предоставлены
        необходимые параметры 'headquarter' и 'class_above' при создании
        нового объекта (не вызывается для центрального штаба).
        """
        if self.skip_central_creation:
            if self._state.adding:
                default_position, _ = Position.objects.get_or_create(
                    name=settings.DEFAULT_POSITION_NAME
                )
                headquarter = kwargs.pop('headquarter', None)
                class_above = kwargs.pop('class_above', None)
                if headquarter and class_above:
                    user_id = self.user_id
                    try:
                        instance = class_above.objects.get(
                            user_id=user_id,
                            headquarter=headquarter
                        )
                        if not isinstance(instance, UserCentralHeadquarterPosition):
                            instance_position = instance.position
                            instance.delete()
                        else:
                            instance_position = default_position
                    except class_above.DoesNotExist:
                        instance_position = default_position
                    class_above.objects.create(
                        user_id=user_id,
                        headquarter=headquarter,
                        position=instance_position
                    )
                else:
                    raise ValueError(
                        'headquarter и class_above должны быть переданы '
                        'в качестве kwargs в подклассах'
                    )

        kwargs.pop('headquarter', None)
        kwargs.pop('class_above', None)
        super().save(*args, **kwargs)

    def delete_user_from_all_units(self):
        """
        Удаляет пользователя из всех связанных структурных единиц.
        """
        UserCentralHeadquarterPosition.objects.filter(user=self.user).delete()
        UserDistrictHeadquarterPosition.objects.filter(user=self.user).delete()
        UserRegionalHeadquarterPosition.objects.filter(user=self.user).delete()
        UserLocalHeadquarterPosition.objects.filter(user=self.user).delete()
        UserEducationalHeadquarterPosition.objects.filter(
            user=self.user).delete()
        UserDetachmentPosition.objects.filter(user=self.user).delete()

    def delete(self, *args, **kwargs):
        """
        Переопределяет стандартный метод delete для обеспечения
        удаления пользователя из всех структурных единиц при его удалении
        из одной из структур.
        """
        if isinstance(self, UserDetachmentPosition):
            self.delete_user_from_all_units()
        super().delete(*args, **kwargs)

    def __str__(self):
        position = self.position.name if self.position else 'без должности'
        return (
            f'Пользователь с ником {self.user.username}, ФИО'
            f' {self.user.last_name} '
            f'{self.user.first_name} {self.user.patronymic_name}  - '
            f'{position} '
            f'в "{self.headquarter.name}"'
        )


class UserCentralHeadquarterPosition(UserUnitPosition):
    headquarter = models.ForeignKey(
        'CentralHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='Центральный штаб',
        related_name='members'
    )

    def save(self, *args, **kwargs):
        # if self._state.adding and self.skip_central_creation:
        if self._state.adding:
            return
        super().save(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Члены центрального штаба'
        verbose_name = 'Член центрального штаба'


class UserDistrictHeadquarterPosition(UserUnitPosition):
    headquarter = models.ForeignKey(
        'DistrictHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='Окружной штаб',
        related_name='members'
    )

    class Meta:
        verbose_name_plural = 'Члены окружных штабов'
        verbose_name = 'Член окружного штаба'

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.skip_central_creation = True
            default_position, _ = Position.objects.get_or_create(
                name=settings.DEFAULT_POSITION_NAME
            )
            try:
                instance = UserCentralHeadquarterPosition.objects.get(
                    user_id=self.user_id,
                    headquarter=CentralHeadquarter.objects.first(),
                )
                instance_position = instance.position
                instance.delete()
            except UserCentralHeadquarterPosition.DoesNotExist:
                instance_position = default_position
            central_position = UserCentralHeadquarterPosition.objects.create(
                user_id=self.user_id,
                headquarter=CentralHeadquarter.objects.first(),
                position=instance_position,
            )
            central_position.save_base(force_insert=True)
            kwargs['headquarter'] = self.headquarter.central_headquarter
            kwargs['class_above'] = UserCentralHeadquarterPosition
        super().save(*args, **kwargs)


class UserRegionalHeadquarterPosition(UserUnitPosition):
    headquarter = models.ForeignKey(
        'RegionalHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='Региональный штаб',
        related_name='members'
    )

    class Meta:
        verbose_name_plural = 'Члены региональных штабов'
        verbose_name = 'Член регионального штаба'

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.skip_central_creation = True
            kwargs['headquarter'] = self.headquarter.district_headquarter
            kwargs['class_above'] = UserDistrictHeadquarterPosition
        super().save(*args, **kwargs)


class UserLocalHeadquarterPosition(UserUnitPosition):
    headquarter = models.ForeignKey(
        'LocalHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='Местный штаб',
        related_name='members'
    )

    class Meta:
        verbose_name_plural = 'Члены местных штабов'
        verbose_name = 'Член местного штаба'

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.skip_central_creation = True
            kwargs['headquarter'] = self.headquarter.regional_headquarter
            kwargs['class_above'] = UserRegionalHeadquarterPosition
        super().save(*args, **kwargs)


class UserEducationalHeadquarterPosition(UserUnitPosition):
    headquarter = models.ForeignKey(
        'EducationalHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='Образовательный штаб',
        related_name='members'
    )

    class Meta:
        verbose_name_plural = 'Члены образовательных штабов'
        verbose_name = 'Член образовательного штаба'

    def get_first_filled_headquarter(self):
        """
        Возвращает первый связанный с ШОО заполненный штаб по иерархии:
        МШ или РШ.
        """
        local_headquarter = self.headquarter.local_headquarter
        if local_headquarter:
            return local_headquarter
        return self.headquarter.regional_headquarter

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.skip_central_creation = True
            headquarter = self.get_first_filled_headquarter()
            kwargs['headquarter'] = headquarter
            if isinstance(headquarter, LocalHeadquarter):
                kwargs['class_above'] = UserLocalHeadquarterPosition
            else:
                kwargs['class_above'] = UserRegionalHeadquarterPosition

        super().save(*args, **kwargs)


class UserDetachmentPosition(UserUnitPosition):

    headquarter = models.ForeignKey(
        'Detachment',
        on_delete=models.CASCADE,
        verbose_name='Отряд',
        related_name='members'
    )

    class Meta:
        verbose_name_plural = 'Члены отрядов'
        verbose_name = 'Член отряда'

    def get_first_filled_headquarter(self):
        """
        Возвращает первый связанный с отрядом заполненный штаб по иерархии:
        ШОО, МШ или РШ.
        """

        educational_headquarter = self.headquarter.educational_headquarter
        if educational_headquarter:
            return educational_headquarter
        local_headquarter = self.headquarter.local_headquarter
        if local_headquarter:
            return local_headquarter
        return self.headquarter.regional_headquarter

    def save(self, *args, **kwargs):
        if not self.position:
            default_position, _ = Position.objects.get_or_create(
                name=settings.DEFAULT_POSITION_NAME
            )
            self.position = default_position
        if self._state.adding:
            self.skip_central_creation = True
            headquarter = self.get_first_filled_headquarter()
            kwargs['headquarter'] = headquarter
            if isinstance(headquarter, EducationalHeadquarter):
                kwargs['class_above'] = UserEducationalHeadquarterPosition
            elif isinstance(headquarter, LocalHeadquarter):
                kwargs['class_above'] = UserLocalHeadquarterPosition
            elif isinstance(headquarter, RegionalHeadquarter):
                kwargs['class_above'] = UserRegionalHeadquarterPosition

        super().save(*args, **kwargs)


class UserDetachmentApplication(models.Model):
    """Таблица для подачи заявок на вступление в отряд."""
    user = models.ForeignKey(
        'users.RSOUser',
        on_delete=models.CASCADE,
        verbose_name='Пользователь, подавший заявку на вступление в отряд',
        related_name='applications',
    )
    detachment = models.ForeignKey(
        'Detachment',
        on_delete=models.CASCADE,
        verbose_name='Отряд, в который была подана заявка на вступление',
        related_name='applications',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'detachment'],
                                    name='unique_constraint')
        ]
        verbose_name_plural = 'Заявки на вступление в отряды'
        verbose_name = 'Заявка на вступление в отряд'


class UserEducationalApplication(models.Model):
    """Таблица для подачи заявок на вступление в обр.штаб."""
    user = models.ForeignKey(
        'users.RSOUser',
        on_delete=models.CASCADE,
        verbose_name='Пользователь, подавший заявку на вступление в обр.штаб',
        related_name='edu_applications',
    )
    headquarter = models.ForeignKey(
        'EducationalHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='Обр.штаб, в который была подана заявка на вступление',
        related_name='edu_applications',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'headquarter'],
                                    name='user_eduunique_constraint')
        ]
        verbose_name_plural = 'Заявки на вступление в обр.штабы'
        verbose_name = 'Заявка на вступление в обр.штаб'


class UserLocalApplication(models.Model):
    """Таблица для подачи заявок на вступление в МШ."""

    user = models.ForeignKey(
        'users.RSOUser',
        on_delete=models.CASCADE,
        verbose_name='Пользователь, подавший заявку на вступление в МШ',
        related_name='local_applications',
    )
    headquarter = models.ForeignKey(
        'LocalHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='МШ, в который была подана заявка на вступление',
        related_name='local_applications',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'headquarter'],
                                    name='user_local_unique_constraint')
        ]
        verbose_name_plural = 'Заявки на вступление в МШ'
        verbose_name = 'Заявка на вступление в МШ'


class UserRegionalApplication(models.Model):
    """Таблица для подачи заявок на вступление в РШ."""

    user = models.ForeignKey(
        'users.RSOUser',
        on_delete=models.CASCADE,
        verbose_name='Пользователь, подавший заявку на вступление в РШ',
        related_name='regional_applications',
    )
    headquarter = models.ForeignKey(
        'RegionalHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='РШ, в котором была подана заявка на вступление',
        related_name='regional_applications',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'headquarter'],
                                    name='user_regional_unique_constraint')
        ]
        verbose_name_plural = 'Заявки на вступление в РШ'
        verbose_name = 'Заявка на вступление в РШ'


class UserDistrictApplication(models.Model):
    """Таблица для подачи заявок на вступление в Окружной штаб."""

    user = models.ForeignKey(
        'users.RSOUser',
        on_delete=models.CASCADE,
        verbose_name=(
            'Пользователь, подавший заявку на вступление в Окружной штаб'
        ),
        related_name='district_applications',
    )
    headquarter = models.ForeignKey(
        'DistrictHeadquarter',
        on_delete=models.CASCADE,
        verbose_name=(
            'Окружной штаб, в котором была подана заявка на вступление'
        ),
        related_name='district_applications',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'headquarter'],
                                    name='user_district_unique_constraint')
        ]
        verbose_name_plural = 'Заявки на вступление в Окружной штаб'
        verbose_name = 'Заявка на вступление в Окружной штаб'


class UserCentralApplication(models.Model):
    """Таблица для подачи заявок на вступление в ЦШ."""

    user = models.ForeignKey(
        'users.RSOUser',
        on_delete=models.CASCADE,
        verbose_name='Пользователь, подавший заявку на вступление в ЦШ',
        related_name='central_applications',
    )
    headquarter = models.ForeignKey(
        'CentralHeadquarter',
        on_delete=models.CASCADE,
        verbose_name='ЦШ, в котором была подана заявка на вступление',
        related_name='central_applications',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'headquarter'],
                                    name='user_central_unique_constraint')
        ]
        verbose_name_plural = 'Заявки на вступление в ЦШ'
        verbose_name = 'Заявка на вступление в ЦШ'
