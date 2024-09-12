import logging
from io import BytesIO

from celery import shared_task
from openpyxl import Workbook
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from urllib.parse import unquote

from reports.utils import (
    get_attributes_of_uniform_data, get_commander_school_data, get_detachment_q_results, get_membership_fee_data,
    get_regions_users_data, get_safety_results,
    get_competition_participants_contact_data,
    get_competition_participants_data,
    get_q5_data, get_q6_data, get_q7_data, get_q8_data, get_q9_data, get_q10_data, get_q11_data, get_q12_data, get_q13_data, get_q14_data,
    get_q15_data, get_q16_data, get_q17_data,get_q18_data, get_q19_data, get_district_hq_data,
    get_regional_hq_data, get_detachment_data, get_educational_hq_data, get_local_hq_data, get_central_hq_data
)


logger = logging.getLogger('tasks')


@shared_task
def generate_excel_file(headers, worksheet_title, filename, data_func, fields=None):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = worksheet_title
    worksheet.append(headers)

    def default_process_row(index, row):
        return [index] + list(row)

    data = None
    match data_func:
        case 'safety_test_results':
            data = get_safety_results()
        case 'detachment_q_results':
            data = get_detachment_q_results(settings.COMPETITION_ID)
        case 'contact_data':
            data = get_competition_participants_contact_data()
        case 'competition_participants':
            data = get_competition_participants_data()
        case 'commander_school':
            data = get_commander_school_data(
                competition_id=settings.COMPETITION_ID)
        case 'regions_users_data':
            data = get_regions_users_data()
        case 'get_q5_data':
            data = get_q5_data(settings.COMPETITION_ID)
        case 'get_q6_data':
            data = get_q6_data(settings.COMPETITION_ID)
        case 'get_q7_data':
            data = get_q7_data(settings.COMPETITION_ID)
        case 'get_q8_data':
            data = get_q8_data(settings.COMPETITION_ID)
        case 'get_q9_data':
            data = get_q9_data(settings.COMPETITION_ID)
        case 'get_q10_data':
            data = get_q10_data(settings.COMPETITION_ID)
        case 'get_q11_data':
            data = get_q11_data(settings.COMPETITION_ID)
        case 'get_q12_data':
            data = get_q12_data(settings.COMPETITION_ID)
        case 'get_q13_data':
            data = get_q13_data(settings.COMPETITION_ID)
        case 'get_q14_data':
            data = get_q14_data(settings.COMPETITION_ID)
        case 'get_q15_data':
            data = get_q15_data(settings.COMPETITION_ID)
        case 'get_q16_data':
            data = get_q16_data(settings.COMPETITION_ID)
        case 'get_q17_data':
            data = get_q17_data(settings.COMPETITION_ID)
        case 'get_q18_data':
            data = get_q18_data(settings.COMPETITION_ID)
        case 'get_q19_data':
            data = get_q19_data(settings.COMPETITION_ID)
        case 'membership_fee':
            data = get_membership_fee_data(
                competition_id=settings.COMPETITION_ID)
        case 'attributes_of_uniform':
            data = get_attributes_of_uniform_data(
                competition_id=settings.COMPETITION_ID)
        case 'get_central_hq_data':
            data = get_central_hq_data(fields)
        case 'get_district_hq_data':
            data = get_district_hq_data(fields)
        case'get_regional_hq_data':
            data = get_regional_hq_data(fields)
        case 'get_educational_hq_data':
            data = get_educational_hq_data(fields)
        case 'get_local_hq_data':
            data = get_local_hq_data(fields)
        case 'get_detachment_data':
            data = get_detachment_data(fields)
        case _:
            logger.error(f"Неизвестное значение data_func: {data_func}")
            return
    if not data:
        logger.warning(
            'Вызов функции не соответствующей кейсу для вызова функции с data')
        return

    for index, row in enumerate(data, start=1):
        processed_row = default_process_row(index, row)
        worksheet.append(processed_row)

    file_content = BytesIO()
    workbook.save(file_content)
    file_content.seek(0)
    decoded_filename = unquote(filename)

    content = ContentFile(file_content.read())
    file_path = default_storage.save(f'to_delete_content/{decoded_filename}', content)

    return file_path


@shared_task
def delete_temp_reports_task():
    for file_name in default_storage.listdir('to_delete_content')[1]:
        default_storage.delete(f'to_delete_content/{file_name}')
