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
    get_competition_participants_data, get_q5_data,
    get_q15_data, get_q16_data, get_q17_data, get_q20_data, get_q18_data
)


logger = logging.getLogger('tasks')


@shared_task
def generate_excel_file(headers, worksheet_title, filename, data_func):
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
        case 'get_q15_data':
            data = get_q15_data(settings.COMPETITION_ID)
        case 'get_q16_data':
            data = get_q16_data(settings.COMPETITION_ID)
        case 'get_q17_data':
            data = get_q17_data(settings.COMPETITION_ID)
        case 'get_q18_data':
            data = get_q18_data(settings.COMPETITION_ID)
        case 'get_q20_data':
            data = get_q20_data(settings.COMPETITION_ID)
        case 'membership_fee':
            data = get_membership_fee_data(
                competition_id=settings.COMPETITION_ID)
        case 'attributes_of_uniform':
            data = get_attributes_of_uniform_data(
                competition_id=settings.COMPETITION_ID)
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
