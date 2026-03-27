# ============================================================
#  keyboards.py — все inline-клавиатуры бота
# ============================================================

from telebot import types
from config import POPULAR_CITIES


def kb_cities() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = [
        types.InlineKeyboardButton(name, callback_data=f"city:{city_id}:{name}")
        for name, city_id in POPULAR_CITIES.items()
    ]
    markup.add(*btns)
    markup.add(
        types.InlineKeyboardButton("🌍 Другой город", callback_data="city:other"),
        types.InlineKeyboardButton("🗺 Любой", callback_data="city:0:Любой"),
    )
    return markup


def kb_experience() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    options = [
        ("🌱 Без опыта",  "noExperience"),
        ("📘 1–3 года",   "between1And3"),
        ("📗 3–6 лет",    "between3And6"),
        ("🏆 Более 6",    "moreThan6"),
        ("⏩ Не важно",   "any"),
    ]
    for label, val in options:
        markup.add(types.InlineKeyboardButton(label, callback_data=f"exp:{val}"))
    return markup


def kb_salary() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=2)
    options = [
        ("от 50 000 ₽",  "50000"),
        ("от 80 000 ₽",  "80000"),
        ("от 100 000 ₽", "100000"),
        ("от 150 000 ₽", "150000"),
        ("от 200 000 ₽", "200000"),
        ("✏️ Ввести",     "custom"),
        ("⏩ Не важно",   "any"),
    ]
    for label, val in options:
        markup.add(types.InlineKeyboardButton(label, callback_data=f"salary:{val}"))
    return markup


def kb_employment_type() -> types.InlineKeyboardMarkup:
    """Тип занятости (employment)"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    options = [
        ("🏢 Полная занятость", "full"),
        ("📊 Частичная занятость", "part"),
        ("📋 Проектная работа", "project"),
        ("🤝 Волонтерство", "volunteer"),
        ("⏩ Не важно", "any"),
    ]
    for label, val in options:
        markup.add(types.InlineKeyboardButton(label, callback_data=f"emp_type:{val}"))
    return markup

def kb_schedule() -> types.InlineKeyboardMarkup:
    """График работы (schedule)"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    options = [
        ("🏠 Удаленная работа", "remote"),
        ("🔄 Гибкий график", "flexible"),
        ("🏢 Полный день", "full_day"),
        ("🌙 Сменный график", "shift"),
        ("⏩ Любой график", "any"),
    ]
    for label, val in options:
        markup.add(types.InlineKeyboardButton(label, callback_data=f"schedule:{val}"))
    return markup

def kb_vacancy(
    vacancy_id: str,
    index: int,
    total: int,
    is_fav: bool,
) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=3)

    prev_btn = types.InlineKeyboardButton(
        "⬅️", callback_data=f"page:{index - 1}" if index > 0 else "page:noop"
    )
    counter_btn = types.InlineKeyboardButton(
        f"{index + 1}/{total}", callback_data="page:noop"
    )
    next_btn = types.InlineKeyboardButton(
        "➡️", callback_data=f"page:{index + 1}" if index < total - 1 else "page:noop"
    )
    markup.add(prev_btn, counter_btn, next_btn)

    fav_label = "❌ Убрать из избранного" if is_fav else "⭐ В избранное"
    fav_data  = f"fav:remove:{vacancy_id}" if is_fav else f"fav:add:{vacancy_id}"
    markup.add(types.InlineKeyboardButton(fav_label, callback_data=fav_data))
    markup.add(types.InlineKeyboardButton("🔔 Подписаться на новые", callback_data="sub:add"))
    markup.add(types.InlineKeyboardButton("🔍 Новый поиск", callback_data="search:new"))
    return markup


def kb_favorites(favorites: list[dict]) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    for fav in favorites[:10]:
        title = (fav["title"] or "Вакансия")[:40]
        markup.add(types.InlineKeyboardButton(
            f"❌ {title}",
            callback_data=f"fav:remove:{fav['vacancy_id']}",
        ))
    markup.add(types.InlineKeyboardButton("🔍 Новый поиск", callback_data="search:new"))
    return markup


def kb_subscriptions(subs: list[dict]) -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup(row_width=1)
    for sub in subs:
        label = f"❌ {sub['keyword']} · {sub['city_name'] or 'Любой город'}"
        markup.add(types.InlineKeyboardButton(label, callback_data=f"sub:del:{sub['id']}"))
    markup.add(types.InlineKeyboardButton("🔍 Новый поиск", callback_data="search:new"))
    return markup


def kb_cancel() -> types.InlineKeyboardMarkup:
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Отменить", callback_data="action:cancel"))
    return markup
