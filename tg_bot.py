import requests
import pprint
from environs import Env

env = Env()
env.read_env()
pp = pprint.PrettyPrinter(indent=4)

headers = {
    'Authorization': f'Bearer {env.str("ACCESS_TOKEN")}',
}

products_url = 'https://api.moltin.com/oauth/access_token'
response = requests.get('https://api.moltin.com/pcm/products', headers=headers)

pp.pprint(response.json())
