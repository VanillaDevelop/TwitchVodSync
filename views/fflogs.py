import os
import uuid
import pkce
import requests
from dotenv import load_dotenv
from flask import redirect, url_for, session, request, Blueprint
import FFLogs.API as FFLogsAPI

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
    # compare state
    if session['fflogs_state'] == request.args.get('state'):
        # request token with verifier and provided auth code
        r = requests.post("https://www.fflogs.com/oauth/token", data={
            "client_id": os.getenv("FFLOGS_CLIENT_ID"),
            "code_verifier": session['fflogs_verifier'],
            "redirect_uri": host_url + url_for("fflogs.auth_verify"),
            "grant_type": "authorization_code",
            "code": request.args.get('code')
        })

        # if successful, store access token for user and get his username and uid, then return to home
        if r.status_code == 200:
            session['fflogs_token'] = r.json()['access_token']
            userdata = FFLogsAPI.get_username(session['fflogs_token'])
            session['fflogs_username'] = userdata['name']
            session['fflogs_uid'] = userdata['id']

        del session['fflogs_state']
        del session['fflogs_verifier']

    return redirect(url_for('home'))


@fflogs_routes.route('/auth/fflogs/signout', methods=['POST'])
def auth_signout():
    # signout from FFLogs session => delete the data stored by the FFLogs auth flow, then return home
    if session['fflogs_username'] and request.method == "POST":
        del session['fflogs_username']
        del session['fflogs_token']
        del session['fflogs_uid']
    return redirect(url_for('home'))