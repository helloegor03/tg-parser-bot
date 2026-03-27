# ============================================================
#  config.py — все настройки в одном месте
# ============================================================

import os
import socket

# Токен от @BotFather
TOKEN = "7020497677:AAF4UvElsqL8cuLnVmfio0rjZMxIRx8z2a4"

# HH API (публичный, ключ не нужен для базовых запросов)
HH_API_URL = "https://api.hh.ru"
HH_USER_AGENT = "HH-JobBot/2.0 (job-search-telegram-bot)"

# SQLite
DB_PATH = "bot.db"

# Кэш запросов к HH (секунды)
CACHE_TTL = 1800  # 30 минут

# Интервал проверки подписок (секунды)
SUBSCRIPTION_INTERVAL = 3600  # 1 час

# Сколько вакансий показываем за один поиск
VACANCIES_PER_PAGE = 15

# Популярные города (название → area_id в HH API)
POPULAR_CITIES = {
    "Москва": 1,
    "Санкт-Петербург": 2,
    "Новосибирск": 4,
    "Екатеринбург": 3,
    "Казань": 88,
    "Нижний Новгород": 66,
    "Краснодар": 53,
    "Ростов-на-Дону": 76,
}

# ========== НАСТРОЙКА ПРОКСИ ==========
def check_tor_proxy(host='127.0.0.1', ports=[9050, 9150]):
    """
    Проверяет доступность Tor прокси на указанных портах.
    Возвращает (port, proxy_string) или (None, None)
    """
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return port, f"socks5://{host}:{port}"
        except:
            continue
    return None, None

# Автоматически определяем прокси
USE_PROXY = False
PROXY_URL = None
TOR_PORT, PROXY_URL = check_tor_proxy()

if PROXY_URL:
    USE_PROXY = True
    print(f"✅ Tor прокси найден на порту {TOR_PORT}, будет использован")
else:
    print("ℹ️ Tor прокси не найден, работаем напрямую")