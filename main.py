from telethon import TelegramClient, events, connection
from telethon.errors import SessionPasswordNeededError
from config import CREDENTIALS_FILE, SHEET_ID, SESSIONS_DIR, LOG_FILE, MESSAGES_FILE, CITES_FILE, ENVELOPE_TIME_BEFORE_SEND_MESSAGE, ENVELOPE_EMOJI, TRIGGER_GEO_ITERATION_CHANGE
from utils.sheets_manager import SheetsManager

import json
import os
import random
import logging
import asyncio
import time
import re, sys

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
sheet_manager = SheetsManager(cred_path=CREDENTIALS_FILE, sheet_id=SHEET_ID)

def load_json(path):
    if os.path.exists(path):
        with open(path, 'r') as file:
            return json.load(file)
    else:
        logger.error(f"Файл {path} не найден!")
        return None

def write_json(path, data):
    if os.path.exists(path):
        with open(path, 'w') as file:
            json.dump(data, file, ensure_ascii=False, indent=3)
    else:
        logger.error(f"Файл {path} не найден!")
        return None


def load_txt(path):
    with open(path, 'r', encoding='utf-8') as file:
        return [line.strip() for line in file.readlines()]


def generate_random_message(messages):
    random_message = random.choice(messages)
    return random_message


def generate_text_keyboard(keyboard):
    buttons = keyboard.rows
    result = []

    for row in buttons:
        for button in row.buttons:
            result.append(button.text)

    return result


async def like_people(phone, client):
    buttons_not_found = 0
    iterations = 0

    generated_messages = load_txt(MESSAGES_FILE)
    generated_cites = load_txt(CITES_FILE)

    while True:
        try:
            bot = await client.get_entity('leomatchbot')
            messages = await client.get_messages(bot, limit=1)
            reply_markup = messages[0].reply_markup

            if iterations >= TRIGGER_GEO_ITERATION_CHANGE:
                logger.info(f"({phone}) Превышено количество итераций для смены города, меняем город.")

                await client.send_message(bot, "/myprofile")
                time.sleep(2)
                # Изменить анкету
                await client.send_message(bot, "2")
                time.sleep(2)
                # Лет
                messages = await client.get_messages(bot, limit=1)
                await messages[0].click()
                time.sleep(2)
                # Пол
                messages = await client.get_messages(bot, limit=1)
                await messages[0].click()
                time.sleep(2)
                # Кто тебе интересен
                await client.send_message(bot, "Все равно")
                time.sleep(2)
                # Ввод города
                random_cite = generate_random_message(generated_cites)
                await client.send_message(bot, random_cite)
                time.sleep(2)
                # Имя
                messages = await client.get_messages(bot, limit=1)
                await messages[0].click()
                time.sleep(2)
                # О себе
                messages = await client.get_messages(bot, limit=1)
                await messages[0].click()
                time.sleep(2)
                # Фото
                messages = await client.get_messages(bot, limit=1)
                await messages[0].click()
                time.sleep(2)
                # Все ок
                messages = await client.get_messages(bot, limit=1)
                await messages[0].click()

                logger.info(f"({phone}) Город изменен на {random_cite}!")
                iterations = 0

                session_path = os.path.join(SESSIONS_DIR, f'{phone}.json')
                config = load_json(session_path)
                if config:
                    config["city"] = random_cite
                    write_json(session_path, config)


                continue

            if buttons_not_found >= 3:
                buttons_not_found = 0
                await client.send_message(bot, "/myprofile")
                messages = await client.get_messages(bot, limit=1)
                await messages[0].click()

            if not reply_markup:
                buttons_not_found += 1
                logger.error(
                    f"({phone}) Под последним сообщением не найдена клавиатура, делаем поиск по старым сообщениям")
                i = 1
                while True:
                    await asyncio.sleep(5)
                    messages = await client.get_messages(bot, limit=i)
                    reply_markup = messages[-1].reply_markup
                    if not reply_markup:
                        i += 1
                    else:
                        break

            keyboard_text = generate_text_keyboard(reply_markup)
            if reply_markup:
                logger.info(f"({phone}) ({keyboard_text}) Клавиатура найдена!")

            found = False
            buttons = reply_markup.rows

            for row in buttons:
                for button in row.buttons:

                    if any(char in item for item in button.text for char in ENVELOPE_EMOJI if char.strip()):

                        await client.send_message(bot, button.text)
                        found = True
                        logger.info(f"Нажата кнопка {button.text}")
                        random_message = generate_random_message(
                            generated_messages)
                        logger.info(
                            f"Спим прежде чем отправить сообщение: {ENVELOPE_TIME_BEFORE_SEND_MESSAGE} секунд")
                        time.sleep(ENVELOPE_TIME_BEFORE_SEND_MESSAGE)
                        await client.send_message(bot, random_message)
                        logger.info(f"Отправлено сообщение: {random_message}")

                        break

                if not found:
                    for button in row.buttons:
                        if button.text == "❤️":
                            await client.send_message(bot, button.text)
                            found = True
                            logger.info("Нажата кнопка ❤️")
                            break

                if found:
                    buttons_not_found = 0
                    break

            if not found:
                logger.info(
                    f"({phone})({keyboard_text}) Не удалось нажать ни на одну кнопку, нажимаем на первую")
                await messages[0].click()

            iterations += 1
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(
                f"({phone}) Ошибка при нажатии на конвертик, продолжаем попытки: {e}")



async def process_mutual_sympathy_messages(event, phone, client):
    session_path = os.path.join(SESSIONS_DIR, f'{phone}.json')
    config = load_json(session_path)

    if event.message.entities:
        entity = event.message.entities[0]

        if hasattr(entity, 'user_id'):
            user_id = entity.user_id
            user = await client.get_entity(user_id)
            username = user.username if user.username else user.first_name

            sheet_manager.mutual_sympathy(city=config.get("city"), account=phone, username=username)
            logger.info(f"Взаимная симпатия отправлено в таблицу {phone}: {event.raw_text}")
        elif hasattr(entity, 'url'):
            url = entity.url
            sheet_manager.mutual_sympathy(city=config.get("city"), account=phone, username=url)
            logger.info(f"Взаимная симпатия отправлено в таблицу {phone}: {event.raw_text}")

        else:
            logger.warning(f"Сущность не содержит user_id или url: {entity}")
    else:
        logger.warning(f"В сообщении не найдены сущности: {event.raw_text}")


async def process_session(phone):
    session_path = os.path.join(SESSIONS_DIR, f'{phone}.json')
    config = load_json(session_path)
    if not config:
        return


    api_id = config.get('app_id')
    api_hash = config.get('app_hash')
    proxy = config.get('proxy')
    proxy_type = config.get('proxy_type')

    if (proxy):
        proxy = tuple(proxy)

    if (proxy_type == "MTPROTO"):
        client = TelegramClient(os.path.join(
            SESSIONS_DIR, phone), api_id, api_id, proxy=proxy, connection=connection.ConnectionTcpMTProxyRandomizedIntermediate)
    elif (not proxy_type):
        client = TelegramClient(os.path.join(
            SESSIONS_DIR, phone), api_id, api_id)
    else:
        client = TelegramClient(os.path.join(
            SESSIONS_DIR, phone), api_id, api_id, proxy=proxy)

    try:
        await client.start(phone=phone)
        if await client.is_user_authorized():
            logger.info(f"Успешная авторизация для {phone}")
        else:
            logger.error(f"Не удалось авторизоваться для {phone}")

        @client.on(events.NewMessage(pattern='Отлично! Надеюсь хорошо проведете время'))
        async def handle_favorite_message(event):
            await process_mutual_sympathy_messages(event, phone, client)

        @client.on(events.NewMessage(pattern='Есть взаимная симпатия! Начинай общаться'))
        async def handle_favorite_message(event):
            await process_mutual_sympathy_messages(event, phone, client)

        await like_people(phone, client)

    except SessionPasswordNeededError:
        logger.error(f"Необходим пароль для двухфакторной аутентификации для {phone}")
    except Exception as e:
        logger.error(f"Ошибка для {phone}: {e}")
    finally:
        await client.disconnect()

async def main():
    phones = [f.split('.')[0] for f in os.listdir(SESSIONS_DIR) if f.endswith('.session')]
    if not phones:
        logger.error("Не найдено ни одной сессии в папке.")
        return

    tasks = [asyncio.create_task(process_session(phone)) for phone in phones]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("bye :)")
