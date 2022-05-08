import logging
import os
import time
import requests
import sys
import http

from telegram import Bot
from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s, %(levelname)s, %(message)s',
    handlers=logging.StreamHandler(sys.stdout)
)


def send_message(bot, message):
    """Отправляет сообщение в телеграм"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        logging.info('сообщение отправлено')
    except Exception as error:
        logging.error(f'сбой отправки сообщения {error}')
    return bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Делает запрос к API-сервису"""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != HTTPStatus.OK:
        logging.error('страница не доступна')
        raise http.exceptions.HTTPError()
    return response.json()


def check_response(response):
    """"Проверяет ответ API на корректность.Ожидается JSON формат"""
    if not isinstance(response, dict):
        logging.error('формат ответа отличается от ожидаемого')
        raise TypeError('формат ответа отличается от ожидаемого')
    homeworks = response.get('homeworks')
    if homeworks is None:
        logging.error('ответ API не содержит ключ homeworks')
        raise KeyError('ответ API не содержит ключ homeworks')
    if isinstance(homeworks, list):
        if homeworks == []:
            logging.debug('в ответе нет новых статусов')
    else:
        logging.error('тип значения дз отличается от ожидаемого')
        raise TypeError('тип значения дз отличается от ожидаемого')
    return homeworks


def parse_status(homework):
    """"Извлекает из информации о конкретной работе статус ее проверки"""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if 'homework_name' not in homework:
        logging.error('Неверный статус проверки домашней работы')
        raise KeyError('Не найден ключ homeworks')
    if 'status' not in homework:
        logging.error('Неверный статус проверки домашней работы')
        raise KeyError('Не найден ключ homeworks')
    verdict = HOMEWORK_STATUSES[homework_status]
    if homework_status not in HOMEWORK_STATUSES:
        logging.error('Неверный статус проверки домашней работы')
        raise KeyError('Не найден ключ homeworks')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """"Проверяет доступность переменных окружения"""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        logging.critical('потерялась переменная окружения')
        return True
    return False


def main():
    """Основная логика работы бота."""
    current_timestamp = int(time.time())
    bot = Bot(token=TELEGRAM_TOKEN)
    if check_tokens() is False:
        raise ValueError('Не найден токен для запуска')
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logging.debug('нет обновлений по домашней работе')
            else:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            current_timestamp = response.get('current_date', current_timestamp)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            current_timestamp = int(time.time())
            time.sleep(RETRY_TIME)
        else:
            logging.error(message)


if __name__ == '__main__':
    main()
