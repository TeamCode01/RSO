import logging
from functools import wraps
from io import BytesIO

from django.core.exceptions import FieldDoesNotExist
from django.http import HttpResponse
from drf_yasg.utils import swagger_auto_schema
from django.conf import settings
from django.core.mail import EmailMessage
from openpyxl import Workbook
from reportlab.lib.units import cm
from rest_framework import status
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, HRFlowable
from pdfrw import PdfWriter, PdfReader, PageMerge
import os

from headquarters.models import RegionalHeadquarterEmail, RegionalHeadquarter
# from regional_competitions.r_calculations import calculate_r5_score

from rest_framework import serializers

logger = logging.getLogger('tasks')



def swagger_schema_for_retrieve_method(serializer_cls):
    """Создает декоратор для метода retrieve, генерирующий Swagger схему."""

    def decorator(func):
        @swagger_auto_schema(responses={status.HTTP_200_OK: serializer_cls})
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            return func(self, *args, **kwargs)

        return wrapped

    return decorator


def swagger_schema_for_district_review(serializer_cls):
    def decorator(func):
        @swagger_auto_schema(methods=['PATCH'], request_body=serializer_cls)
        @wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapped

    return decorator


def swagger_schema_for_central_review(serializer_cls):
    def decorator(func):
        @swagger_auto_schema(methods=['PATCH', 'DELETE'], request_body=serializer_cls)
        @wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapped

    return decorator


def swagger_schema_for_create_and_update_methods(serializer_cls):
    def decorator(func):
        @swagger_auto_schema(request_body=serializer_cls)
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            return func(self, *args, **kwargs)

        return wrapped

    return decorator


def get_report_number_by_class_name(link):
    """
    Получает номер отчета для классов с названием,
    соответствующего шаблону `RegionalR<номер_отчета>`.
    """
    if link.__class__.__name__[11].isdigit():
        return link.__class__.__name__[9:12]
    if link.__class__.__name__[10].isdigit():
        return link.__class__.__name__[9:11]
    return link.__class__.__name__[9]


def regional_comp_regulations_files_path(instance, filename) -> str:
    """Функция для формирования пути сохранения файлов конкурса РШ.

    :param instance: Экземпляр модели.
    :param filename: Имя файла. Добавляем к имени текущую дату и время.
    :return: Путь к изображению.
    """
    filename = filename.split('.')
    return (
        f'regional_comp/regulations/{instance.__class__.__name__}/'
        f'{instance.regional_headquarter.id}/{filename[0][:25]}.{filename[1]}'
    )


def get_emails(report_instance) -> list:
    if settings.DEBUG:
        addresses = settings.TEST_EMAIL_ADDRESSES
    else:
        try:
            addresses = [
                RegionalHeadquarterEmail.objects.get(regional_headquarter=report_instance.regional_headquarter).email
            ]
            if report_instance.regional_headquarter.id == 74 and settings.PRODUCTION and not settings.DEBUG:
                addresses.append("rso.71@yandex.ru")
        except RegionalHeadquarterEmail.DoesNotExist:
            logger.warning(
                f'Не найден почтовый адрес в RegionalHeadquarterEmail '
                f'для РШ ID {report_instance.regional_headquarter.id}'
            )
            return []
    return addresses


def send_email_with_attachment(subject: str, message: str, recipients: list, file_path: str):
    mail = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.EMAIL_HOST_USER,
        to=recipients
    )
    with open(file_path, 'rb') as f:
        file_name_start = file_path.find('О')
        mail.attach(file_path.split('/')[-1][file_name_start:], f.read(), 'application/octet-stream')
    mail.send()


def generate_pdf_report_part_1(report):
    pdf_file_name = f"Отчет_ч1_РСО_{report.regional_headquarter}.pdf"
    pdf_file_path = os.path.join(settings.MEDIA_ROOT, pdf_file_name)

    pdfmetrics.registerFont(TTFont(
        'Times_New_Roman',
        os.path.join(
            str(settings.BASE_DIR),
            'templates',
            'samples',
            'fonts',
            'times.ttf'
        )
    ))

    temp_pdf_file_path = os.path.join(settings.MEDIA_ROOT, f"Temp_{pdf_file_name}")
    doc = SimpleDocTemplate(temp_pdf_file_path, pagesize=A4)
    elements = []

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(name='CustomTitle', fontName='Times_New_Roman', fontSize=18, spaceAfter=20,
                              alignment=1, leading=24))
    styles.add(ParagraphStyle(name='Times_New_Roman', fontName='Times_New_Roman', fontSize=12))

    elements.append(Spacer(1, 60))

    elements.append(
        Paragraph("Отчет о деятельности регионального отделения за 2024 год. Часть 1.", styles['CustomTitle'])
    )

    elements.append(Spacer(1, 20))

    data = [["Поле", "Значение"]]

    for field in report._meta.fields:
        if field.name == 'id':
            continue
        field_name = field.verbose_name
        field_value = getattr(report, field.name, '')
        if isinstance(field_value, str):
            field_value = field_value
        elif isinstance(field_value, (int, float)):
            field_value = str(field_value)
        elif field_value is None:
            field_value = ''
        else:
            field_value = str(field_value)

        data.append(
            [Paragraph(field_name, styles['Times_New_Roman']), Paragraph(field_value, styles['Times_New_Roman'])])

    table = Table(data, colWidths=[150, 350], repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6699CC')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Times_New_Roman'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)

    elements.append(PageBreak())

    doc.build(elements)

    template_pdf_path = os.path.join(
        str(settings.BASE_DIR),
        'templates',
        'samples',
        'header_regional_r.pdf'
    )
    template_reader = PdfReader(template_pdf_path)
    content_reader = PdfReader(temp_pdf_file_path)

    writer = PdfWriter()

    for template_page, content_page in zip(template_reader.pages, content_reader.pages):
        PageMerge(template_page).add(content_page, prepend=False).render()

        writer.addpage(template_page)

    writer.write(pdf_file_path)
    os.remove(temp_pdf_file_path)
    return pdf_file_path


def get_verbose_names_and_values(serializer) -> dict:
    """Возвращает словарь с названиями полей и значениями полей из сериализатора."""

    verbose_names_and_values = {}
    model_meta = serializer.Meta.model._meta
    instance = serializer.instance

    for field_name in serializer.Meta.fields:
        field = serializer.fields[field_name]
        field_value = getattr(instance, field_name, None)

        if isinstance(field, serializers.ListSerializer):
            nested_serializer_class = field.child.__class__
            nested_verbose_names_and_values = []

            for nested_instance in field_value.all():
                nested_serializer = nested_serializer_class(nested_instance)
                nested_verbose_names_and_values.append(get_verbose_names_and_values(nested_serializer))

            verbose_names_and_values[field_name] = nested_verbose_names_and_values

        elif isinstance(field, serializers.ModelSerializer):
            nested_serializer = field.__class__(field_value)
            nested_verbose_names_and_values = get_verbose_names_and_values(nested_serializer)

            for nested_field_name, nested_verbose_name_and_value in nested_verbose_names_and_values.items():
                verbose_names_and_values[f"{field_name}.{nested_field_name}"] = nested_verbose_name_and_value

        else:
            try:
                verbose_name = model_meta.get_field(field_name).verbose_name
                if hasattr(field_value, '__str__'):
                    field_value = str(field_value)
                verbose_names_and_values[field_name] = (verbose_name, field_value)
            except FieldDoesNotExist:
                pass
            except AttributeError:
                verbose_names_and_values[field_name] = (field_name, field_value)

    return verbose_names_and_values


def get_headers_values(fields_dict: dict, prefix: str = '') -> dict:
    """Формирует плоский словарь для заголовков и значений листа Excel."""

    # TODO: убрать полный путь для названий файлов
    # TODO: True, False и None заменить на человекочитаемые значения
    flat_dict = {}

    for value in fields_dict.values():
        if isinstance(value, list):
            for item in value:
                nested_prefix = f'{prefix}{item["id"][0]}_{item["id"][1]}.'
                nested_dict = get_headers_values(fields_dict=item, prefix=nested_prefix)
                flat_dict.update(nested_dict)
        elif isinstance(value, tuple):
            flat_dict[f'{prefix}{value[0]}'] = value[1]

    return flat_dict


def get_report_xlsx(self):
    """Выгрузка отчёта в формате Excel."""
    serializer = self.get_serializer(self.get_object())
    flat_data_dict = get_headers_values(
        get_verbose_names_and_values(serializer)
    )
    title = self.get_report_number()
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = title

    worksheet.append(list(flat_data_dict.keys()))
    worksheet.append(list(flat_data_dict.values()))

    file_content = BytesIO()
    workbook.save(file_content)
    file_content.seek(0)
    response = HttpResponse(
        file_content.read(),
        content_type=(
            'application/vnd.openxmlformats-officedocument'
            '.spreadsheetml.sheet'
        )
    )
    response['Content-Disposition'] = (f'attachment; filename={title}.xlsx')
    return response


def generate_pdf_report_part_2(regional_headquarter_id: int) -> str:
    """Генерация общего PDF-файла для отчета по 2-й части."""
    from regional_competitions.serializers import REPORTS_SERIALIZERS
    pdf_file_name = f"Отчет_ч2_РСО_{regional_headquarter_id}.pdf"
    pdf_file_path = os.path.join(settings.MEDIA_ROOT, pdf_file_name)

    pdfmetrics.registerFont(TTFont(
        'Times_New_Roman',
        os.path.join(
            str(settings.BASE_DIR),
            'templates',
            'samples',
            'fonts',
            'times.ttf'
        )
    ))

    temp_pdf_file_path = os.path.join(settings.MEDIA_ROOT, f"Temp_{pdf_file_name}")
    doc = SimpleDocTemplate(temp_pdf_file_path, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=30,
                            bottomMargin=18)
    elements = []

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name='CustomTitle', fontName='Times_New_Roman', fontSize=18, spaceAfter=20, alignment=1, leading=24
        )
    )
    styles.add(
        ParagraphStyle(name='Times_New_Roman', fontName='Times_New_Roman', fontSize=12)
    )
    styles.add(
        ParagraphStyle(name='NestedField', fontName='Times_New_Roman', fontSize=12, leftIndent=20, spaceAfter=10)
    )

    try:
        regional_hq = RegionalHeadquarter.objects.get(id=regional_headquarter_id).name
    except RegionalHeadquarter.DoesNotExist:
        regional_hq = ''

    elements.append(Spacer(1, 90))
    elements.append(
        Paragraph(
            f'Отчет о деятельности регионального отделения за 2024 год. Часть 2. {regional_hq}',
            styles['CustomTitle']
        )
    )
    elements.append(Spacer(1, 15))

    first_block = True

    for serializer_class in REPORTS_SERIALIZERS:
        queryset = serializer_class.Meta.model.objects.filter(regional_headquarter_id=regional_headquarter_id)
        for instance in queryset:
            serializer = serializer_class(instance)
            verbose_names_and_values = get_verbose_names_and_values(serializer)

            if first_block:
                elements.append(
                    HRFlowable(
                        width="100%", thickness=1, color=colors.HexColor('#003366'), spaceBefore=10, spaceAfter=10
                    )
                )
                first_block = False

            elements.append(Paragraph(serializer.Meta.model._meta.verbose_name, styles['CustomTitle']))
            elements.append(Spacer(1, 10))

            add_verbose_names_and_values_to_pdf(verbose_names_and_values, elements, styles)

            elements.append(
                HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366'), spaceBefore=10, spaceAfter=20)
            )

    doc.build(elements)

    template_pdf_path = os.path.join(
        str(settings.BASE_DIR),
        'templates',
        'samples',
        'header_regional_r.pdf'
    )
    template_reader = PdfReader(template_pdf_path)
    content_reader = PdfReader(temp_pdf_file_path)

    writer = PdfWriter()
    for i, content_page in enumerate(content_reader.pages):
        if i == 0:
            template_page = template_reader.pages[0]
            PageMerge(template_page).add(content_page, prepend=False).render()
            writer.addpage(template_page)
        else:
            writer.addpage(content_page)

    writer.write(pdf_file_path)
    os.remove(temp_pdf_file_path)
    return pdf_file_path


def add_verbose_names_and_values_to_pdf(
        verbose_names_and_values: dict,
        elements: list,
        styles,
        indent=0,
        is_nested=False
):
    """Добавляет поля и значения в PDF с таблицами и улучшенным дизайном для вложенных структур."""

    excluded_fields = [
        'id',
        'regional_headquarter',
        'regional_r',
        'verified_by_chq',
        'verified_by_dhq',
        'score',
        'updated_at',
        'file_size',
        'file_type',
        'regional_version',
        'district_version',
        'central_version',
        'rejecting_reasons'
    ]

    primary_color = colors.HexColor('#003366')
    secondary_color = colors.HexColor('#99CCFF')
    background_color = colors.HexColor('#E6F2FF')

    data = []
    nested_structures = []

    nested_title_style = ParagraphStyle(
        'NestedTitle',
        parent=styles['Times_New_Roman'],
        fontSize=14,
        alignment=1,
        textColor=primary_color,
        spaceBefore=20,
        spaceAfter=10
    )

    for field_name, field_value in verbose_names_and_values.items():
        if any(field_name.startswith(excluded_field) for excluded_field in excluded_fields):
            continue

        if isinstance(field_value, list):
            nested_structures.append((field_name, field_value))
            continue

        if isinstance(field_value, tuple) and len(field_value) == 2:
            verbose_name, field_value_content = field_value
        else:
            logger.error(
                f"Неправильное количество значений для распаковки в поле: {field_name}. Значение: {field_value}")
            continue

        if not isinstance(field_value_content, dict):
            data.append([Paragraph(f"<b>{verbose_name}:</b>", styles['Times_New_Roman']),
                         Paragraph(str(field_value_content), styles['Times_New_Roman'])])

    if data:
        table = Table(data, colWidths=[5 * cm, 10 * cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), secondary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('TEXTCOLOR', (0, 1), (-1, -1), primary_color),
            ('FONTNAME', (0, 0), (-1, -1), 'Times_New_Roman'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BACKGROUND', (0, 1), (-1, -1), background_color),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 15))

    for nested_name, nested_items in nested_structures:
        verbose_nested_name = nested_name.replace('_', ' ').capitalize()
        elements.append(Paragraph(verbose_nested_name, nested_title_style))
        elements.append(Spacer(1, 5))

        for item in nested_items:
            if isinstance(item, dict):
                add_verbose_names_and_values_to_pdf(item, elements, styles, indent + 1, is_nested=True)
            elements.append(Spacer(1, 5))
