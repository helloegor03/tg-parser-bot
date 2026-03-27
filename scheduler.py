# ============================================================
#  scheduler.py — фоновая проверка подписок раз в час
# ============================================================

import time
import json
import logging
import threading

from config import SUBSCRIPTION_INTERVAL
from db import sub_all, sub_update_known
from hh_api import search_vacancies

logger = logging.getLogger(__name__)


def _check_subscriptions(bot):
    """Один проход: проверяем все подписки, шлём новые вакансии."""
    subs = sub_all()
    for sub in subs:
        try:
            known_ids = json.loads(sub.get("known_ids") or "[]")

            vacancies = search_vacancies(
                keyword=sub["keyword"],
                city_id=sub.get("city_id"),
                experience=sub.get("experience"),
                salary_from=sub.get("salary_from"),
                employment=sub.get("employment"),
            )

            new_vacancies = [v for v in vacancies if v["id"] not in known_ids]

            if new_vacancies:
                header = (
                    f"🔔 <b>Новые вакансии по подписке «{sub['keyword']}»"
                    + (f" · {sub['city_name']}" if sub.get("city_name") else "")
                    + ":</b>"
                )
                bot.send_message(sub["user_id"], header, parse_mode="HTML")

                for v in new_vacancies[:5]:  # не спамим больше 5 за раз
                    text = (
                        f"📌 <b>{v['title']}</b>\n"
                        f"🏢 {v['company']}\n"
                        f"💰 {v['salary']}\n"
                        f'<a href="{v["url"]}">Открыть вакансию →</a>'
                    )
                    bot.send_message(sub["user_id"], text, parse_mode="HTML",
                                     disable_web_page_preview=True)

            # Обновляем known_ids (храним только последние 50)
            all_ids = list({v["id"] for v in vacancies} | set(known_ids))[-50:]
            sub_update_known(sub["id"], all_ids, int(time.time()))

        except Exception as e:
            logger.error("Subscription %s check error: %s", sub["id"], e)


def start_scheduler(bot):
    """Запускаем бесконечный цикл в отдельном потоке."""

    def loop():
        logger.info("Scheduler started (interval=%ds)", SUBSCRIPTION_INTERVAL)
        while True:
            time.sleep(SUBSCRIPTION_INTERVAL)
            logger.info("Checking subscriptions...")
            _check_subscriptions(bot)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
