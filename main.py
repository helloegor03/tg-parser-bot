import telebot
import requests
from config import TOKEN
from telebot import types

bot = telebot.TeleBot(TOKEN) #Токен
@bot.message_handler(commands=['start'])
def start_message(message):
    markup = types.InlineKeyboardMarkup()  # Создаем клавиатуру
    item1 = types.InlineKeyboardButton("Как пользоваться данным ботом", callback_data='button_pressed')  # Создаем кнопку
    markup.add(item1)  # Добавляем кнопку в клавиатуру

    bot.send_message(message.chat.id, 'Привет, это HH хендлер!', reply_markup=markup)
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == 'button_pressed':
        bot.answer_callback_query(callback_query_id=call.id)
        bot.send_message(call.message.chat.id, 'Чтобы получить список вакансий, вы должно написать команду /search вакансия которая вас интересует!')

# Хранение юзера]
USER_STATES = {}
@bot.message_handler(commands=['profile'])
def profile_message(message):
    USER_STATES[message.chat.id] = {'state': 'waiting_city'}
    bot.send_message(message.chat.id, "Выбери свой город из списка:\n1. Москва\n2. Санкт-Петербург")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    state = USER_STATES.get(message.chat.id, {})

    if state.get('state') == 'waiting_city':
        if message.text.strip() == '1':
            USER_STATES[message.chat.id] = {'state': 'waiting_keyword', 'city': 1}  # Москва
            bot.send_message(message.chat.id, "Отлично! Теперь укажите ключевое слово для поиска вакансий.")
        elif message.text.strip() == '2':
            USER_STATES[message.chat.id] = {'state': 'waiting_keyword', 'city': 2}  # СПб
            bot.send_message(message.chat.id, "Отлично! Теперь укажите ключевое слово для поиска вакансий.")
        else:
            bot.send_message(message.chat.id, "Пожалуйста, введите 1 или 2.")

    elif state.get('state') == 'waiting_keyword':
        keyword = message.text.strip()
        area = state.get('city', 1)
        vacancies = get_vacancies(keyword, area)

        if not vacancies:
            bot.send_message(message.chat.id, 'Вакансий по вашему запросу не найдено.')
            return

        for vacancy in vacancies:
            bot.send_message(
                message.chat.id,
                f"📌 {vacancy['title']}\n"
                f"🏢 {vacancy['company']}\n"
                f"🔗 {vacancy['url']}\n"
                f"💼 {vacancy['description']}"
            )

@bot.message_handler(commands=['search'])
def search_message(message):
    if not message.text.split():
        bot.send_message(message.chat.id, 'Пожалуйста, укажите поисковый запрос после команды')
        return

    keyword = message.text.split(maxsplit=1)[1]
    vacancies = get_vacancies(keyword)

    if not vacancies:
        bot.send_message(message.chat.id, 'Вакансий по вашему запросу не найдено.')
        return

    for vacancy in vacancies:
        bot.send_message(
            message.chat.id,
            f"📌 {vacancy['title']}\n"
            f"🏢 {vacancy['company']}\n"
            f"🔗 {vacancy['url']}\n"
            f"💼 {vacancy['description']}"
        )

def get_vacancies(keyword, area):
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": keyword,
        "area": area,  # Айди area, для примера сейчас только Москва и Спб
        "per_page": 10,  # Число вакансий на страничке
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()

        data = response.json()
        vacancies = data.get("items", [])

        formatted_vacancies = []
        for vacancy in vacancies:
            formatted_vacancy = {
                'title': vacancy.get("name", "Название не указано"),
                'company': vacancy.get("employer", {}).get("name", "Компания не указана"),
                'url': vacancy.get("alternate_url", ""),
                'description': vacancy.get("snippet", {}).get("responsibility", "Описание не указано")
            }
            formatted_vacancies.append(formatted_vacancy)

        return formatted_vacancies
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении вакансий: {e}")
        return []


bot.polling(non_stop=True)