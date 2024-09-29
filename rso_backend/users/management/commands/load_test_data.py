from django.core.management.base import BaseCommand
from users.models import RSOUser, UserDocuments, UserEducation, UserRegion
from headquarters.models import (
    Area, UserCentralHeadquarterPosition, UserDistrictHeadquarterPosition,
    UserRegionalHeadquarterPosition, UserEducationalHeadquarterPosition,
    UserDetachmentPosition, EducationalInstitution, Position, Detachment, Region
)
from faker import Faker
import random


class Command(BaseCommand):
    help = "Generates test data for RSOUser"

    def handle(self, *args, **kwargs):
        fake = Faker()

        # Получаем или создаем необходимые объекты EducationalInstitution и Position
        educational_institution, _ = EducationalInstitution.objects.get_or_create(
            name=fake.company(),
            short_name=fake.company_suffix(),
            region_id=1  # или используйте подходящее значение региона
        )

        positions = [Position.objects.get_or_create(name=fake.job())[0] for _ in range(5)]

        # Получаем или создаем Region (используйте подходящее имя региона)
        region = Region.objects.filter(id=1).first()
        area = Area.objects.filter(id=1).first()
        commander = RSOUser.objects.filter(id=22).first()
        # Генерация 30 тысяч пользователей
        users = []
        for _ in range(30000):
            user = RSOUser(
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                patronymic_name=fake.first_name(),
                username=fake.unique.user_name(),
                date_of_birth=fake.date_of_birth(),
                phone_number=fake.unique.phone_number(),
                email=fake.unique.email(),
                is_rso_member=random.choice([True, False]),
                is_verified=random.choice([True, False]),
                membership_fee=random.choice([True, False])
            )
            users.append(user)

        # Сохраняем пользователей батчами
        RSOUser.objects.bulk_create(users, batch_size=1000)

        # Генерация связанных данных
        for user in RSOUser.objects.all():
            # Проверяем, существует ли уже UserDocuments для пользователя
            if not UserDocuments.objects.filter(user=user).exists():
                UserDocuments.objects.create(
                    user=user,
                    russian_passport=random.choice([True, False]),
                    pass_ser_num=fake.random_number(digits=6),
                    pass_whom=fake.company(),
                    pass_date=fake.date(),
                    pass_code=fake.random_number(digits=6),
                    inn=fake.random_number(digits=12),
                    snils=fake.random_number(digits=11),
                )

            # Проверяем, существует ли уже UserEducation для пользователя
            if not UserEducation.objects.filter(user=user).exists():
                UserEducation.objects.create(
                    user=user,
                    study_institution=educational_institution,
                    study_faculty=fake.word(),
                    study_specialty=fake.job(),
                    study_year=fake.year(),
                )

            # Проверяем, существует ли уже UserRegion для пользователя
            if not UserRegion.objects.filter(user=user).exists():
                UserRegion.objects.create(
                    user=user,
                    reg_town=fake.city(),
                    reg_house=fake.building_number(),
                    reg_fact_same_address=random.choice([True, False]),
                    fact_town=fake.city(),
                    fact_house=fake.building_number(),
                )

            # Создаем или получаем Detachment
            detachment, _ = Detachment.objects.get_or_create(
                name=fake.company(),
                region=region,
                founding_date=fake.date(),
                area=area,
                commander=commander
            )

            if not UserDetachmentPosition.objects.filter(user=user).exists():
                UserDetachmentPosition.objects.create(
                    user=user,
                    position=random.choice(positions),
                    headquarter=detachment,
                )

        self.stdout.write(self.style.SUCCESS('Successfully generated 30,000 users with related data'))
