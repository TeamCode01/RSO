from io import BytesIO

from celery import shared_task
from openpyxl import Workbook
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from urllib.parse import quote, unquote


@shared_task
def generate_excel_file(data, headers, worksheet_title, filename, process_row_type):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = worksheet_title
    worksheet.append(headers)

    def default_process_row(index, row):
        return [index] + list(row)

    def safety_test_results_process_row(index, row):
        return [
            index,
            row['region_name'] if row['region_name'] else '-',
            f'{row["last_name"]} {row["first_name"]} '
            f'{row["patronymic_name"] if row["patronymic_name"] else "(без отчества)"}',
            row['detachment'] if row['detachment'] else '-',
            row['detachment_position'] if row['detachment_position'] else '-',
            row['attempt_number'],
            "Да" if row['is_valid'] else "Нет",
            row['score'],
        ]

    def detachment_q_results_process_row(index, row):
        return [
            index,
            row['region_name'],
            row['name'],
            row['status'],
            row['nomination'],
            row['participants_count'],
            row['overall_ranking'],
            row['places_sum'],
            *row['places']
        ]

    process_row = default_process_row
    if process_row_type == 'safety_test_results':
        process_row = safety_test_results_process_row
    elif process_row_type == 'detachment_q_results':
        process_row = detachment_q_results_process_row

    for index, row in enumerate(data, start=1):
        processed_row = process_row(index, row)
        worksheet.append(processed_row)

    file_content = BytesIO()
    workbook.save(file_content)
    file_content.seek(0)

    decoded_filename = unquote(filename)

    content = ContentFile(file_content.read())
    file_path = default_storage.save(decoded_filename, content)

    return file_path
