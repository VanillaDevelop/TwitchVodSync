import os
import google_auth_oauthlib.flow
from dotenv import load_dotenv
from flask import redirect, url_for, session, request, Blueprint
from google.auth.transport import requests
from google.oauth2 import id_token
from DocStore.MongoDB import store_auth_keys

load_dotenv()
youtube_routes = Blueprint('youtube', __name__)
host_url = os.getenv("HOST_URL")

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'

# authorization flow settings (require YouTube readonly permissions and reading the user email)
flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
    os.getenv("YT_CLIENT_LOCATION"),
    scopes=['https://www.googleapis.com/auth/youtube.readonly','https://www.googleapis.com/auth/userinfo.email'])
# need to hardcode this due to circular dependency
flow.redirect_uri = host_url + "/auth/youtube/response"


@youtube_routes.route('/auth/youtube/flow', methods=['POST'])
def auth_flow():
    # generate oauth URL
    authorization_url, _ = flow.authorization_url(access_type="offline")
    return redirect(authorization_url)


@youtube_routes.route('/auth/youtube/response')
def flow_response():
    if "code" not in request.args:
        return redirect(host_url + url_for("home"))
    if "user" not in session:
        return redirect(host_url + url_for("index"))

    authorization_response = request.url
    flow.fetch_token(authorization_response=authorization_response)
    credentials = flow.credentials

    try:
        id_info = id_token.verify_oauth2_token(credentials.id_token, requests.Request(), credentials.client_id)

        session["auths"]["youtube"] = {
            'username': id_info["email"],
            'token': credentials.token,
            'id_token': credentials.id_token,
            'scopes': credentials.scopes
        }
        store_auth_keys(session["user"], session["auths"])
    except ValueError:
        pass

    return redirect(url_for('home'))


@youtube_routes.route('/auth/youtube/signout', methods=['POST'])
def auth_signout():
    # signout from YouTube session => delete the data stored by the YouTube auth flow, then return home
    if "user" in session and "youtube" in session["auths"] and request.method == "POST":
        del session["auths"]["youtube"]
        store_auth_keys(session["user"], session["auths"])
    return redirect(url_for('home'))
