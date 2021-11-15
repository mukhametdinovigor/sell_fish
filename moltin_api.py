import requests
import pprint
from environs import Env

env = Env()
env.read_env()
pp = pprint.PrettyPrinter(indent=4)


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


def get_available_products(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    products_url = 'https://api.moltin.com/v2/products'
    response = requests.get(products_url, headers=headers)
    response.raise_for_status()
    return response.json()


def add_product_to_cart(access_token, product_id):
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }
    payload = {"data":
                   {"id": product_id,
                    "type": "cart_item",
                    "quantity": 1}
               }
    response = requests.post('https://api.moltin.com/v2/carts/1234/items', headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


def get_products_from_cart(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get('https://api.moltin.com/v2/carts/1234/items', headers=headers)
    response.raise_for_status()
    return response.json()


def get_cart(access_token):
    headers = {
        'Authorization': f'Bearer {access_token}',
    }
    response = requests.get('https://api.moltin.com/v2/carts/1234', headers=headers)
    response.raise_for_status()
    return response.json()


def main():
    access_token = get_access_token()  # TODO сделать проверку кончился ли токен, живет 3600 сек
    available_products = get_available_products(access_token)
    product_id = 'f6bac3f3-b54d-4467-9567-240a0339b996'
    pp.pprint(available_products)
    pp.pprint(get_cart(access_token))
    pp.pprint(add_product_to_cart(access_token, product_id))
    pp.pprint(get_products_from_cart(access_token))


if __name__ == main():
    main()
