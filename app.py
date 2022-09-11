import uuid
import pkce
import requests

from flask import Flask, render_template, redirect, url_for, session, request
from dotenv import load_dotenv
import os

from FFLogs.API import get_username, get_fights_by_user
from flask_session import Session

host_url = "http://localhost:5000"

load_dotenv()
app = Flask(__name__)

SESSION_TYPE = 'filesystem'
app.config.from_object(__name__)
Session(app)


@app.route('/')
def home():  # put application's code here
    if "username" in session:
        if "recent_reports" not in session:
            session["recent_reports"] = get_fights_by_user(session["token"], session["uid"])

        return render_template('index.html', username=session["username"], reports=session["recent_reports"])
    return render_template('index.html')


@app.route('/auth/challenge', methods=['POST'])
def auth():
    verifier, challenge = pkce.generate_pkce_pair()
    state = str(uuid.uuid4())
    session['state'] = state
    session['verifier'] = verifier

    url = f"""https://www.fflogs.com/oauth/authorize?"""
    url += f"""client_id={os.getenv("FFLOGS_ID")}"""
    url += f"""&code_challenge={challenge}"""
    url += f"""&code_challenge_method=S256"""
    url += f"""&state={state}"""
    url += f"""&redirect_uri={host_url + url_for("auth_verify")}"""
    url += f"""&response_type=code"""
    return redirect(url)


@app.route('/auth/verify')
def auth_verify():
    if session['state'] == request.args.get('state'):
        r = requests.post("https://www.fflogs.com/oauth/token", data={
            "client_id": os.getenv("FFLOGS_ID"),
            "code_verifier": session['verifier'],
            "redirect_uri": host_url + url_for("auth_verify"),
            "grant_type": "authorization_code",
            "code": request.args.get('code')
        })
        if r.status_code == 200:
            session['token'] = r.json()['access_token']
            userdata = get_username(session['token'])
            session['username'] = userdata['name']
            session['uid'] = userdata['id']

    return redirect(url_for('home'))


@app.route('/auth/signout', methods=['POST'])
def auth_signout():
    if session['username'] and request.method == "POST":
        del session['username']
        del session['token']
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run()
