import os
import uuid

import requests
from dotenv import load_dotenv
from flask import redirect, url_for, session, request, Blueprint

from DocStore.MongoDB import store_auth_keys

from Twitch import twitch

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
    if "twitch_state" not in session:
        return redirect(host_url + url_for("home"))

    state = request.args.get('state')
    code = request.args.get('code')
    state_matches = session["twitch_state"] == state
    del session["twitch_state"]

    if "user" not in session or not code or not state_matches:
        return redirect(host_url + url_for("home"))

    # when redirected from Twitch
    status_token, data = twitch.try_obtain_token(code, host_url + url_for("twitch.auth_verify"))
    # store twitch token and refresh token user auths if successful
    if status_token == 200:
        status_name, name = twitch.try_get_username(data[0])
        if status_name == 200:
            session["auths"]["twitch"] = {
                "token": data[0],
                "refresh_token": data[1],
                "username": name
            }
    store_auth_keys(session["user"], session["auths"])
    return redirect(host_url + url_for("home"))


@twitch_routes.route('/auth/twitch/refresh')
async def auth_refresh():
    if "twitch_refresh" not in session:
        return redirect(host_url + url_for("home"))
    del session["twitch_refresh"]

    if "user" not in session or "twitch" not in session["auths"]:
        return redirect(host_url + url_for("home"))

    status_token, data = twitch.try_refresh_twitch_token(refresh_token=session["auths"]["twitch"]["refresh_token"])
    # store twitch token and refresh token user auths if successful
    if status_token == 200:
        status_name, name = twitch.try_get_username(data[0])
        if status_name == 200:
            session["auths"]["twitch"] = {
                "token": data[0],
                "refresh_token": data[1],
                "username": name
            }
    else:
        # otherwise delete no longer functioning auth (user must manually reauthorize)
        del session["auths"]["twitch"]

    store_auth_keys(session["user"], session["auths"])
    return redirect(host_url + url_for("home"))


@twitch_routes.route('/auth/twitch/signout', methods=['POST'])
def auth_signout():
    # signout from twitch session => delete the data stored by the twitch auth flow, then return home
    if "user" in session and "twitch" in session["auths"] and request.method == "POST":
        del session["auths"]["twitch"]
        store_auth_keys(session["user"], session["auths"])
    return redirect(url_for('home'))
