import urllib
import uuid
import pkce
from hashlib import sha256

from flask import Flask, render_template, redirect, url_for
from dotenv import load_dotenv
import os

host_url = "http://localhost:5000"

load_dotenv()
app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return render_template('index.html')


@app.route('/auth/challenge')
def auth():
    verifier, challenge = pkce.generate_pkce_pair()
    challenge = sha256(verifier.encode('utf-8')).hexdigest()
    state = uuid.uuid4()

    url = f"""https://www.fflogs.com/oauth/authorize?"""
    url += f"""client_id={os.getenv("FFLOGS_ID")}"""
    url += f"""&code_challenge={challenge}"""
    url += f"""&code_challenge_method=S256"""
    url += f"""&state={state}"""
    url += f"""&redirect_uri={urllib.parse.quote(host_url + url_for("auth_verify"))}"""
    url += f"""&response_type=code"""
    return redirect(url)


@app.route('/auth/verify')
def auth_verify():
    return "yooo"


if __name__ == '__main__':
    app.run()
