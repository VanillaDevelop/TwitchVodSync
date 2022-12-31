import json
import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("FFLOGS_CLIENT_ID")


def try_refresh_fflogs_token(refresh_token: str) -> (int, Optional[tuple[str, str]]):
    """
    Tries to use a refresh token to get a new access token
    :param refresh_token: The refresh token
    :return: A tuple containing the status code of the call, and optionally the new access and refresh tokens (in that
    order) if the call was successful.
    """
    r = requests.post("https://www.fflogs.com/oauth/token", data={
        "client_id": client_id,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    # return new auth data if successful
    if r.status_code == 200:
        data = json.loads(r.text)
        return 200, (data["access_token"], data["refresh_token"])
    else:
        return r.status_code, None


def try_obtain_token(code: str, verifier: str, redirect_uri: str) -> (int, Optional[tuple[str, str]]):
    """
    Try to obtain an access token using a PKCE exchange.
    :param code: The code obtained by the user's login flow.
    :param verifier: The verifier obtained from the PKCE flow.
    :param redirect_uri: The redirect uri of the token process.
    :return: A tuple containing the status code of the call, and optionally the access and refresh tokens (in that
    order) if the call was successful.
    """
    r = requests.post("https://www.fflogs.com/oauth/token", data={
        "client_id": client_id,
        "code_verifier": verifier,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code": code
    })
    # return fflogs token and refresh token if successful
    if r.status_code == 200:
        data = json.loads(r.text)
        return 200, (data["access_token"], data["refresh_token"])
    else:
        return r.status_code, None
