import os
import secrets
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from twinfield import TwinfieldApi
from oauthlib.oauth2 import WebApplicationClient
from http_server import HTTPServer

load_dotenv()

CLIENT_ID = os.environ["TWINFIELD_CLIENT_ID"]
CLIENT_SECRET = os.environ["TWINFIELD_CLIENT_SECRET"]
REDIRECT_URI = os.environ["TWINFIELD_REDIRECT_URI"]
AUTHORIZATION_URL = os.environ["TWINFIELD_AUTHORIZATION_URL"]
TOKEN_URL = os.environ["TWINFIELD_TOKEN_URL"]

httpd, address = HTTPServer()

scope = [
    "openid",
    "twf.user",
    "twf.organisation",
    "twf.organisationUser",
    "offline_access",
]

client = WebApplicationClient(CLIENT_ID)
authorization_url = client.prepare_request_uri(
    AUTHORIZATION_URL,
    scope=scope,
    redirect_uri=REDIRECT_URI,
    nonce=secrets.token_urlsafe(),
)

print(f"Please go to {authorization_url} and authorize access.")
# callback_url = input("Enter the full callback URL: ")
# params = client.parse_request_uri_response(callback_url)
authorization_code = input("Enter the received authorization code: ")

auth = HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
# body = client.prepare_request_body(code=params["code"], redirect_uri=REDIRECT_URI)
body = client.prepare_request_body(code=authorization_code, redirect_uri=REDIRECT_URI)

response = requests.post(TOKEN_URL, data=body, auth=auth)
token = client.parse_request_body_response(response.text)
print(token)

os.environ["TWINFIELD_ACCESS_TOKEN"] = str(client.access_token)
os.environ["TWINFIELD_REFRESH_TOKEN"] = str(client.refresh_token)

print(f"Access token: {client.access_token}")

tw = TwinfieldApi()
print(tw.__dict__)

print(tw.organisation)

print(tw.list_offices())
print(tw.determine_cluster())
print(tw.dimensions("BAS").columns)
# print(tw.dimensions("CRD").columns)
print(tw.dimensions("DEB").columns)
print(type(tw.dimensions("DEB")))
for i, deb in tw.dimensions("DEB").iterrows():
    print(
        deb["dimension.code"],
        deb["dimension.name"],
    )
