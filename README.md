# 🤖 HH Handler Bot v2

Telegram Bot for searching vacancies on HeadHunter has been rewritten from scratch.

## Structure

```
hh_bot/
├── bot.py           # Entry point, all handlers
├── hh_api.py        # HH API Client (session, cache, normalization)
├── db.py            # SQLite: states, favorites, subscriptions, cache
├── keyboards.py     # All inline keyboards
├── utils.py         # format_salary, strip_html, format_date
├── scheduler.py     # Background subscription checking
├── config.py        # Settings
└── requirements.txt
```

## Installation

```bash
git clone <repo>
cd hh_bot
pip install -r requirements.txt
```

Edit `config.py` and insert the token from @BotFather:
```python
TOKEN = "1234567890:AAxxxx..."
```

## Start

```bash
python bot.py
```

## Possibilities

| Feature | Description |
|------|----------|
| 🔍 Search | Inline buttons: city, experience, salary, employment → keyword |
| 📄 Cards | Pagination ⬅️ ➡️, clean formatting, salary range |
| ⭐ Favorites | Save vacancies, view the list, delete |
| 🔔 Subscriptions | The bot automatically checks for new vacancies once an hour. |
| 💾 SQLite | States survive bot reboot |
| ⚡ Cache | Repeated requests are not sent to the API (30 min) |
| 🛡 Rate limit | Processing 403, retry at 5xx, timeout |

## HH API

The public API doesn't require a key for basic requests.
Documentation: https://github.com/hhru/api
