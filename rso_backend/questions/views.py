from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from datetime import datetime
from django.db import transaction
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from questions.models import Question, Attempt, UserAnswer, AnswerOption
from questions.serializers import QuestionSerializer
import random

from questions.swagger_schemas import answers_request_body


class QuestionsView(APIView):
    """
    Предоставляет вопросы пользователям на основе заданной категории
    через параметры запроса.

    ## Эндпоинт поддерживает следующие параметры запроса:
    - `category` (строка): указывает на категорию вопросов, которые необходимо
    получить.
      Допустимые значения: 'university' и 'safety'.

    ## Ограничения по датам:
    - Вопросы из первого блока ('university') доступны до 10 апреля 2024 года
    включительно.
    - Вопросы из категории 'safety' доступны до 15 июня 2024 года включительно.


    ## Правила:
    - Пользователь должен быть аутентифицирован.
    - Для каждой категории пользователь может совершить не более 3 попыток
     получения вопросов.
    - Вопросы в категории 'university' подбираются из смешанных блоков в
    следующем порядке:
        - 6 вопросов из блока 1,
        - 8 вопросов из блока 2,
        - 5 вопросов из блока 3,
        - 1 вопрос из блока 4.
      Вопросы перемешиваются перед возвратом.
    - Вопросы в категории 'safety' выбираются случайным образом из блока 5
    (всего 15 вопросов).

    ## Ответы:
    При успешном выполнении запроса возвращается список вопросов в формате JSON,
    соответствующих указанной категории. Каждый вопрос включает в себя название,
    изображение (если есть) и варианты ответов.

    В случае ошибки (например, превышения количества попыток или
    неверной категории)
    возвращается сообщение об ошибке и соответствующий HTTP статус.
    """

    permission_classes = (permissions.IsAuthenticated,)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name='category',
                in_=openapi.IN_QUERY,
                description="Категория вопросов ('university' или 'safety')",
                type=openapi.TYPE_STRING,
            ),
        ],
        responses={
            200: QuestionSerializer(many=True),
            400: 'Превышено макс. число попыток (3) или иные ошибки запроса'
        },
    )
    def get(self, request, format=None):
        user = request.user
        category = request.query_params.get('category', None)

        current_date = datetime.now().date()
        university_deadline = datetime(2024, 4, 10).date()
        safety_deadline = datetime(2024, 6, 15).date()

        attempts_count = Attempt.objects.filter(
            user=user, category=category, is_valid=True
        ).count()

        if attempts_count > 2 and category == 'university':
            return Response(
                {"error": "Превышено макс. число попыток (3)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if attempts_count > 1 and category == 'safety':
            return Response(
                {"error": "Превышено макс. число попыток (2)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if category == 'university':
            if current_date > university_deadline and user.region.code != 90:
                return Response(
                    {"error": "Срок получения вопросов по "
                              "категории 'university' истек."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            questions = self.get_university_questions_mix()
        elif category == 'safety':
            if current_date > safety_deadline:
                return Response(
                    {"error": "Срок получения вопросов по "
                              "категории 'safety' истек."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            questions = self.get_block_questions(5, 15)
        else:
            return Response(
                {
                    "error": "Неверная категория. "
                             "Выберите university или safety."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        attempt = Attempt.objects.create(user=user, category=category)
        attempt.questions.set(questions)
        attempt.save()

        serializer = QuestionSerializer(questions, many=True, context={'request': request})
        return Response(serializer.data)

    def get_university_questions_mix(self):
        questions_mix = []
        questions_mix.extend(self.get_block_questions(1, 6))
        questions_mix.extend(self.get_block_questions(2, 8))
        questions_mix.extend(self.get_block_questions(3, 5))
        questions_mix.extend(self.get_block_questions(4, 1))
        random.shuffle(questions_mix)
        return questions_mix

    def get_block_questions(self, block_number, count):
        questions = Question.objects.filter(block=block_number).order_by('?')[
                    :count]
        return list(questions)


@swagger_auto_schema(
    method='post',
    request_body=answers_request_body,
    responses={
        200: openapi.Response(
            description="Ответы успешно отправлены. Получено баллов: X"
        ),
        400: openapi.Response(
            description="Ошибка в запросе"
        ),
    },
    security=[],
    operation_id="submit_answers",
)
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def submit_answers(request):
    """
    Функция проверяет принадлежность вопросов к последней попытке, регистрирует
    ответы пользователя и вычисляет итоговый счет на основе
    правильности ответов.

    Принимаемые данные:
    Функция принимает POST-запрос с JSON телом, содержащим список ответов
    пользователя ("answers"). Также в ключе "category" указывается категория.

     Каждый ответ представлен словарем с двумя ключами:

    question_id - идентификатор вопроса (целое число),
    answer_option_id - идентификатор выбранного варианта ответа (целое число).
    Формат тела запроса:
    ```
    {
      "answers": [
            {
              "question_id": 1,
              "answer_option_id": 3
            },
            {
              "question_id": 2,
              "answer_option_id": 5
            },
            ...
        ],
      "category": "university"
    }
    ```
    Ответ функции:
    Функция возвращает JSON объект с сообщением о результате операции.
    В случае успешного приема и обработки ответов, возвращается
    общее количество набранных баллов.

    При успешной обработке ответов:
    ```
    {
        "score": X
    }
    ```
    Где X - итоговое количество набранных баллов (целое число).

    При возникновении ошибки (например, если вопросы не принадлежат
    последней попытке или попытка не найдена):
    ```
    {
        "error": "Текст ошибки"
    }
    ```

    Сообщение об ошибке будет соответствовать причине отказа.

    Ограничения и проверки:
    - Пользователь должен быть аутентифицирован.
    - Должна существовать активная попытка пользователя.
    - Для каждой попытки допускается отправка ответов только один раз.
    Все вопросы в отправленных ответах должны соответствовать вопросам
    последней активной попытки пользователя.

    Баллы:
    - За каждый правильный ответ начисляется фиксированное количество баллов.
    - Количество баллов за правильный ответ может варьироваться в зависимости от
    категории попытки (указывается в параметре scores_per_answer).

    HTTP Статусы ответа:
    - 200 OK - запрос успешно обработан,
    - 400 Bad Request - в запросе обнаружена ошибка (например, не все
    вопросы принадлежат последней попытке или ответы уже были отправлены).
    """
    user = request.user
    answers_data = request.data.get('answers', [])
    category = request.data.get('category', None)

    if category not in ('safety', 'university'):
        return Response(
            {
                "error": "Неверная категория. "
                         "Выберите university или safety."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Получаем последнюю попытку
    latest_attempt = Attempt.objects.filter(
        user=user, category=category
    ).order_by('-timestamp').first()
    if not latest_attempt:
        return Response(
            {'error': 'Сначала нужны получить вопросы.'}, status=400
        )

    with transaction.atomic():
        # Проверяем, есть ли уже ответы для этой попытки
        if UserAnswer.objects.filter(attempt=latest_attempt).exists():
            return Response(
                {'error': 'Ответы по попытке уже были приняты.'},
                status=400
            )

        score = 0
        scores_per_answer = 6.66 if latest_attempt.category == 'safety' else 5

        for answer in answers_data:
            question_id = answer.get('question_id')
            answer_option_id = answer.get('answer_option_id')

            # Проверяем, принадлежит ли вопрос к последней попытке
            if not latest_attempt.questions.filter(id=question_id).exists():
                return Response(
                    {'error': 'Вопрос не относится к последней попытке.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                question = Question.objects.get(id=question_id)
                answer_option = question.answer_options.get(id=answer_option_id)
            except (Question.DoesNotExist, AnswerOption.DoesNotExist):
                return Response(
                    {
                        'error': f'Неверная пара id вопрос-ответ: '
                                 f'question_id: {question_id}, answer_id: {answer_option_id}.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            UserAnswer.objects.create(
                attempt=latest_attempt,
                question=question,
                answer_option=answer_option
            )
            if answer_option.is_correct:
                score += scores_per_answer

    latest_attempt.score = round(score)
    latest_attempt.is_valid = True
    latest_attempt.save()

    best_score = Attempt.objects.filter(
        user=user, category=category, is_valid=True
    ).order_by('-score').first().score

    return Response(
        {
            'score': round(score),
            'best_score': best_score
        },
        status=status.HTTP_200_OK
    )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_attempts_status(request):
    """
    Получает статус попыток пользователя по конкретной категории тестирования.

    Эндпоинт принимает GET-запрос и ожидает параметр 'category' в query параметрах запроса.
    Category может быть либо 'university' и 'safety'. Функция возвращает JSON-ответ,
    содержащий информацию о статусе попыток пользователя в указанной категории.

    1. Проверяет, что пользователь аутентифицирован.
    2. Валидирует значение 'category' из query параметров запроса.
    3. Считает количество попыток пользователя в данной категории.
    4. Если количество попыток меньше 3, возвращает сообщение о количестве оставшихся попыток.
    5. Если попытки исчерпаны, определяет лучший результат среди всех попыток и возвращает его.

    Ответы:
    - HTTP 400 для неверно указанной категории с соответствующим сообщением.
    - HTTP 200 с сообщением о недостатке попыток, если их менее трех.
    - HTTP 200 с лучшим результатом, если попытки были сделаны.
    """
    user = request.user
    category = request.query_params.get('category', None)
    if category not in ('safety', 'university'):
        return Response(
            {
                "error": "Неверная категория. "
                         "Выберите university или safety."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    attempts_count = Attempt.objects.filter(
        user=user, category=category, is_valid=True
    ).count()
    best_attempt = Attempt.objects.filter(
        user=user, category=category, is_valid=True
    ).order_by('-score').first()
    if best_attempt:
        best_score = best_attempt.score
    else:
        best_score = 0
    if attempts_count < 3:
        return Response(
            {
                "left_attempts": 3-attempts_count,
                'best_score': best_score
            },
            status=status.HTTP_200_OK
        )

    return Response(
        {
            'best_score': best_score
        },
        status=status.HTTP_200_OK
    )
