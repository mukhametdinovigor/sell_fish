import requests
from environs import Env

env = Env()
env.read_env()


class WrongEmail(Exception):
    pass


def get_access_token():
    client_credentials = {
        'client_id': env.str('CLIENT_ID'),
        'client_secret': env.str('CLIENT_SECRET'),
        'grant_type': 'client_credentials'
    }
    moltin_url = 'https://api.moltin.com/oauth/access_token'
    response = requests.post(moltin_url, data=client_credentials)
    response.raise_for_status()
    return response.json().get('access_token')


def get_available_products():
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    products_url = 'https://api.moltin.com/v2/products'
    response = requests.get(products_url, headers=headers)
    response.raise_for_status()
    return response.json()


def add_product_to_cart(product_id, chat_id, quantity):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    payload = {"data":
                   {"id": product_id,
                    "type": "cart_item",
                    "quantity": quantity}
               }
    response = requests.post(f'https://api.moltin.com/v2/carts/{chat_id}/items', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_products_from_cart(chat_id):
    access_token = get_access_token()
    products_from_cart = dict()
    total_price = 0

    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/carts/{chat_id}/items', headers=headers)
    response.raise_for_status()
    products = response.json()

    for product in products['data']:
        product_amount = product['value']['amount'] / 100
        total_price += product_amount
        products_from_cart[product['id']] = '\n'.join([product['name'],
                                                       product['description'],
                                                       f"${product['unit_price']['amount'] / 100} per kg",
                                                       f"${product['quantity']}kg in cart for ${product_amount}",
                                                       ])
    products_from_cart['total'] = f"Total: ${total_price}"
    return products_from_cart


def get_product_by_id(product_id):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    product_endpoint = f'https://api.moltin.com/v2/products/{product_id}'
    response = requests.get(product_endpoint, headers=headers)
    response.raise_for_status()
    return response.json()


def get_product_details(product):
    product_details = [
        product["data"]["name"],
        f'{product["data"]["meta"]["display_price"]["with_tax"]["formatted"]} per kg\n'
        f'{product["data"]["meta"]["stock"]["level"]}kg in stock',

        product["data"]["description"]
    ]
    return product_details


def get_cart(chat_id):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/carts/{chat_id}', headers=headers)
    response.raise_for_status()
    return response.json()


def get_product_image_url(image_id):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get(f'https://api.moltin.com/v2/files/{image_id}', headers=headers)
    response.raise_for_status()
    return response.json()['data']['link']['href']


def delete_cart(chat_id):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.delete(f'https://api.moltin.com/v2/carts/{chat_id}', headers=headers)
    response.raise_for_status()
    return response.text


def delete_cart_items(chat_id, product_id):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.delete(f'https://api.moltin.com/v2/carts/{chat_id}/items/{product_id}', headers=headers)
    response.raise_for_status()
    return response.text


def create_customer(email):
    access_token = get_access_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    payload = {"data":
                   {"type": "customer",
                    "name": email,
                    "email": email
                    }
               }
    response = requests.post('https://api.moltin.com/v2/customers', headers=headers, json=payload)
    if response.status_code == 422:
        raise WrongEmail
    return response.json()


def get_product_titles_and_ids(products):
    product_titles_and_ids = dict()
    for product in products['data']:
        product_titles_and_ids[product['name']] = product['id']
    return product_titles_and_ids
