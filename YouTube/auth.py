import json
from typing import Optional
import requests


class YouTubeAuth:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    def try_obtain_token(self, code: str, redirect_uri: str) -> (int, Optional[tuple[str, str]]):
        """
        Try to obtain an access token using an OAuth code.
        :param code: The code obtained by the user's login flow.
        :param redirect_uri: The redirect uri of the token process.
        :return: A tuple containing the status code of the call, and optionally the access and refresh tokens (in that
        order) if the call was successful.
        """
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        })
        # return YouTube token and refresh token if successful
        if r.status_code == 200:
            data = json.loads(r.text)
            return 200, (data["access_token"], data["refresh_token"])
        else:
            return r.status_code, None

    def try_refresh_youtube_token(self, refresh_token: str) -> (int, Optional[tuple[str, str]]):
        """
        Tries to use a refresh token to get a new access token.
        :param refresh_token: The refresh token.
        :return: A tuple containing the status code of the call, and optionally the new access and refresh tokens
        (in that order) if the call was successful.
        """
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        # return new auth data if successful
        if r.status_code == 200:
            data = json.loads(r.text)
            return 200, (data["access_token"], refresh_token)
        else:
            return r.status_code, None

    @staticmethod
    def try_get_username(token: str) -> (int, Optional[str]):
        """
        Tries to get the YouTube e-mail for a given access token.
        :param token: The access token of the user.
        :return: A tuple containing the status code of the call, and optionally the e-mail if the call was successful.
        """
        headers = {'Authorization': 'Bearer ' + token}
        url = 'https://www.googleapis.com/oauth2/v3/userinfo'
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            data = json.loads(r.text)
            return 200, data['email']
        else:
            return r.status_code, None

    def get_auth_url(self, redirect_uri: str):
        """
        Gets the URL to redirect the user to for the login flow.
        :param redirect_uri: The redirect uri of the token process.
        :return: The URL to redirect the user to.
        """
        url = f"""https://accounts.google.com/o/oauth2/auth?""" \
              f"""client_id={self.client_id}""" \
              f"""&response_type=code""" \
              f"""&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube.readonly%20https%3A%2F%2Fwww.googleapis
              .com%2Fauth%2Fuserinfo.email%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Foffline""" \
              f"""&access_type=offline""" \
              f"""&prompt=consent""" \
              f"""&redirect_uri={redirect_uri}"""
        return url
