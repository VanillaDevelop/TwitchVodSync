import json
import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("TWITCH_ID")
client_secret = os.getenv("TWITCH_SECRET")


def try_get_username(token: str) -> (int, Optional[str]):
    """
    Tries to get the twitch username for a given access token
    :param token: The access token of the user
    :return: A tuple containing the status code of the call, and optionally the name if the call was successful
    """
    headers = {'Authorization': 'Bearer ' + token, 'Client-ID': client_id}
    url = 'https://api.twitch.tv/helix/users'
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data = json.loads(r.text)
        return 200, data['data'][0]['login']
    else:
        return r.status_code, None


def try_refresh_twitch_token(refresh_token: str) -> (int, Optional[tuple[str, str]]):
    """
    Tries to use a refresh token to get a new access token
    :param refresh_token: The refresh token
    :return: A tuple containing the status code of the call, and optionally the new access and refresh tokens (in that
    order) if the call was successful.
    """
    r = requests.post("https://id.twitch.tv/oauth2/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    # return new auth data if successful
    if r.status_code == 200:
        data = json.loads(r.text)
        return 200, (data["access_token"], data["refresh_token"])
    else:
        return r.status_code, None


def try_obtain_token(code: str, redirect_uri: str) -> (int, Optional[tuple[str, str]]):
    """
    Try to obtain an access token using an OAuth code.
    :param code: The code obtained by the user's login flow.
    :param redirect_uri: The redirect uri of the token process.
    :return: A tuple containing the status code of the call, and optionally the access and refresh tokens (in that
    order) if the call was successful.
    """
    r = requests.post("https://id.twitch.tv/oauth2/token", data={
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    })
    # store twitch token and refresh token user auths
    if r.status_code == 200:
        data = json.loads(r.text)
        return 200, (data["access_token"], data["refresh_token"])
    else:
        return r.status_code, None

