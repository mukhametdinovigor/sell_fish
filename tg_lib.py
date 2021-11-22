from datetime import datetime
import copy
from environs import Env

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from moltin_api import get_available_products, get_product_titles_and_ids, get_products_from_cart, get_access_token

env = Env()
env.read_env()

BUTTONS_IN_ROW = 2


def generate_inline_buttons(access_token):
    inline_buttons = []
    row_buttons = []
    available_products = get_available_products(access_token)
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


def display_card(access_token, update):
    keyboard = []
    products_from_cart = get_products_from_cart(access_token, update.effective_chat.id)
    product_ids = list(products_from_cart.keys())[:-1]
    product_titles = [product.split('\n')[0] for product in list(products_from_cart.values())[:-1]]
    for product_id, product_title in zip(product_ids, product_titles):
        keyboard.append([InlineKeyboardButton(f"Убрать из корзины {product_title}", callback_data=product_id)])
    keyboard.append([InlineKeyboardButton("В меню", callback_data='menu')])
    keyboard.append([InlineKeyboardButton("Оплатить", callback_data='pay')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.callback_query.message.reply_text(text='\n\n'.join(list(products_from_cart.values())), reply_markup=reply_markup)


def get_valid_token(context):
    access_token, expired_at = context.bot_data['token_attrs']
    now = datetime.now()
    timestamp_now = datetime.timestamp(now)
    if expired_at < timestamp_now:
        access_token, expired_at = get_access_token()
        context.bot_data['token_attrs'] = access_token, expired_at
    return access_token, expired_at
