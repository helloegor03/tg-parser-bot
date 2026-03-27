# ============================================================
#  utils.py — форматирование зарплат, дат, очистка HTML
# ============================================================

import re
from datetime import datetime

CURRENCY_SYMBOLS = {
    "RUR": "₽",
    "RUB": "₽",
    "USD": "$",
    "EUR": "€",
    "KZT": "₸",
    "UAH": "₴",
    "BYR": "Br",
}

EXPERIENCE_LABELS = {
    "noExperience":   "без опыта",
    "between1And3":   "1–3 года",
    "between3And6":   "3–6 лет",
    "moreThan6":      "6+ лет",
}

EMPLOYMENT_LABELS = {
    "full":     "Полный день",
    "remote":   "Удалёнка",
    "flexible": "Гибкий график",
    "part":     "Частичная занятость",
}


def format_salary(salary_data: dict | None) -> str:
    """Красивая строка зарплаты из объекта HH API."""
    if not salary_data:
        return "З/П не указана"

    fr  = salary_data.get("from")
    to  = salary_data.get("to")
    cur = CURRENCY_SYMBOLS.get(salary_data.get("currency", "RUR"), "₽")
    gross = salary_data.get("gross", False)
    tax_note = " (до вычета налогов)" if gross else ""

    def fmt(n):
        if n is None:
            return None
        if n >= 1000:
            return f"{n // 1000} {cur}" if n % 1000 == 0 else f"{n:,} {cur}".replace(",", " ")
        return f"{n} {cur}"

    fr_s, to_s = fmt(fr), fmt(to)

    if fr_s and to_s:
        result = f"{fr_s} — {to_s}"
    elif fr_s:
        result = f"от {fr_s}"
    elif to_s:
        result = f"до {to_s}"
    else:
        return "З/П не указана"

    return result + tax_note


def strip_html(text: str | None) -> str:
    """Убираем HTML-теги из сниппетов HH."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    return text.strip()


def format_date(iso_str: str | None) -> str:
    """'2025-03-20T10:00:00+0300' → '20 марта 2025'"""
    if not iso_str:
        return ""
    MONTHS = [
        "", "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]
    try:
        dt = datetime.fromisoformat(iso_str[:19])
        return f"{dt.day} {MONTHS[dt.month]} {dt.year}"
    except Exception:
        return iso_str[:10]


def format_vacancy_card(v: dict, index: int, total: int, user_id: int = None) -> str:
    """Готовая карточка вакансии для Telegram (HTML-разметка)."""
    title   = v.get("title", "Без названия")
    company = v.get("company", "Компания не указана")
    company_url = v.get("company_url", "")
    salary  = v.get("salary", "З/П не указана")
    url     = v.get("url", "")
    snippet = v.get("snippet", "")
    date    = v.get("date", "")
    city    = v.get("city", "")
    emp     = v.get("employment", "")

    company_line = (
        f'<a href="{company_url}">{company}</a>' if company_url else company
    )

    meta_parts = []
    if city:
        meta_parts.append(f"📍 {city}")
    if emp:
        meta_parts.append(emp)
    meta_line = " · ".join(meta_parts)

    snippet_line = f"\n\n📋 <i>{snippet[:300]}{'…' if len(snippet) > 300 else ''}</i>" if snippet else ""

    date_line = f"\n📅 {date}" if date else ""

    counter = f"[{index + 1} / {total}]"

    return (
        f"<b>{title}</b>  <i>{counter}</i>\n"
        f"🏢 {company_line}\n"
        f"💰 {salary}"
        + (f"\n{meta_line}" if meta_line else "")
        + snippet_line
        + date_line
        + f'\n\n<a href="{url}">🔗 Открыть вакансию</a>'
    )


def make_cache_key(keyword, city_id, experience, salary_from, employment, schedule=None):
    parts = [
        keyword or "",
        str(city_id or ""),
        experience or "",
        str(salary_from or ""),
        employment or "",
        schedule or ""  
    ]
    return ":".join(parts)