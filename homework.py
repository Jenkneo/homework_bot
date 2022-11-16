import logging
import requests
import time
import telegram
import os
import exceptions
from dotenv import load_dotenv

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
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
    format='[%(asctime)s | %(levelname)s] - %(name)s: %(message)s'
)


def send_message(bot, message) -> None:
    """Отправка сообщения в телеграм."""
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logging.info('The message has been sent')


def get_api_answer(current_timestamp) -> dict:
    """Получение списка домашки через API."""
    # Получение ответа API
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}

    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        logging.debug(
            f'Practicum. Response received, status code {response.status_code}'
        )
    except Exception as error:
        raise exceptions.PracticumResponseException(
            f'Practicum server server is not respond. ERROR:{error}'
        )

    if response.status_code != 200:
        raise exceptions.PracticumResponseException(
            'Practicum response code is not 200'
        )

    return response.json()


def check_response(response):
    """Получение ответа от сервера Практикум."""
    try:
        homeworks = response["homeworks"]
    except Exception as error:
        raise exceptions.PracticumDataException(
            f'Practicum API returned incorrect data \n{error}'
        )

    if type(homeworks) is not list:
        raise exceptions.PracticumDataException(
            'Practicum API returned not a list'
        )

    return homeworks


def parse_status(homework) -> str:
    """Подготовка отправки ответа в ТГ."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")

    if not homework_status or not homework_name:
        raise KeyError(
            'Practicum API return incorrect data'
        )

    logging.debug(
        f'Homework {homework_name} status has changed to {homework_status}'
    )

    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Провекра существования токенов."""
    if TELEGRAM_TOKEN is None or PRACTICUM_TOKEN is None:
        logging.critical('Necessary tokens have not been received')
        return False
    if TELEGRAM_CHAT_ID is None:
        logging.critical('TELEGRAM_CHAT_ID have not been received')
        return False
    return True


def main():
    """Основная логика работы бота."""
    def sleep():
        logging.debug(f'Break {RETRY_TIME} seconds')
        time.sleep(RETRY_TIME)

    if not check_tokens():
        raise exceptions.TokenExpection(
            "The necessary tokens have not been received"
        )
    current_timestamp = int(time.time())
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    send_message(bot, "Бот запущен")
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if not homeworks:
                logging.debug(
                    'Homework status has not changed'
                )
                sleep()
                continue
            for homework in homeworks:
                message = parse_status(homework)
                send_message(bot, message)
            else:
                current_timestamp = int(time.time())
        except Exception as error:
            logging.error(f'{error}')
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        finally:
            sleep()


if __name__ == '__main__':
    main()
