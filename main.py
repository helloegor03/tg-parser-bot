import telebot
import requests
import json
import time
import os

bot = telebot.TeleBot('8262292170:AAF-W8kDHTgzdbmEDep1M-ROqP2IQX2L7SI')

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, 'Привет!')

@bot.message_handler(commands=['info'])
def info_message(message):
    bot.send_message(message.chat.id, 'Этот бот предназначен для того, чтобы найти подходящие вакансии по твоей специальности и опыту работы')

def get_vacancies(keyword):
    url = "https://api.hh.ru/vacancies"
    params = {
        "text": keyword,
        "area": 1,  # Айди area, для примера сейчас только Москва
        "per_page": 10,  # Number of vacancies per page
    }
    headers = {
        "User-Agent": "Your User Agent",  # Replace with your User-Agent header
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()
        vacancies = data.get("items", [])
        for vacancy in vacancies:

            vacancy_id = vacancy.get("id")
            vacancy_title = vacancy.get("name")
            vacancy_url = vacancy.get("alternate_url")
            company_name = vacancy.get("employer", {}).get("name")
            print(f"ID: {vacancy_id}\nTitle: {vacancy_title}\nCompany: {company_name}\nURL: {vacancy_url}\n")
    else:

        print(f"Request failed with status code: {response.status_code}")

bot.polling(non_stop=True)