import logging

from celery import shared_task
from django.conf import settings
from competitions.models import (
    Q10Ranking, Q10Report, Q10TandemRanking, Q11Ranking,
    Q11Report, Q11TandemRanking, Q12Ranking, Q12Report,
    Q12TandemRanking, Q16Ranking, Q16Report, Q16TandemRanking, Q1Ranking,
    Q20Report, Q20TandemRanking, Q7Ranking, Q7Report, Q7TandemRanking,
    Q8Ranking, Q8Report, Q8TandemRanking, Q9Ranking, Q9Report,
    Q9TandemRanking, Q1Report, Q1TandemRanking, Q20Ranking, Q2Ranking, Q3Ranking, Q4Ranking, Q5Ranking, Q6Ranking,
    Q13Ranking, Q14Ranking, Q15Rank, Q17Ranking, Q18Ranking, Q19Ranking, Q2TandemRanking, Q3TandemRanking,
    Q4TandemRanking, Q5TandemRanking, Q6TandemRanking, Q13TandemRanking, Q14TandemRanking, Q15TandemRank,
    Q17TandemRanking, Q18TandemRanking, Q19TandemRanking,
)

from competitions.q_calculations import (
    calculate_q17_place,
    calculate_q18_place,
    calculate_place,
    calculate_q1_score, calculate_q3_q4_place, calculate_q5_place,
    calculate_score_q16, calculate_q15_place, calculate_q14_place, calculate_q6_place, calculate_overall_rankings
)

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
    calculate_q3_q4_place(competition_id=settings.COMPETITION_ID)


@shared_task
def calculate_q5_places_task():
    """Считает места по 3-4 показателям."""
    calculate_q5_place(competition_id=settings.COMPETITION_ID)


@shared_task
def calculate_q6_places_task():
    """Считает места по 6 показателю."""
    calculate_q6_place(competition_id=settings.COMPETITION_ID)


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
    calculate_q14_place(competition_id=settings.COMPETITION_ID)
    logger.info(
        'Посчитали.'
    )


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
    calculate_q17_place(competition_id=settings.COMPETITION_ID)
    logger.info(
        'Посчитали.'
    )


@shared_task
def calculate_q18_places_task():
    logger.info('Начинаем считать места по 18 показателю')
    calculate_q18_place(competition_id=settings.COMPETITION_ID)
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
    solo_ranking_models = [
        Q1Ranking,
        Q2Ranking,
        Q3Ranking,
        Q4Ranking,
        Q5Ranking,
        Q6Ranking,
        Q7Ranking,
        Q8Ranking,
        Q9Ranking,
        Q10Ranking,
        Q11Ranking,
        Q12Ranking,
        Q13Ranking,
        Q14Ranking,
        Q15Rank,
        Q16Ranking,
        Q17Ranking,
        Q18Ranking,
        Q19Ranking,
        Q20Ranking
    ]
    tandem_ranking_models = [
        Q1TandemRanking,
        Q2TandemRanking,
        Q3TandemRanking,
        Q4TandemRanking,
        Q5TandemRanking,
        Q6TandemRanking,
        Q7TandemRanking,
        Q8TandemRanking,
        Q9TandemRanking,
        Q10TandemRanking,
        Q11TandemRanking,
        Q12TandemRanking,
        Q13TandemRanking,
        Q14TandemRanking,
        Q15TandemRank,
        Q16TandemRanking,
        Q17TandemRanking,
        Q18TandemRanking,
        Q19TandemRanking,
        Q20TandemRanking
    ]
    calculate_overall_rankings(
        solo_ranking_models=solo_ranking_models,
        tandem_ranking_models=tandem_ranking_models,
        competition_id=settings.COMPETITION_ID
    )
