import json

from headquarters.models import RegionalHeadquarter
from regional_competitions.models import RVerificationLog, r9_models_factory, r6_models_factory
from regional_competitions.serializers import r9_serializers_factory, r6_serializers_factory


def fix_links_r6_r9():
    with open('templates/samples/rso_reports_6_9_links.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    for report in data:
        try:
            regional_headquarter = RegionalHeadquarter.objects.get(
                id=report['regional_id'],
            )
            print(f'Работаем с РШ {regional_headquarter.name} {regional_headquarter.id}')
        except RegionalHeadquarter.DoesNotExist:
            continue

        reports_6 = report['reports_6']
        for event in reports_6:
            try:
                event_id = event['event_id']
            except KeyError:
                print('EXCEPTION event_id')
                continue
            model_name = f'RegionalR6{event_id}'
            link_model_name = f'RegionalR6{event_id}Link'
            try:
                model = r6_models_factory.models[model_name]
                link_model = r6_models_factory.models[link_model_name]
            except KeyError:
                print('EXCEPTION MODEL_NAME r6')
                continue
            instance = model.objects.filter(
                regional_headquarter=regional_headquarter,
            ).last()
            if not instance:
                continue
            else:
                print(f'Обнаружили для мероприятия R6 {event_id} модели {model_name} и {link_model_name}')
            instance.links.all().delete()
            print('удалили все ссылки для последнего отчета')
            try:
                links = event['links']
            except KeyError:
                print('EXCEPTION LINKS r6')
                continue

            links_to_create = []

            for link in links:
                link_payload = {
                    f'regional_r6{event_id}': instance,
                    'link': link
                }
                links_to_create.append(link_model(**link_payload))

            print(f'создаем ссылки: {links_to_create}')
            link_model.objects.bulk_create(links_to_create)
            print(f'создали ссылки')
            last_log = RVerificationLog.objects.filter(
                regional_headquarter=instance.regional_headquarter,
                is_regional_data=True,
                is_district_data=False,
                is_central_data=False,
                report_id=instance.id,
                report_number=f'6{event_id}',
            ).last()
            print('Ищем последний коммент РШ')
            if last_log:
                print('Нашли последний коммент РШ')
                comment = last_log.data
                print(f'Распарсили: {comment}, type: {type(comment)}')
                instance.comment = comment
            serializer = r6_serializers_factory.serializers[f'{model_name}'](instance)
            report_version_data = serializer.data
            RVerificationLog.objects.create(
                regional_headquarter=instance.regional_headquarter,
                is_regional_data=True,
                is_district_data=False,
                is_central_data=False,
                report_id=instance.id,
                report_number=f'6{event_id}',
                data=report_version_data
            )
            print('Создали версию')

        reports_9 = report['reports_9']
        for event in reports_9:
            try:
                event_id = event['event_id']
            except KeyError:
                continue
            model_name = f'RegionalR9{event_id}'
            link_model_name = f'RegionalR9{event_id}Link'
            try:
                model = r9_models_factory.models[model_name]
                link_model = r9_models_factory.models[link_model_name]
            except KeyError:
                continue
            print(f'Обнаружили для мероприятия R9 {event_id} модели {model_name} и {link_model_name}')
            instance = model.objects.filter(
                regional_headquarter=regional_headquarter,
            ).last()
            if not instance:
                continue
            instance.links.all().delete()
            print('удалили все ссылки для последнего отчета')
            try:
                links = event['links']
            except KeyError:
                continue

            links_to_create = []

            for link in links:
                link_payload = {
                    f'regional_r9{event_id}': instance,
                    'link': link
                }
                links_to_create.append(link_model(**link_payload))

            print(f'создаем ссылки: {links_to_create}')
            link_model.objects.bulk_create(links_to_create)
            print(f'создали ссылки')
            last_log = RVerificationLog.objects.filter(
                regional_headquarter=instance.regional_headquarter,
                is_regional_data=True,
                is_district_data=False,
                is_central_data=False,
                report_id=instance.id,
                report_number=f'9{event_id}',
            ).last()
            print('Ищем последний коммент РШ')
            if last_log:
                print('Нашли последний коммент РШ')
                comment = last_log.data
                print(f'Распарсили: {comment}, type: {type(comment)}')
                instance.comment = comment
            serializer = r9_serializers_factory.serializers[f'{model_name}'](instance)
            report_version_data = serializer.data
            RVerificationLog.objects.create(
                regional_headquarter=instance.regional_headquarter,
                is_regional_data=True,
                is_district_data=False,
                is_central_data=False,
                report_id=instance.id,
                report_number=f'9{event_id}',
                data=report_version_data
            )
            print('Создали версию')
