import base64
import datetime
import json
from urllib.parse import urlencode
import requests

client_id = '345e6510e55a4627b22178f94e700807'
client_secret = '1c71f278e1b6437eaaa0fd09bc5364a4'

class SpotifyAPI(object):
    access_token = None
    access_token_expires = datetime.datetime.now()
    access_token_did_expire = True
    client_id = None
    client_secret = None
    token_url = "https://accounts.spotify.com/api/token"

    def __init__(self, client_id, client_secret, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret

    def get_client_credentials(self):
        """
        Returns a base64 encoded string
        """
        client_id = self.client_id
        client_secret = self.client_secret
        if client_secret == None or client_id == None:
            raise Exception("You must set client_id and client_secret")
        client_creds = f"{client_id}:{client_secret}"
        client_creds_b64 = base64.b64encode(client_creds.encode())
        return client_creds_b64.decode()

    def get_token_headers(self):
        client_creds_b64 = self.get_client_credentials()
        return {
            "Authorization": f"Basic {client_creds_b64}"
        }

    def get_token_data(self):
        return {
            "grant_type": "client_credentials"
        }

    def perform_auth(self):
        token_url = self.token_url
        token_data = self.get_token_data()
        token_headers = self.get_token_headers()
        r = requests.post(token_url, data=token_data, headers=token_headers)
        if r.status_code not in range(200, 299):
            raise Exception("Could not authenticate client.")
            # return False
        data = r.json()
        now = datetime.datetime.now()
        access_token = data['access_token']
        expires_in = data['expires_in']  # seconds
        expires = now + datetime.timedelta(seconds=expires_in)
        self.access_token = access_token
        self.access_token_expires = expires
        self.access_token_did_expire = expires < now
        return True


spotify = SpotifyAPI(client_id, client_secret)
spotify.perform_auth()
access_token = spotify.access_token


headers = {
    "Authorization": f"Bearer {access_token}"
}

BASE_URL = 'https://api.spotify.com/v1/'

user_input = input("enter your search:")

data1 = urlencode({"q": user_input, "type": "artist"})
endpoint = BASE_URL + "search"
lookupURL = f"{endpoint}?{data1}"
r1 = requests.get(lookupURL, headers=headers)
r1_json = r1.json()
print(r1_json)
#for artist in r1_json["items"]:
    #print(artist['name'], ' --- ', artist['id'])
artist_id = '36QJpDe2go2KgaRleHCDTp'


r = requests.get(BASE_URL + 'artists/' + artist_id + '/albums',
                 headers=headers,
                 params={'include_groups': 'album', 'limit': 50})
d = r.json()
print(d)
#for album in d['items']:
    #print(album['name'], ' --- ', album['release_date'])


