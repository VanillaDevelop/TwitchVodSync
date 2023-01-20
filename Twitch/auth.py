import json
from typing import Optional
import requests


class TwitchAuth:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    def try_get_username(self, token: str) -> (int, Optional[str]):
        """
        Tries to get the Twitch username for a given access token.
        :param token: The access token of the user.
        :return: A tuple containing the status code of the call, and optionally the name if the call was successful.
        """
        headers = {'Authorization': 'Bearer ' + token, 'Client-ID': self.client_id}
        url = 'https://api.twitch.tv/helix/users'
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = json.loads(r.text)
            return 200, data['data'][0]['login']
        else:
            return r.status_code, None

    def try_refresh_twitch_token(self, refresh_token: str) -> (int, Optional[tuple[str, str]]):
        """
        Tries to use a refresh token to get a new access token.
        :param refresh_token: The refresh token.
        :return: A tuple containing the status code of the call, and optionally the new access and refresh tokens
        (in that order) if the call was successful.
        """
        r = requests.post("https://id.twitch.tv/oauth2/token", data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        # return new auth data if successful
        if r.status_code == 200:
            data = json.loads(r.text)
            return 200, (data["access_token"], data["refresh_token"])
        else:
            return r.status_code, None

    def try_obtain_token(self, code: str, redirect_uri: str) -> (int, Optional[tuple[str, str]]):
        """
        Try to obtain an access token using an OAuth code.
        :param code: The code obtained by the user's login flow.
        :param redirect_uri: The redirect uri of the token process.
        :return: A tuple containing the status code of the call, and optionally the access and refresh tokens (in that
        order) if the call was successful.
        """
        r = requests.post("https://id.twitch.tv/oauth2/token", data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        # return twitch token and refresh token if successful
        if r.status_code == 200:
            data = json.loads(r.text)
            return 200, (data["access_token"], data["refresh_token"])
        else:
            return r.status_code, None

    def get_auth_url(self, state, redirect_url):
        """
        Get the URL to redirect the user to for the Twitch login flow.
        :param state: The state to pass to the login flow.
        :param redirect_url: The redirect URL to pass to the login flow.
        :return: The URL to redirect the user to.
        """
        url = f"""https://id.twitch.tv/oauth2/authorize?""" \
              f"""client_id={self.client_id}""" \
              f"""&response_type=code""" \
              f"""&state={state}""" \
              f"""&scope=""" \
              f"""&redirect_uri={redirect_url}"""
        return url

    def get_client_id(self):
        """
        Get the client ID of the Twitch app.
        :return: The client ID of the Twitch app.
        """
        return self.client_id
