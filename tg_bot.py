import copy
import logging

import redis
from environs import Env
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler
from telegram.ext import Filters, Updater

from moltin_api import get_access_token, get_available_products, get_product_titles_and_ids, get_product_by_id, \
    get_product_details, get_product_image_url, add_product_to_cart, get_products_from_cart, delete_cart_items, delete_cart, \
    create_customer
from tg_logs_handler import TelegramLogsHandler

logger = logging.getLogger('Logger')
env = Env()
env.read_env()
_database = None

BUTTONS_IN_ROW = 2


def generate_inline_buttons():
    inline_buttons = []
    row_buttons = []
    available_products = get_available_products()
    product_titles_and_ids = get_product_titles_and_ids(available_products)
    for product, product_id in product_titles_and_ids.items():
        row_buttons.append(InlineKeyboardButton(product, callback_data=product_id))
        if len(row_buttons) == BUTTONS_IN_ROW:
            inline_buttons.append(copy.deepcopy(row_buttons))
            row_buttons.clear()
        else:
            continue
    inline_buttons.append(row_buttons)
    return inline_buttons


def display_card(update):
    keyboard = []
    products_from_cart = get_products_from_cart(update.effective_chat.id)
    product_ids = list(products_from_cart.keys())[:-1]
    product_titles = [product.split('\n')[0] for product in list(products_from_cart.values())[:-1]]
    for product_id, product_title in zip(product_ids, product_titles):
        keyboard.append([InlineKeyboardButton(f"Убрать из корзины {product_title}", callback_data=product_id)])
    keyboard.append([InlineKeyboardButton("В меню", callback_data='menu')])
    keyboard.append([InlineKeyboardButton("Оплатить", callback_data='pay')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(text='\n\n'.join(list(products_from_cart.values())), reply_markup=reply_markup)


def start(update, context):
    keyboard = generate_inline_buttons()
    keyboard.append([InlineKeyboardButton('Корзина', callback_data='cart')])
    context.user_data['keyboard'] = keyboard
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        update.callback_query.message.reply_text(text='Вы можете выбрать товар:', reply_markup=reply_markup)
        return "HANDLE_MENU"
    else:
        update.message.reply_text(text='Вы можете выбрать товар:', reply_markup=reply_markup)
        return "HANDLE_MENU"


def handle_menu(update, context):
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton('1 кг', callback_data=1), InlineKeyboardButton('5 кг', callback_data=5), InlineKeyboardButton('10 кг', callback_data=10)],
        [InlineKeyboardButton('Назад', callback_data='_')],
        [InlineKeyboardButton('Корзина', callback_data='cart')]
    ])

    product_id = update.callback_query.data
    context.user_data['product_id'] = product_id
    product = get_product_by_id(product_id)
    product_details = get_product_details(product)
    image_id = product['data']['relationships']['main_image']['data']['id']
    image_url = get_product_image_url(image_id)
    context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=image_url,
        caption='\n\n'.join(product_details),
        reply_markup=reply_markup
    )
    context.bot.delete_message(
        chat_id=update.effective_chat.id,
        message_id=update.callback_query.message.message_id
    )
    return "HANDLE_DESCRIPTION"


def handle_description(update, context):
    keyboard = context.user_data['keyboard']
    reply_markup = InlineKeyboardMarkup(keyboard)
    product_id = context.user_data['product_id']
    if update.callback_query.data.isdigit():
        quantity = int(update.callback_query.data)
        add_product_to_cart(product_id, update.effective_chat.id, quantity)
        return "HANDLE_DESCRIPTION"
    else:
        update.callback_query.message.reply_text(text='Вы можете выбрать товар:', reply_markup=reply_markup)
        return "HANDLE_MENU"


def handle_cart(update, context):
    if update.callback_query.data == 'menu':
        keyboard = context.user_data['keyboard']
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.message.reply_text(text='Вы можете выбрать товар:', reply_markup=reply_markup)
        return "HANDLE_MENU"
    elif update.callback_query.data == 'cart':
        display_card(update)
        return 'HANDLE_CART'
    else:
        delete_cart_items(update.effective_chat.id, update.callback_query.data)
        display_card(update)
        return 'HANDLE_CART'


def waiting_email(update, context):
    if update.message:
        reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton('Заново', callback_data='again')]])
        try:
            create_customer(update.message.text)
        except Exception as err:
            if '422 Client Error' in str(err):
                update.message.reply_text(text='Неверная почта, попробуйте ещё раз')
                return "WAITING_EMAIL"
        delete_cart(update.effective_chat.id)
        update.message.reply_text(text=f'Вы прислали эту почту: {update.message.text}', reply_markup=reply_markup)
        return "START"

    else:
        update.callback_query.message.reply_text(text='Для оформления заказа, отправьте свою почту')
        return "WAITING_EMAIL"


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
    elif user_reply == 'cart':
        user_state = 'HANDLE_CART'
    elif user_reply == 'pay':
        user_state = 'WAITING_EMAIL'

    else:
        user_state = db.get(chat_id).decode("utf-8")

    states_functions = {
        'START': start,
        'HANDLE_MENU': handle_menu,
        'HANDLE_DESCRIPTION': handle_description,
        'HANDLE_CART': handle_cart,
        'WAITING_EMAIL': waiting_email,
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
    chat_id = env.str('CHAT_ID')
    token = env.str("TG_TOKEN")
    updater = Updater(token)
    logger.setLevel(logging.WARNING)
    logger.addHandler(TelegramLogsHandler(chat_id))
    logger.warning('TG_Fish_Bot запущен.')
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CallbackQueryHandler(handle_users_reply))
    dispatcher.add_handler(MessageHandler(Filters.text, handle_users_reply))
    dispatcher.add_handler(CommandHandler('start', handle_users_reply))
    updater.start_polling()
