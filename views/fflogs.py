import os
import uuid
import pkce
from dotenv import load_dotenv
from flask import redirect, url_for, session, request, Blueprint, current_app
import FFLogs.API as FFLogsAPI
from FFLogs import auth

load_dotenv()
fflogs_routes = Blueprint('fflogs', __name__)
host_url = os.getenv("HOST_URL")


@fflogs_routes.route('/auth/fflogs/challenge', methods=['POST'])
def auth_challenge():
    # generate PKCE challenge pair
    verifier, challenge = pkce.generate_pkce_pair()
    state = str(uuid.uuid4())
    # store state and verifier in session
    session['fflogs_state'] = state
    session['fflogs_verifier'] = verifier

    # redirect user to FFLogs auth page with challenge
    url = f"""https://www.fflogs.com/oauth/authorize?""" \
          f"""client_id={os.getenv("FFLOGS_CLIENT_ID")}""" \
          f"""&code_challenge={challenge}""" \
          f"""&code_challenge_method=S256""" \
          f"""&state={state}""" \
          f"""&redirect_uri={host_url + url_for("fflogs.auth_verify")}""" \
          f"""&response_type=code"""
    return redirect(url)


@fflogs_routes.route('/auth/fflogs/verify')
def auth_verify():
    if "user" not in session or "auths" not in session:
        return redirect(host_url + url_for("index"))

    if "fflogs_state" not in session or "fflogs_verifier" not in session:
        return redirect(host_url + url_for("index"))

    state = request.args.get('state')
    code = request.args.get('code')
    verifier = session["fflogs_verifier"]
    state_matches = session["fflogs_state"] == state
    del session["fflogs_state"]
    del session["fflogs_verifier"]

    if not code or not state_matches:
        return redirect(host_url + url_for("home"))

    # request token with verifier and provided auth code
    status_code, data = auth.try_obtain_token(code, verifier, host_url + url_for("fflogs.auth_verify"))

    # if successful, store access token for user and get his username and uid, then return to home
    if status_code == 200:
        userdata = FFLogsAPI.get_username(data[0])
        if userdata:
            session["auths"]["fflogs"] = {
                "token": data[0],
                "username": userdata["name"],
                "uid": userdata["id"],
                "refresh_token": data[1]
            }
            current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])

    return redirect(url_for('home'))


@fflogs_routes.route('/auth/fflogs/refresh')
async def auth_refresh():
    # don't allow users to arbitrarily request token refreshes
    if "fflogs_refresh" not in session:
        return redirect(host_url + url_for("home"))
    del session["fflogs_refresh"]

    if "user" not in session or "auths" not in session or "fflogs" not in session["auths"]:
        return redirect(host_url + url_for("home"))

    status_token, data = auth.try_refresh_fflogs_token(refresh_token=session["auths"]["fflogs"]["refresh_token"])
    # store fflogs token and refresh token user auths if successful
    if status_token == 200:
        userdata = FFLogsAPI.get_username(data[0])
        if userdata:
            session["auths"]["fflogs"] = {
                "token": data[0],
                "username": userdata["name"],
                "uid": userdata["id"],
                "refresh_token": data[1]
            }
        else:
            # otherwise delete no longer functioning auth (user must manually reauthorize)
            del session["auths"]["fflogs"]
    else:
        # same here
        del session["auths"]["fflogs"]

    current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
    return redirect(host_url + url_for("home"))


@fflogs_routes.route('/auth/fflogs/signout', methods=['POST'])
def auth_signout():
    # signout from FFLogs session => delete the data stored by the FFLogs auth flow, then return home
    if "user" in session and "auths" in session and "fflogs" in session["auths"]:
        del session["auths"]["fflogs"]
        current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
    return redirect(url_for('home'))
