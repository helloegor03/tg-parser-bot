import telebot
import requests
import json
import time
import os
from config import TOKEN

bot = telebot.TeleBot('TOKEN') #Токен


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет!')


@bot.message_handler(commands=['info'])
def info_message(message):
    bot.send_message(message.chat.id,
                     'Этот бот предназначен для того, чтобы найти подходящие вакансии по твоей специальности и опыту работы')


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


def get_vacancies(keyword):
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": keyword,
        "area": 1,  # Айди area, для примера сейчас только Москва
        "per_page": 10,  # Number of vacancies per page
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