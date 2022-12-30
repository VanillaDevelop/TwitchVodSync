import asyncio
import os
import uuid

import requests
from dotenv import load_dotenv
from flask import redirect, url_for, session, request, Blueprint
from twitchAPI.helper import first

from DocStore.MongoDB import store_auth_keys
from twitchAPI import Twitch

load_dotenv()
twitch_routes = Blueprint('twitch', __name__)
host_url = os.getenv("HOST_URL")


@twitch_routes.route('/auth/twitch/challenge', methods=['POST'])
def auth_challenge():
    # when button to start twitch auth flow is clicked
    # generate state
    state = str(uuid.uuid4())
    session['twitch_state'] = state

    # call twitch auth url with state
    url = f"""https://id.twitch.tv/oauth2/authorize?""" \
          f"""client_id={os.getenv("TWITCH_ID")}""" \
          f"""&response_type=code""" \
          f"""&state={state}""" \
          f"""&scope=""" \
          f"""&redirect_uri={host_url + url_for("twitch.auth_verify")}"""
    return redirect(url)


@twitch_routes.route('/auth/twitch/verify')
async def auth_verify():
    if "twitch_state" not in session or "user" not in session:
        return redirect(host_url + url_for("home"))

    # when redirected from Twitch
    # compare state, request token with auth code provided
    if session["twitch_state"] == request.args.get('state'):
        r = requests.post("https://id.twitch.tv/oauth2/token", data={
            "client_id": os.getenv("TWITCH_ID"),
            "client_secret": os.getenv("TWITCH_SECRET"),
            "code": request.args.get('code'),
            "redirect_uri": host_url + url_for("twitch.auth_verify"),
            "grant_type": "authorization_code",
        })
        # store twitch token and refresh token user auths
        if r.status_code == 200:
            api = await Twitch(os.getenv("TWITCH_ID"), os.getenv("TWITCH_SECRET"))
            await api.set_user_authentication(r.json()["access_token"], [], r.json()["refresh_token"])
            response = await first(api.get_users())
            username = response.login

            session["auths"]["twitch"] = {
                "token": r.json()['access_token'],
                "refresh_token": r.json()['refresh_token'],
                "username": username
            }
        store_auth_keys(session["user"], session["auths"])

    del session["twitch_state"]
    return redirect(host_url + url_for("home"))


@twitch_routes.route('/auth/twitch/signout', methods=['POST'])
def auth_signout():
    # signout from twitch session => delete the data stored by the twitch auth flow, then return home
    if "user" in session and "twitch" in session["auths"] and request.method == "POST":
        del session["auths"]["twitch"]
        store_auth_keys(session["user"], session["auths"])
    return redirect(url_for('home'))
