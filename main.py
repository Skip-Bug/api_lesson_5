from terminaltables import AsciiTable 
from dotenv import load_dotenv
import requests
import time
import os



def predict_salary(salary_from, salary_to):
    """Усредняет зарплату.

    Если указаны обе границы (payment_from и payment_to)
    возвращает среднее арифметическое.
    Если только payment_from возвращает payment_from * 1.2.
    Если только payment_to возвращает payment_to * 0.8.
    Если ни одной границы нет возвращает None.
    """
    if salary_from and salary_to:
        return int((salary_from + salary_to) / 2)
    return int(salary_from * 1.2) if salary_from else int(salary_to * 0.8)


def predict_rub_salary_hh(vacancy):
    """Собирает информацию по зарплатам из вакансий.

    Принимает объект вакансии, возвращает усредненную зарплату в рублях,
    если зарплата указана и валюта RUR, иначе None.

    Args:
        vacancy (dict): словарь с данными одной вакансии от API Head Hunter.

    Returns:
        int | None: усредненная зарплата в рублях или None,
        если зарплата не указана.
    """
    salary = vacancy.get('salary')
    if not salary or salary.get('currency') != 'RUR':
        return None
    salary_to = salary.get('to')
    salary_from = salary.get('from')
    return predict_salary(salary_from, salary_to)


def predict_rub_salary_sj(vacancy):
    """Собирает информацию по зарплатам из вакансий.

    Принимает объект вакансии SuperJob,
    возвращает усредненную зарплату в рублях,
    если зарплата указана, иначе None.

    Args:
        vacancy (dict): словарь с данными одной вакансии от API SuperJob.

    Returns:
        int | None: усреденная зарплата в рублях или None,
        если зарплата не указана.
    """
    salary_from = vacancy.get('payment_from')
    salary_to = vacancy.get('payment_to')

    if not salary_from and not salary_to:
        return None
    return predict_salary(salary_from, salary_to)


def fetch_vacancies_sj(
    keyword,
    town,
    period,
    api_key,
    per_page=100,
):
    """
    Загружает все доступные вакансии SuperJob по ключевому слову и городу.
    
    no_agreement параметр отвечающий за показ вакансий с пустыми полями
    зарплаты.

    Args:
        keyword (str): ключевое слово для поиска (например, 'Python').
        town (int): ID города (например, 4 для Москвы).
        period (int | None): Период публикации вакансии.
        Возможные значения:
                0 — за всё время.
                1 — за последние 24 часа.
                3 — за последние 3 дня.
                7 — за последнюю неделю.
        Если None, фильтрация по периоду не применяется.
        api_key (str): секретный ключ API SuperJob.
        per_page (int): количество вакансий на страницу (1..100).
        По умолчанию 100.   
    
    Returns:
        tuple[list, int, str | None]:
        (список вакансий, общее количество найденных, название города).
    """
    url = 'https://api.superjob.ru/2.0/vacancies/'
    headers = {'X-Api-App-Id': api_key, 'User-Agent': 'Mozilla/5.0'}
    no_agreement = 1
    all_vacancies = []
    total_found = 0
    town_name = None
    page = 0
    while True:
        params = {
            'page': page,
            'count': per_page,
            'town': town,
            'keyword': keyword,
            'no_agreement': no_agreement
        }
        if period is not None:
            params['period'] = period
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            response_api = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка SuperJob для {keyword} (стр. {page+1}): {e}")
            break
        
        vacancies = response_api.get('objects', [])
        if not vacancies:
            break
        
        if town_name is None and vacancies:
            town_name = vacancies[0].get('town', {}).get('title')
        
        all_vacancies.extend(vacancies)
        total_found = response_api.get('total', len(all_vacancies))
        time.sleep(1)
        if not response_api.get('more'):
            break
        page += 1
    return all_vacancies, total_found, town_name


def fetch_vacancies_hh(
    text,
    area,
    period=None,
    per_page=100,
):
    """Загружает доступные вакансии Head Hunter по ключевому слову и городу.


    only_with_salary параметр отвечающий за показ вакансий с пустыми полями
    зарплаты.

    Args:
        text (str): ключевое слово для поиска (например, 'Python').
        area (int): ID города (например, 1 для Москвы).
        period (int | None): Период публикации вакансии.
        Возможные значения:
                0 — за всё время.
                1 — за последние 24 часа.
                3 — за последние 3 дня.
                30 — за последний месяц (Для hh.ru это максимум).
        Если None, фильтрация по периоду не применяется.
        per_page (int): количество вакансий на страницу (1..100).
        По умолчанию 100.

    Returns:
            tuple[list, int, str | None]:
            (список вакансий, общее количество найденных, название города).
    """
    url = 'https://api.hh.ru/vacancies'
    headers = {'User-Agent': 'Mozilla/5.0'}
    only_with_salary = True
    all_vacancies = []
    total_found = 0
    town_name = None
    page = 0
    while True:
        params = {
            'page': page,
            'text': text,
            'area': area,
            'per_page': per_page,
            'only_with_salary': only_with_salary,
        }

        if period is not None:
            params['period'] = period

        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            response_api = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка HeadHunter для {text} (стр. {page+1}): {e}")
            break
        
        vacancies = response_api.get('items', [])
        if not vacancies:
            break
        
        if town_name is None and vacancies:
            town_name = vacancies[0].get('area', {}).get('name')        
        
        all_vacancies.extend(vacancies)
        total_found = response_api.get('found', len(all_vacancies))
        time.sleep(1)
        if page >= response_api.get('pages', 1) - 1:
            break
        page += 1   
            
    return all_vacancies, total_found, town_name


def calculate_stats(vacancies, total_found, salary_predictor):
    """Собирает статистику для каждой вакансии.

    Args:
        vacancies (list): список вакансий (словарей).
        total_found (int): общее количество вакансий по данным API.
        salary_predictor (callable): функция,
        принимающая вакансию и возвращающая зарплату в рублях или None.

    Returns:
            dict: {
                'vacancies_found': int, общее количество вакансий.
                'vacancies_processed': int, кол-во вакансий,
                 участвующих в статистике.
                'average_salary': int | None усреднённая зарплата.
            }

    """
    processed = 0
    total_salary = 0
    for vacancy in vacancies:
        salary = salary_predictor(vacancy)
        if salary is not None:
            processed += 1
            total_salary += salary
    average_salary = int(total_salary / processed) if processed else None
    return {
        'vacancies_found': total_found,
        'vacancies_processed': processed,
        'average_salary': average_salary
    }


def print_table(platform_name, lang_stats, town_name=None, period=None):
    """Выводит информацию.

    Печатает сводную таблицу для одной платформы.

    Args:
        platform_name (str): название платформы ('SuperJob' или 'HeadHunter')
        lang_stats (dict): словарь { язык: статистика } (
        результат calculate_stats).
        town_name (str): название города.
        period (int | None): период в днях (опционально)
    """
    if town_name:
        title = f"{platform_name} {town_name}"
    else:
        title = platform_name

    if period is not None:
        title += f" период {period} д."

    table_data = [['Язык', 'Всего вакансий', 'Обработано', 'Средняя зарплата']]

    for lang, stat in lang_stats.items():
        table_data.append([
            lang,
            stat['vacancies_found'],
            stat['vacancies_processed'],
            stat['average_salary'] or '-'
        ])

    table = AsciiTable(table_data, title)
    table.justify_columns[3] = 'right'
    print(table.table)
    print()


def main():
    """Парсит по superjob.ru и hh.ru.

    Поиск вакансий на сайте superjob.ru и hh.ru.
    """
    load_dotenv()
    area_hh_id = int(os.getenv('AREA_HH','1'))
    town_sj_id = int(os.getenv('TOWN_SJ','4'))
    
    period_raw = os.getenv('PERIOD')
    try:
        period = int(period_raw) if period_raw else None
    except ValueError:
        print(f"Ошибка: PERIOD='{period_raw}' — не число")
    period = None
    
    langs_str = os.getenv('PROGRAMMING_LANGUAGES', '')
    langs = [
        lang.strip()
        for lang in langs_str.split(',')
        if lang.strip()
    ]
        
    sj_key = os.getenv('SJ_KEY')
    if not sj_key:
        print("Ошибка: не найден SJ_KEY в переменных окружения")
        return

    stats_sj = {}
    stats_hh = {}
    sj_town = None
    hh_town = None
    print("Собираем статистику, подождите пару минут...")
    for lang in langs:

        vacancies_sj, total_sj, town_sj = fetch_vacancies_sj(
            lang,
            town_sj_id,
            period,
            sj_key
        )
        stats_sj[lang] = calculate_stats(
            vacancies_sj,
            total_sj,
            predict_rub_salary_sj
        )
        if sj_town is None and town_sj is not None:
            sj_town = town_sj
        
        vacancies_hh, total_hh, town_hh = fetch_vacancies_hh(
            lang,
            area_hh_id,
            period
        )
        stats_hh[lang] = calculate_stats(
            vacancies_hh,
            total_hh,
            predict_rub_salary_hh
        )
        if hh_town is None and town_hh is not None:
            hh_town = town_hh

    print_table('SuperJob', stats_sj, sj_town, period)
    print_table('HeadHunter', stats_hh, hh_town, period)


if __name__ == "__main__":
    main()
