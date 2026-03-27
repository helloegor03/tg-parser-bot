# ============================================================
#  hh_api.py — клиент HeadHunter API с сессией и кэшем
# ============================================================

import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import HH_API_URL, HH_USER_AGENT, CACHE_TTL, VACANCIES_PER_PAGE
from utils import format_salary, strip_html, format_date, make_cache_key
from db import cache_get, cache_set

logger = logging.getLogger(__name__)

# ─── HTTP-сессия с retry ────────────────────────────────────

def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": HH_USER_AGENT})
    return session

_session = _make_session()

# ─── Маппинг для параметров HH API ──────────────────────────
# Для employment (тип занятости)
EMPLOYMENT_MAPPING = {
    'full': 'full',           # Полная занятость
    'part': 'part',           # Частичная занятость
    'project': 'project',     # Проектная работа
    'volunteer': 'volunteer', # Волонтерство
    'any': None
}

# Для schedule (график работы)
SCHEDULE_MAPPING = {
    'remote': 'remote',       # Удаленная работа
    'flexible': 'flexible',   # Гибкий график
    'full_day': 'fullDay',    # Полный день
    'shift': 'shift',         # Сменный график
    'any': None
}

# ─── Поиск вакансий ─────────────────────────────────────────

def search_vacancies(
    keyword: str,
    city_id: int | None = None,
    experience: str | None = None,
    salary_from: int | None = None,
    employment: str | None = None,  # Это тип занятости (full, part, project, volunteer)
    schedule: str | None = None,    # Это график (remote, flexible, fullDay)
    page: int = 0,
) -> list[dict]:
    """
    Возвращает список вакансий (уже форматированных).
    Использует кэш на 30 минут.
    """
    cache_key = make_cache_key(keyword, city_id, experience, salary_from, employment, schedule)
    cached = cache_get(cache_key)
    if cached is not None:
        logger.info("HH cache hit: %s", cache_key)
        return cached

    params = {
        "text":     keyword,
        "per_page": VACANCIES_PER_PAGE,
        "page":     page,
        "order_by": "relevance",
    }
    
    if city_id:
        params["area"] = city_id
        
    if experience and experience != 'any':
        params["experience"] = experience
        
    if salary_from and salary_from > 0:
        params["salary"] = salary_from
        
    # employment - тип занятости (полная/частичная/проектная)
    if employment and employment != 'any' and employment in EMPLOYMENT_MAPPING:
        employment_value = EMPLOYMENT_MAPPING[employment]
        if employment_value:
            params["employment"] = employment_value
            
    # schedule - график работы (удаленка/гибкий/полный день)
    if schedule and schedule != 'any' and schedule in SCHEDULE_MAPPING:
        schedule_value = SCHEDULE_MAPPING[schedule]
        if schedule_value:
            params["schedule"] = schedule_value

    logger.info(f"HH API request params: {params}")

    try:
        resp = _session.get(
            f"{HH_API_URL}/vacancies",
            params=params,
            timeout=15,
        )

        if resp.status_code == 403:
            logger.warning("HH API: rate limit / 403")
            return []
        
        if resp.status_code == 400:
            logger.error(f"HH API 400 error. Params: {params}")
            logger.error(f"Response: {resp.text}")
            
            # Если ошибка в employment или schedule, пробуем без них
            if 'employment' in params or 'schedule' in params:
                logger.info("Trying without employment/schedule filters")
                params.pop('employment', None)
                params.pop('schedule', None)
                resp = _session.get(
                    f"{HH_API_URL}/vacancies",
                    params=params,
                    timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("items", [])
                    result = [_normalize(v) for v in items]
                    cache_set(cache_key, result, CACHE_TTL)
                    return result
            return []

        resp.raise_for_status()
        data = resp.json()

    except requests.exceptions.Timeout:
        logger.error("HH API timeout")
        return []
    except requests.exceptions.RequestException as e:
        logger.error("HH API error: %s", e)
        return []

    items = data.get("items", [])
    result = [_normalize(v) for v in items]

    cache_set(cache_key, result, CACHE_TTL)
    return result


def get_vacancy_ids(
    keyword: str,
    city_id: int | None = None,
    experience: str | None = None,
    salary_from: int | None = None,
    employment: str | None = None,
    schedule: str | None = None,
) -> list[str]:
    """Только ID вакансий — для проверки подписок."""
    vacancies = search_vacancies(keyword, city_id, experience, salary_from, employment, schedule)
    return [v["id"] for v in vacancies]


def find_city_id(city_name: str) -> tuple[int | None, str | None]:
    """
    Ищем город через HH API.
    Возвращает (area_id, canonical_name) или (None, None).
    """
    try:
        resp = _session.get(
            f"{HH_API_URL}/suggests/areas",
            params={"text": city_name},
            timeout=8,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
        if items:
            return int(items[0]["id"]), items[0]["text"]
    except Exception as e:
        logger.error("find_city_id error: %s", e)
    return None, None


# ─── Нормализация ───────────────────────────────────────────

def _normalize(raw: dict) -> dict:
    employer = raw.get("employer") or {}
    snippet  = raw.get("snippet") or {}
    address  = raw.get("address") or {}

    responsibility = strip_html(snippet.get("responsibility", ""))
    requirement    = strip_html(snippet.get("requirement", ""))
    full_snippet = " ".join(filter(None, [requirement, responsibility]))

    employment_raw = (raw.get("employment") or {}).get("name", "")
    schedule_raw   = (raw.get("schedule") or {}).get("name", "")
    emp_label = f"{employment_raw} / {schedule_raw}".strip(" /")

    return {
        "id":          raw.get("id", ""),
        "title":       raw.get("name", "Без названия"),
        "company":     employer.get("name", "Компания не указана"),
        "company_url": employer.get("alternate_url", ""),
        "url":         raw.get("alternate_url", ""),
        "salary":      format_salary(raw.get("salary")),
        "snippet":     full_snippet,
        "date":        format_date(raw.get("published_at")),
        "city":        address.get("city") or (raw.get("area") or {}).get("name", ""),
        "employment":  emp_label,
    }