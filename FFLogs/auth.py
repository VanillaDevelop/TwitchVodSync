import json
from typing import Optional
import requests


class FFLogsAuth:
    def __init__(self, client_id: str):
        self.client_id = client_id

    def try_refresh_fflogs_token(self, refresh_token: str) -> (int, Optional[tuple[str, str]]):
        """
        Tries to use a refresh token to get a new access token
        :param refresh_token: The refresh token
        :return: A tuple containing the status code of the call, and optionally the new access and refresh tokens
        (in that order) if the call was successful.
        """
        r = requests.post("https://www.fflogs.com/oauth/token", data={
            "client_id": self.client_id,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        # return new auth data if successful
        if r.status_code == 200:
            data = json.loads(r.text)
            return 200, (data["access_token"], data["refresh_token"])
        else:
            return r.status_code, None

    def try_obtain_token(self, code: str, verifier: str, redirect_uri: str) -> (int, Optional[tuple[str, str]]):
        """
        Try to obtain an access token using a PKCE exchange.
        :param code: The code obtained by the user's login flow.
        :param verifier: The verifier obtained from the PKCE flow.
        :param redirect_uri: The redirect uri of the token process.
        :return: A tuple containing the status code of the call, and optionally the access and refresh tokens (in that
        order) if the call was successful.
        """
        r = requests.post("https://www.fflogs.com/oauth/token", data={
            "client_id": self.client_id,
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

    def get_auth_url(self, challenge: str, state: str, redirect_uri: str) -> str:
        """
        Gets the URL to redirect the user to for the login flow.
        :param challenge: PKCE challenge.
        :param state: Internally stored state for this login process.
        :param redirect_uri: The redirect uri of the token process.
        :return: The URL to redirect the user to.
        """
        url = f"""https://www.fflogs.com/oauth/authorize?""" \
              f"""client_id={self.client_id}""" \
              f"""&code_challenge={challenge}""" \
              f"""&code_challenge_method=S256""" \
              f"""&state={state}""" \
              f"""&redirect_uri={redirect_uri}""" \
              f"""&response_type=code"""
        return url
