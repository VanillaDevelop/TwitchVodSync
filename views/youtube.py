import os
from dotenv import load_dotenv
from flask import redirect, url_for, session, request, Blueprint, current_app
from DocStore.MongoDB import MongoDBConnection
from YouTube import auth

load_dotenv()
youtube_routes = Blueprint('youtube', __name__)
host_url = os.getenv("HOST_URL")

client_id = os.getenv("YOUTUBE_ID")


@youtube_routes.route('/auth/youtube/challenge', methods=['POST'])
def auth_challenge():
    # when button to start YouTube auth flow is clicked

    # call YouTube auth url with state
    url = f"""https://accounts.google.com/o/oauth2/auth?""" \
          f"""client_id={client_id}""" \
          f"""&response_type=code""" \
          f"""&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fyoutube.readonly%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email%20https%3A%2F%2Fwww.googleapis.com%2Fauth%2Foffline""" \
          f"""&access_type=offline""" \
          f"""&prompt=consent""" \
          f"""&redirect_uri={host_url + url_for("youtube.auth_verify")}"""
    return redirect(url)


@youtube_routes.route('/auth/youtube/verify')
def auth_verify():
    if "user" not in session or "auths" not in session:
        return redirect(host_url + url_for("index"))

    code = request.args.get('code')
    if not code:
        return redirect(host_url + url_for("home"))

    # request token with verifier and provided auth code
    status_code, data = auth.try_obtain_token(code, host_url + url_for("youtube.auth_verify"))

    # if successful, store access token for user and get his username and uid, then return to home
    if status_code == 200:
        status_name, name = auth.try_get_username(data[0])
        if status_name == 200:
            session["auths"]["youtube"] = {
                "token": data[0],
                "refresh_token": data[1],
                "username": name
            }
            current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])

    return redirect(url_for('home'))


@youtube_routes.route('/auth/youtube/signout', methods=['POST'])
def auth_signout():
    # signout from youtube session => delete the data stored by the twitch auth flow, then return home
    if "user" in session and "auths" in session and "youtube" in session["auths"]:
        del session["auths"]["youtube"]
        current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
    return redirect(url_for('home'))


@youtube_routes.route('/auth/youtube/refresh', methods=['POST'])
async def auth_refresh():
    # don't allow users to arbitrarily request token refreshes
    if "youtube_refresh" not in session:
        return redirect(host_url + url_for("home"))
    del session["youtube_refresh"]

    if "user" not in session or "auths" not in session or "youtube" not in session["auths"]:
        return redirect(host_url + url_for("home"))

    status_token, data = auth.try_refresh_youtube_token(refresh_token=session["auths"]["youtube"]["refresh_token"])
    # store youtube token and refresh token user auths if successful
    if status_token == 200:
        status_name, name = auth.try_get_username(data[0])
        if status_name == 200:
            session["auths"]["youtube"] = {
                "token": data[0],
                "refresh_token": data[1],
                "username": name
            }
    else:
        # otherwise delete no longer functioning auth (user must manually reauthorize)
        del session["auths"]["youtube"]

    current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
    return redirect(host_url + url_for("home"))
