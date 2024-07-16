import logging
from datetime import date, timedelta, datetime

from celery import shared_task
from django.conf import settings

from competitions.constants import SOLO_RANKING_MODELS, TANDEM_RANKING_MODELS, COUNT_PLACES_DEADLINE
from competitions.models import (Q1Ranking, Q1Report, Q1TandemRanking,
                                 Q2Ranking, Q2TandemRanking, Q3Ranking,
                                 Q3TandemRanking, Q4Ranking, Q4TandemRanking,
                                 Q5Ranking, Q5TandemRanking, Q6Ranking,
                                 Q6TandemRanking, Q7Ranking, Q7Report,
                                 Q7TandemRanking, Q8Ranking, Q8Report,
                                 Q8TandemRanking, Q9Ranking, Q9Report,
                                 Q9TandemRanking, Q10Ranking, Q10Report,
                                 Q10TandemRanking, Q11Ranking, Q11Report,
                                 Q11TandemRanking, Q12Ranking, Q12Report,
                                 Q12TandemRanking, Q13Ranking,
                                 Q13TandemRanking, Q14Ranking,
                                 Q14TandemRanking, Q15Rank, Q15TandemRank,
                                 Q16Ranking, Q16Report, Q16TandemRanking,
                                 Q17Ranking, Q17TandemRanking, Q18Ranking,
                                 Q18TandemRanking, Q19Ranking,
                                 Q19TandemRanking, Q20Ranking, Q20Report,
                                 Q20TandemRanking)
from competitions.q_calculations import (calculate_overall_rankings,
                                         calculate_place, calculate_q1_score,
                                         calculate_q3_q4_place,
                                         calculate_q5_place,
                                         calculate_q6_place,
                                         calculate_q14_place,
                                         calculate_q15_place,
                                         calculate_q17_place,
                                         calculate_q18_place,
                                         calculate_score_q16)

logger = logging.getLogger('tasks')


@shared_task
def calculate_q1_score_task():
    """Считает очки по 1 показателю."""
    calculate_q1_score(competition_id=settings.COMPETITION_ID)


@shared_task
def calculate_q1_places_task():
    """Считает места по 1 показателю."""
    calculate_place(competition_id=settings.COMPETITION_ID,
                    model_report=Q1Report,
                    model_ranking=Q1Ranking,
                    model_tandem_ranking=Q1TandemRanking)


@shared_task
def calculate_q3_q4_places_task():
    """Считает места по 3-4 показателям."""
    today = date.today()
    cutoff_date = date(2024, 5, 18)

    if today <= cutoff_date + timedelta(days=1):
        calculate_q3_q4_place(competition_id=settings.COMPETITION_ID)
    else:
        logger.warning('Истек срок выполнения подсчета по 3-4 показателям')


@shared_task
def calculate_q5_places_task():
    """Считает места по 5 показателю."""
    today = date.today()

    if today <= COUNT_PLACES_DEADLINE:
        calculate_q5_place(competition_id=settings.COMPETITION_ID)
    else:
        logger.warning('Истек срок выполнения подсчета по 5 показателю')


@shared_task
def calculate_q6_places_task():
    """Считает места по 6 показателю."""
    today = date.today()
    if today <= COUNT_PLACES_DEADLINE:
        calculate_q6_place(competition_id=settings.COMPETITION_ID)
    else:
        logger.warning('Истек срок выполнения подсчета по 5 показателю')


@shared_task
def calculate_q7_places_task():
    """Считает места по 7 показателю."""
    logger.info('Начинаем считать места по 7 показателю')
    calculate_place(competition_id=settings.COMPETITION_ID,
                    model_report=Q7Report,
                    model_ranking=Q7Ranking,
                    model_tandem_ranking=Q7TandemRanking)


@shared_task
def calculate_q8_places_task():
    """Считает места по 8 показателю."""
    calculate_place(competition_id=settings.COMPETITION_ID,
                    model_report=Q8Report,
                    model_ranking=Q8Ranking,
                    model_tandem_ranking=Q8TandemRanking)


@shared_task
def calculate_q9_places_task():
    """Считает места по 9 показателю."""
    calculate_place(competition_id=settings.COMPETITION_ID,
                    model_report=Q9Report,
                    model_ranking=Q9Ranking,
                    model_tandem_ranking=Q9TandemRanking,
                    reverse=False)


@shared_task
def calculate_q10_places_task():
    """Считает места по 10 показателю."""
    calculate_place(competition_id=settings.COMPETITION_ID,
                    model_report=Q10Report,
                    model_ranking=Q10Ranking,
                    model_tandem_ranking=Q10TandemRanking,
                    reverse=False)


@shared_task
def calculate_q11_places_task():
    """Считает места по 11 показателю."""
    calculate_place(competition_id=settings.COMPETITION_ID,
                    model_report=Q11Report,
                    model_ranking=Q11Ranking,
                    model_tandem_ranking=Q11TandemRanking,
                    reverse=False)


@shared_task
def calculate_q12_places_task():
    """Считает места по 12 показателю."""
    calculate_place(competition_id=settings.COMPETITION_ID,
                    model_report=Q12Report,
                    model_ranking=Q12Ranking,
                    model_tandem_ranking=Q12TandemRanking,
                    reverse=False)


@shared_task
def calculate_q14_places_task():
    logger.info('Начинаем считать места по 14 показателю')
    today = date.today()
    if today <= COUNT_PLACES_DEADLINE:
        calculate_q14_place(competition_id=settings.COMPETITION_ID)
        logger.info(
            'Посчитали Q14.'
        )
    else:
        logger.info('Истек срок подсчета 14 показателя')


@shared_task
def calculate_q15_places_task():
    """Считает места по 15 показателю."""
    calculate_q15_place(competition_id=settings.COMPETITION_ID)


@shared_task
def calculate_q16_score_task():
    calculate_score_q16(competition_id=settings.COMPETITION_ID)


@shared_task
def calculate_q16_places_task():
    """Считает места по 16 показателю."""
    calculate_place(competition_id=settings.COMPETITION_ID,
                    model_report=Q16Report,
                    model_ranking=Q16Ranking,
                    model_tandem_ranking=Q16TandemRanking)



@shared_task
def calculate_q17_places_task():
    logger.info('Начинаем считать места по 17 показателю')
    today = date.today()
    if today <= COUNT_PLACES_DEADLINE:
        calculate_q17_place(competition_id=settings.COMPETITION_ID)
    else:
        logger.info('Истек срок подсчета 17 показателя')
    logger.info(
        'Посчитали.'
    )


@shared_task
def calculate_q18_places_task():
    logger.info('Начинаем считать места по 18 показателю')
    today = date.today()
    if today <= COUNT_PLACES_DEADLINE:
        calculate_q18_place(competition_id=settings.COMPETITION_ID)
    else:
        logger.info('Истек срок подсчета 18 показателя')
    logger.info(
        'Посчитали.'
    )


@shared_task
def calculate_q20_places_task():
    """Считает места по 20 показателю."""
    calculate_place(competition_id=settings.COMPETITION_ID,
                    model_report=Q20Report,
                    model_ranking=Q20Ranking,
                    model_tandem_ranking=Q20TandemRanking)


@shared_task
def calculate_overall_places_task():
    """Считает общие места для соло и тандемов."""
    calculate_overall_rankings(
        solo_ranking_models=SOLO_RANKING_MODELS,
        tandem_ranking_models=TANDEM_RANKING_MODELS,
        competition_id=settings.COMPETITION_ID
    )
