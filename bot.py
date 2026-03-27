# ============================================================
#  bot.py — основной файл, все хэндлеры
# ============================================================

import json
import logging

import requests
import telebot
from telebot import types
from telebot import apihelper

# ========== НАСТРОЙКА ЛОГГИРОВАНИЯ (ДОЛЖНА БЫТЬ В САМОМ НАЧАЛЕ) ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
# =========================================================================

from config import TOKEN, USE_PROXY, PROXY_URL
from db import (
    init_db, get_state, set_state, clear_state,
    fav_add, fav_remove, fav_list, fav_exists,
    sub_add, sub_list, sub_delete, cache_cleanup,
)
from hh_api import search_vacancies, find_city_id
from keyboards import (
    kb_cities, kb_experience, kb_salary, kb_employment_type, kb_schedule,
    kb_vacancy, kb_favorites, kb_subscriptions, kb_cancel,
)
from utils import format_vacancy_card
from scheduler import start_scheduler

# ========== АВТОМАТИЧЕСКАЯ НАСТРОЙКА ПРОКСИ ==========
if USE_PROXY and PROXY_URL:
    # Настройка прокси для telebot
    apihelper.proxy = {
        'http': PROXY_URL,
        'https': PROXY_URL
    }
    
    # Настройка прокси для requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    
    # Создаем сессию с прокси
    session = requests.Session()
    session.proxies = {
        'http': PROXY_URL,
        'https': PROXY_URL
    }
    
    # Настраиваем retry
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # Переопределяем сессию для telebot
    apihelper._get_req_session = lambda: session
    
    logger.info(f"✅ Proxy настроен: {PROXY_URL}")
else:
    logger.info("✅ Работаем без прокси (прямое подключение)")

# ============================================================

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
# ════════════════════════════════════════════════════════════
#  /start, /help
# ════════════════════════════════════════════════════════════

@bot.message_handler(commands=["start"])
def cmd_start(message):
    clear_state(message.chat.id)
    name = message.from_user.first_name or "друг"
    bot.send_message(
        message.chat.id,
        f"Привет, <b>{name}</b>! 👋\n\n"
        "Я ищу вакансии на <b>HeadHunter</b> прямо в Telegram.\n\n"
        "Команды:\n"
        "🔍 /search — начать поиск\n"
        "⭐ /favorites — избранные вакансии\n"
        "🔔 /subscriptions — мои подписки\n"
        "❓ /help — помощь",
    )


@bot.message_handler(commands=["help"])
def cmd_help(message):
    bot.send_message(
        message.chat.id,
        "🤖 <b>HH Handler Bot</b>\n\n"
        "<b>Как искать:</b>\n"
        "1. /search → выбери город, опыт, зарплату\n"
        "2. Введи ключевое слово (например, <i>Python Developer</i>)\n"
        "3. Листай карточки кнопками ⬅️ ➡️\n\n"
        "<b>Фишки:</b>\n"
        "⭐ Сохраняй вакансии в избранное\n"
        "🔔 Подпишись и получай новые вакансии автоматически\n\n"
        "Результаты кэшируются на 30 минут — бот быстрый.",
    )


# ════════════════════════════════════════════════════════════
#  /search — начало поиска
# ════════════════════════════════════════════════════════════

@bot.message_handler(commands=["search"])
def cmd_search(message):
    _start_search(message.chat.id)


def _start_search(chat_id: int):
    set_state(chat_id, "choosing_city", {})
    bot.send_message(
        chat_id,
        "📍 <b>Шаг 1/5.</b> Выбери город:",
        reply_markup=kb_cities(),
    )


# ════════════════════════════════════════════════════════════
#  callback_query — всё управление через inline-кнопки
# ════════════════════════════════════════════════════════════

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call: types.CallbackQuery):
    data = call.data
    cid  = call.message.chat.id

    bot.answer_callback_query(call.id)

    # ── Навигация noop ──────────────────────────────────────
    if data == "page:noop":
        return

    # ── Новый поиск ─────────────────────────────────────────
    if data == "search:new":
        _start_search(cid)
        return

    # ── Отмена ──────────────────────────────────────────────
    if data == "action:cancel":
        clear_state(cid)
        bot.send_message(cid, "Действие отменено. /search — начать заново.")
        return

    # ── Выбор города ────────────────────────────────────────
    if data.startswith("city:"):
        parts = data.split(":", 2)
        if parts[1] == "other":
            set_state(cid, "entering_city", {})
            bot.send_message(
                cid, "✏️ Введи название города:",
                reply_markup=kb_cancel(),
            )
        else:
            city_id   = int(parts[1])
            city_name = parts[2] if len(parts) > 2 else "Любой"
            _, d = get_state(cid)
            d.update(city_id=city_id, city_name=city_name)
            set_state(cid, "choosing_experience", d)
            bot.send_message(
                cid,
                f"✅ Город: <b>{city_name}</b>\n\n"
                "💼 <b>Шаг 2/5.</b> Выбери опыт работы:",
                reply_markup=kb_experience(),
            )
        return

    # ── Выбор опыта ─────────────────────────────────────────
    if data.startswith("exp:"):
        exp = data.split(":", 1)[1]
        _, d = get_state(cid)
        d["experience"] = None if exp == "any" else exp
        set_state(cid, "choosing_salary", d)
        bot.send_message(
            cid,
            "💰 <b>Шаг 3/5.</b> Минимальная зарплата:",
            reply_markup=kb_salary(),
        )
        return

    # ── Выбор зарплаты ──────────────────────────────────────
    if data.startswith("salary:"):
        val = data.split(":", 1)[1]
        _, d = get_state(cid)
        if val == "custom":
            set_state(cid, "entering_salary", d)
            bot.send_message(cid, "✏️ Введи минимальную зарплату (число):",
                             reply_markup=kb_cancel())
            return
        d["salary_from"] = int(val) if val != "any" else None
        set_state(cid, "choosing_employment", d)
        bot.send_message(
            cid,
            "🏢 <b>Шаг 4/5.</b> Тип занятости:",
            reply_markup=kb_employment_type(),
        )
        return

    # ── Тип занятости ───────────────────────────────────────
    if data.startswith("emp_type:"):
        emp_type = data.split(":", 1)[1]
        _, d = get_state(cid)
        d["employment_type"] = None if emp_type == "any" else emp_type
        set_state(cid, "choosing_schedule", d)
        bot.edit_message_text(
            "📅 <b>Шаг 5/6.</b> Выбери график работы:",
            cid,
            call.message.message_id,
            reply_markup=kb_schedule(),
        )
        return

    # ── График работы ───────────────────────────────────────
    if data.startswith("schedule:"):
        schedule = data.split(":", 1)[1]
        _, d = get_state(cid)
        d["schedule"] = None if schedule == "any" else schedule
        set_state(cid, "entering_keyword", d)
        bot.edit_message_text(
            "🔎 <b>Шаг 6/6.</b> Введи ключевое слово для поиска:\n\n"
            "<i>Например: Python Developer, бухгалтер, маркетолог</i>",
            cid,
            call.message.message_id,
            reply_markup=kb_cancel(),
        )
        return

    # ── Пагинация ───────────────────────────────────────────
    if data.startswith("page:"):
        idx_str = data.split(":", 1)[1]
        _, d = get_state(cid)
        vacancies = d.get("vacancies", [])
        if not vacancies:
            bot.send_message(cid, "Результаты устарели. /search — ищи заново.")
            return
        new_idx = int(idx_str)
        if new_idx < 0 or new_idx >= len(vacancies):
            return
        d["current_index"] = new_idx
        set_state(cid, "browsing", d)
        _show_vacancy(call.message, cid, vacancies, new_idx)
        return

    # ── Избранное: добавить ─────────────────────────────────
    if data.startswith("fav:add:"):
        vacancy_id = data.split(":", 2)[2]
        _, d = get_state(cid)
        vacancies = d.get("vacancies", [])
        vacancy   = next((v for v in vacancies if v["id"] == vacancy_id), None)
        if vacancy and fav_add(cid, vacancy):
            bot.send_message(cid, f"⭐ Вакансия <b>{vacancy['title']}</b> добавлена в избранное.")
        else:
            bot.send_message(cid, "Уже в избранном.")
        # Обновляем кнопки
        idx = d.get("current_index", 0)
        _edit_vacancy_markup(call.message, cid, vacancies, idx)
        return

    # ── Избранное: убрать ───────────────────────────────────
    if data.startswith("fav:remove:"):
        vacancy_id = data.split(":", 2)[2]
        fav_remove(cid, vacancy_id)
        bot.send_message(cid, "Вакансия убрана из избранного.")
        # Пробуем обновить кнопки если мы в режиме browsing
        _, d = get_state(cid)
        if d.get("vacancies"):
            idx = d.get("current_index", 0)
            _edit_vacancy_markup(call.message, cid, d["vacancies"], idx)
        return

    # ── Подписки: добавить ──────────────────────────────────
    if data == "sub:add":
        _, d = get_state(cid)
        if not d.get("keyword"):
            bot.send_message(cid, "Сначала выполни поиск.")
            return
        sub_id = sub_add(cid, d)
        keyword   = d["keyword"]
        city_name = d.get("city_name", "любой город")
        bot.send_message(
            cid,
            f"🔔 Подписка оформлена!\n"
            f"Буду присылать новые вакансии по запросу «<b>{keyword}</b>» в <b>{city_name}</b>.\n\n"
            f"Управление подписками: /subscriptions",
        )
        return

    # ── Подписки: удалить ───────────────────────────────────
    if data.startswith("sub:del:"):
        sub_id = int(data.split(":", 2)[2])
        sub_delete(sub_id, cid)
        subs = sub_list(cid)
        if subs:
            bot.edit_message_reply_markup(
                cid, call.message.message_id,
                reply_markup=kb_subscriptions(subs),
            )
        else:
            bot.edit_message_text(
                "У тебя нет активных подписок. /search — начать поиск.",
                cid, call.message.message_id,
            )
        return


# ════════════════════════════════════════════════════════════
#  Обработка текстовых сообщений (ввод в процессе диалога)
# ════════════════════════════════════════════════════════════

@bot.message_handler(content_types=["text"])
def handle_text(message):
    cid  = message.chat.id
    text = message.text.strip()
    state, d = get_state(cid)

    # ── Ввод названия города ────────────────────────────────
    if state == "entering_city":
        if len(text) < 2:
            bot.send_message(cid, "Слишком короткое название. Попробуй ещё раз:")
            return
        bot.send_message(cid, f"🔎 Ищу город «{text}»...")
        city_id, city_name = find_city_id(text)
        if not city_id:
            bot.send_message(
                cid,
                "Не нашёл такой город в базе HH. Попробуй другое написание "
                "или выбери из списка. /search",
            )
            return
        d.update(city_id=city_id, city_name=city_name)
        set_state(cid, "choosing_experience", d)
        bot.send_message(
            cid,
            f"✅ Город: <b>{city_name}</b>\n\n"
            "💼 <b>Шаг 2/6.</b> Выбери опыт работы:",
            reply_markup=kb_experience(),
        )
        return

    # ── Ввод зарплаты вручную ───────────────────────────────
    if state == "entering_salary":
        if not text.isdigit():
            bot.send_message(cid, "Введи число, например: 80000")
            return
        d["salary_from"] = int(text)
        set_state(cid, "choosing_employment_type", d)  # Изменено: choosing_employment_type
        bot.send_message(
            cid,
            "👔 <b>Шаг 4/6.</b> Тип занятости:",
            reply_markup=kb_employment_type(),  # Изменено: kb_employment_type
        )
        return

    # ── Ввод ключевого слова ────────────────────────────────
    if state == "entering_keyword":
        if len(text) < 2:
            bot.send_message(cid, "Слишком короткий запрос. Попробуй ещё раз:")
            return

        d["keyword"] = text
        set_state(cid, "searching", d)

        city_name = d.get("city_name", "любом городе")
        bot.send_message(
            cid,
            f"🔍 Ищу «<b>{text}</b>» в <b>{city_name}</b>...",
        )

        vacancies = search_vacancies(
            keyword=text,
            city_id=d.get("city_id"),
            experience=d.get("experience"),
            salary_from=d.get("salary_from"),
            employment=d.get("employment_type"),  # Изменено: employment_type
            schedule=d.get("schedule"),           # Добавлено: schedule
        )

        if not vacancies:
            bot.send_message(
                cid,
                f"😔 К сожалению, по запросу «<b>{text}</b>» в <b>{city_name}</b> "
                "ничего не нашлось.\n\n"
                "Попробуй изменить фильтры: /search",
            )
            clear_state(cid)
            return

        d["vacancies"]      = vacancies
        d["current_index"]  = 0
        set_state(cid, "browsing", d)

        bot.send_message(
            cid,
            f"✅ Найдено вакансий: <b>{len(vacancies)}</b>. Листай кнопками ⬅️ ➡️",
        )
        _show_vacancy_new(cid, vacancies, 0)
        return

    # ── Неизвестное сообщение ───────────────────────────────
    bot.send_message(
        cid,
        "Не понимаю. Используй команды:\n"
        "/search — поиск вакансий\n"
        "/favorites — избранное\n"
        "/subscriptions — подписки",
    )

# ════════════════════════════════════════════════════════════
#  /favorites, /subscriptions
# ════════════════════════════════════════════════════════════

@bot.message_handler(commands=["favorites"])
def cmd_favorites(message):
    cid = message.chat.id
    favs = fav_list(cid)
    if not favs:
        bot.send_message(cid, "У тебя нет избранных вакансий.\n/search — найти что-нибудь интересное.")
        return

    text = f"⭐ <b>Избранное</b> ({len(favs)} вакансий)\n\n"
    for i, fav in enumerate(favs[:10], 1):
        text += (
            f"{i}. <a href=\"{fav['url']}\">{fav['title']}</a>\n"
            f"   🏢 {fav['company']} · 💰 {fav['salary'] or 'з/п не указана'}\n\n"
        )

    bot.send_message(
        cid, text,
        reply_markup=kb_favorites(favs),
        disable_web_page_preview=True,
    )


@bot.message_handler(commands=["subscriptions"])
def cmd_subscriptions(message):
    cid = message.chat.id
    subs = sub_list(cid)
    if not subs:
        bot.send_message(
            cid,
            "У тебя нет активных подписок.\n\n"
            "Оформить подписку можно при просмотре вакансий — нажми «🔔 Подписаться».",
        )
        return

    text = f"🔔 <b>Твои подписки</b> ({len(subs)}):\n\n"
    for sub in subs:
        text += (
            f"• <b>{sub['keyword']}</b> · {sub['city_name'] or 'любой город'}\n"
        )
    text += "\nНажми на подписку, чтобы её удалить:"

    bot.send_message(cid, text, reply_markup=kb_subscriptions(subs))


# ════════════════════════════════════════════════════════════
#  Вспомогательные функции отображения карточек
# ════════════════════════════════════════════════════════════

def _show_vacancy_new(cid: int, vacancies: list, index: int):
    """Отправляем новое сообщение с карточкой вакансии."""
    v       = vacancies[index]
    is_fav  = fav_exists(cid, v["id"])
    text    = format_vacancy_card(v, index, len(vacancies))
    markup  = kb_vacancy(v["id"], index, len(vacancies), is_fav)
    bot.send_message(cid, text, reply_markup=markup, disable_web_page_preview=True)


def _show_vacancy(orig_message, cid: int, vacancies: list, index: int):
    """Редактируем существующее сообщение при навигации."""
    v       = vacancies[index]
    is_fav  = fav_exists(cid, v["id"])
    text    = format_vacancy_card(v, index, len(vacancies))
    markup  = kb_vacancy(v["id"], index, len(vacancies), is_fav)
    try:
        bot.edit_message_text(
            text,
            cid,
            orig_message.message_id,
            reply_markup=markup,
            disable_web_page_preview=True,
        )
    except Exception:
        bot.send_message(cid, text, reply_markup=markup, disable_web_page_preview=True)


def _edit_vacancy_markup(orig_message, cid: int, vacancies: list, index: int):
    """Только обновляем кнопки (после добавления/удаления из избранного)."""
    v      = vacancies[index]
    is_fav = fav_exists(cid, v["id"])
    markup = kb_vacancy(v["id"], index, len(vacancies), is_fav)
    try:
        bot.edit_message_reply_markup(cid, orig_message.message_id, reply_markup=markup)
    except Exception:
        pass


# ════════════════════════════════════════════════════════════
#  Запуск
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    init_db()
    cache_cleanup()
    start_scheduler(bot)
    logger.info("Bot started.")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
