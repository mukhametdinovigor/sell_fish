import copy
import logging

from environs import Env
import redis
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Filters, Updater
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

from moltin_api import get_access_token, get_available_products, get_product_titles_and_ids, get_product_by_id, \
    get_product_details, get_product_image_url

env = Env()
env.read_env()
_database = None

ACCESS_TOKEN = get_access_token()


def generate_inline_buttons():
    inline_buttons = []
    row_buttons = []
    available_products = get_available_products(ACCESS_TOKEN)
    product_titles_and_ids = get_product_titles_and_ids(available_products)
    for product, product_id in product_titles_and_ids.items():
        row_buttons.append(InlineKeyboardButton(product, callback_data=product_id))
        if len(row_buttons) == 2:  # TODO вынести количество кнопок в отдельную переменную
            inline_buttons.append(copy.deepcopy(row_buttons))
            row_buttons.clear()
        else:
            continue
    inline_buttons.append(row_buttons)
    return inline_buttons


def start(update, context):
    keyboard = generate_inline_buttons()
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(text='Привет!', reply_markup=reply_markup)
    return "HANDLE_MENU"


def handle_menu(update, context):
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Назад', callback_data='_')]])
    product_id = update.callback_query.data
    product = get_product_by_id(ACCESS_TOKEN, product_id)
    product_details = '\n\n'.join(get_product_details(product))
    image_id = product['data']['relationships']['main_image']['data']['id']
    image_url = get_product_image_url(ACCESS_TOKEN, image_id)
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=image_url,
        caption=product_details,
        reply_markup=reply_markup
    )
    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=update.callback_query.message.message_id
    )
    return "HANDLE_DESCRIPTION"


def handle_description(update, context):
    keyboard = generate_inline_buttons()
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(text='Привет!', reply_markup=reply_markup)
    return "HANDLE_MENU"


def handle_users_reply(update, context):
    db = get_database_connection()
    if update.message:
        user_reply = update.message.text
        chat_id = update.message.chat_id
    elif update.callback_query:
        user_reply = update.callback_query.data
        chat_id = update.callback_query.message.chat_id
    else:
        return
    if user_reply == '/start':
        user_state = 'START'
    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
    }
    state_handler = states_functions[user_state]
    try:
        next_state = state_handler(update, context)
        db.set(chat_id, next_state)
    except Exception as err:
        print(err)


def get_database_connection():
    global _database
    if _database is None:
        database_password = env.str("REDIS_PASSWORD")
        database_host = env.str("REDIS_ENDPOINT")
        database_port = env.str("REDIS_PORT")
        _database = redis.Redis(host=database_host, port=database_port, password=database_password)
    return _database


if __name__ == '__main__':
    token = env.str("TG_TOKEN")
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
