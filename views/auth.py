from flask import Blueprint, url_for, current_app, request, session, redirect, render_template
from flask_cors import cross_origin
from google.auth.transport import requests as google_auth_request
from google.oauth2 import id_token

auth_routes = Blueprint('auth', __name__)


@auth_routes.route('/')
@cross_origin(supports_credentials=True, origins="*")
def index():
    if "user" in session:
        return redirect(current_app.config["HOST_URL"] + url_for("home"))
    else:
        return render_template('index.html', host_url=current_app.config["HOST_URL"] + url_for("auth.login"),
                               google_client_id=current_app.config["GOOGLE_ID"])


@auth_routes.route('/login', methods=['POST'])
def login():
    # try to get the user's email to authorize them
    try:
        id_info = id_token.verify_oauth2_token(request.form["credential"], google_auth_request.Request(),
                                               current_app.config["GOOGLE_ID"])
        if "email" in id_info:
            session["user"] = id_info["email"]
            return redirect(current_app.config["HOST_URL"] + url_for("home"))
        return redirect(current_app.config["HOST_URL"] + url_for("auth.index"))
    except ValueError:
        return redirect(current_app.config["HOST_URL"] + url_for("auth.index"))


@auth_routes.route('/logout', methods=['POST'])
def logout():
    # delete login cookie
    if "user" in session and request.method == "POST":
        session.clear()
    return redirect(url_for('auth.index'))
