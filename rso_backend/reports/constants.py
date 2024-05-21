
# Spread shit data
OPENXML_CONTENT_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

# SQL Queries
COMPETITION_PARTICIPANTS_CONTACT_DATA_QUERY = (
    """
    WITH ranked_positions AS (
        SELECT
            d.id AS ID_Отряда, d.name AS Название_Отряда,
            hr.name AS Регион,
            ar.name AS Направление,
            ur.last_name AS Командир_Фамилия, ur.first_name AS Командир_Имя, ur.patronymic_name AS Командир_Отчество,
            ur.is_verified AS Командир_Верифицирован, ur.membership_fee AS Командир_Взнос, ur.email AS Командир_email, ur.phone_number AS Командир_Номер_Телефона,
            ur2.last_name AS Комиссар_Фамилия, ur2.first_name AS Комиссар_Имя, ur2.patronymic_name AS Комиссар_Отчество, ur2.membership_fee AS Комиссар_Взнос,
            ur2.is_verified AS Комиссар_Верифицирован, ur2.email AS Комиссар_Email, ur2.phone_number AS Комиссар_Номер_Телефона,
            hp.name AS Должность,
            ROW_NUMBER() OVER(PARTITION BY d.id ORDER BY CASE WHEN hp.name = 'Комиссар' THEN 0 ELSE 1 END) AS rn,
            CASE
                WHEN d.id IN (SELECT junior_detachment_id FROM competitions_competitionparticipants WHERE junior_detachment_id IS NOT NULL)
                AND d.id IN (SELECT detachment_id FROM competitions_competitionparticipants WHERE detachment_id IS NOT NULL)
                THEN 'Тандем'
                WHEN d.id IN (SELECT junior_detachment_id FROM competitions_competitionparticipants WHERE junior_detachment_id IS NOT NULL)
                THEN 'Отряд Старт'
                WHEN d.id IN (SELECT detachment_id FROM competitions_competitionparticipants WHERE detachment_id IS NOT NULL)
                THEN 'Отряд Наставник'
                ELSE 'Не участвует'
            END AS Статус_Отряда,
            CASE
                WHEN d.id IN (
                    SELECT junior_detachment_id
                    FROM competitions_competitionparticipants
                    WHERE junior_detachment_id IS NOT NULL AND detachment_id IS NOT NULL
                ) OR d.id IN (
                    SELECT detachment_id
                    FROM competitions_competitionparticipants
                    WHERE junior_detachment_id IS NOT NULL AND detachment_id IS NOT NULL
                )
                THEN 'Тандем'
                ELSE 'Старт'
            END AS Номинация
        FROM headquarters_detachment d
        JOIN headquarters_area ar ON d.area_id = ar.id
        JOIN headquarters_region hr ON d.region_id = hr.id
        JOIN users_rsouser ur ON d.commander_id = ur.id
        LEFT JOIN headquarters_userdetachmentposition udp ON d.id = udp.headquarter_id
        LEFT JOIN users_rsouser ur2 ON udp.user_id = ur2.id
        LEFT JOIN headquarters_position hp ON udp.position_id = hp.id
        WHERE d.id IN (
            SELECT junior_detachment_id
            FROM competitions_competitionparticipants
            WHERE junior_detachment_id IS NOT NULL
            UNION
            SELECT detachment_id
            FROM competitions_competitionparticipants
            WHERE detachment_id IS NOT NULL
        )
    )
    SELECT
        ID_Отряда, Название_Отряда, Направление, Регион, Командир_Фамилия, Командир_Имя, Командир_Отчество, Командир_Email, Командир_Номер_Телефона,
        Командир_Верифицирован, Командир_Взнос, Комиссар_Фамилия, Комиссар_Имя, Комиссар_Отчество, Комиссар_Email, Комиссар_Номер_Телефона,
        Должность, Статус_Отряда, Номинация
    FROM ranked_positions
    WHERE rn = 1
    ORDER BY ID_Отряда;
    """
)

# Headers
COMPETITION_PARTICIPANTS_CONTACT_DATA_HEADERS = [
    '№',
    'ID Отряда',
    'Название Отряда',
    'Направление',
    'Регион',
    'Командир Фамилия',
    'Командир Имя',
    'Командир Отчество',
    'Командир Email',
    'Командир Номер Телефона',
    'Командир Верифицирован',
    'Командир Взнос',
    'Комиссар Фамилия',
    'Комиссар Имя',
    'Комиссар Отчество',
    'Комиссар Email',
    'Комиссар Номер Телефона',
    'Должность',
    'Статус Отряда',
    'Номинация'
]
SAFETY_TEST_RESULTS_HEADERS = [
    '№',
    'Регион',
    'Фамилия',
    'Имя',
    'Отчество'
    'Отряд',
    'Должность',
    'Попытка',
    'Валидность попытки',
    'Очки',
    'Дата'
]
DETACHMENT_Q_RESULTS_HEADERS = [
    '№',
    'Регион',
    'Отряд',
    'Статус отряда',
    'Номинация',
    'Количество участников',
    'Итоговое место',
    'Сумма мест',
    'Численность членов линейного студенческого отряда в соответствии с объемом уплаченных членских взносов',
    'Прохождение Командиром и Комиссаром студенческого отряда региональной школы командного состава',
    'Получение командным составом отряда образования в корпоративном университете РСО',
    'Прохождение обучение по охране труда и пожарной безопасности в рамках недели охраны труда РСО',
    'Процент членов студенческого отряда, прошедших профессиональное обучение',
    'Участие членов студенческого отряда в обязательных общесистемных мероприятиях на региональном уровне',
    'Участие членов студенческого отряда в окружных и межрегиональных мероприятиях РСО',
    'Участие членов студенческого отряда во всероссийских мероприятиях РСО',
    'Призовые места отряда в окружных и межрегиональных мероприятиях и конкурсах РСО',
    'Призовые места отряда во Всероссийских мероприятиях и конкурсах РСО',
    'Призовые места отряда на окружных и межрегиональных трудовых проектах',
    'Призовые места отряда на всероссийских трудовых проектах',
    'Организация собственных мероприятий отряда',
    'Отношение количества бойцов, отработавших в летнем трудовом семестре, к общему числу членов отряда',
    'Победы членов отряда в региональных, окружных и всероссийских грантовых конкурсах, направленных на развитие студенческих отрядов',
    'Активность отряда в социальных сетях',
    'Количество упоминаний в СМИ о прошедших творческих, добровольческих и патриотических мероприятиях отряда',
    'Охват бойцов, принявших участие во Всероссийском дне ударного труда',
    'Отсутствие нарушении техники безопасности, охраны труда и противопожарной безопасности в трудовом семестре',
    'Соответствие требованиями положения символики и атрибутике форменной одежды и символики отрядов'
]
COMPETITION_PARTICIPANTS_DATA_HEADERS = [
    '№',
    'Регион',
    'ФИО',
    'Отряд',
    'Статус отряда',
    'Номинация',
    'Должность',
    'Верификация',
    'Членский взнос'
]
