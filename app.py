import base64
import os

from bson import json_util
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, session, request
from flask_session import Session

import FFLogs.auth
from DocStore import MongoDB
from Twitch.auth import TwitchAuth
from YouTube.auth import YouTubeAuth
from views.ajax import ajax_routes
from views.auth import auth_routes
from views.fflogs import fflogs_routes
from views.twitch import twitch_routes
from views.youtube import youtube_routes

# create flask app
app = Flask(__name__)

# load environment variables
load_dotenv()

# first create the certificate file (yes this is a hack I guess, I don't know, Heroku doesn't have a file upload)
if not os.path.isfile(os.getenv("MONGODB_CERT")):
    with open(os.getenv("MONGODB_CERT"), "w") as f:
        f.write(base64.b64decode(os.getenv("MONGODB_CERT_DATA")).decode("utf-8"))

# create API handlers and store them in the config
app.config["MONGO_CLIENT"] = MongoDB.MongoDBConnection(
    os.getenv("MONGODB_URI"),
    os.getenv("MONGODB_CERT"),
    int(os.getenv("UPDATE_CADENCE"))
)

app.config["YOUTUBE_CLIENT"] = YouTubeAuth(
    os.getenv("YOUTUBE_ID"),
    os.getenv("YOUTUBE_SECRET")
)

app.config["TWITCH_CLIENT"] = TwitchAuth(
    os.getenv("TWITCH_ID"),
    os.getenv("TWITCH_SECRET")
)

app.config["FFLOGS_CLIENT"] = FFLogs.auth.FFLogsAuth(
    os.getenv("FFLOGS_CLIENT_ID"),
)

# store other config variables
app.config["HOST_URL"] = os.getenv("HOST_URL")
app.config["GOOGLE_ID"] = os.getenv("GOOGLE_CLIENT_ID")
app.config["SESSION_TYPE"] = "mongodb"
app.config["SESSION_MONGODB"] = app.config["MONGO_CLIENT"].get_client()
app.config["SESSION_MONGODB_DB"] = "VodSync"

# setup session
Session(app)

# register routes
with app.app_context():
    app.register_blueprint(fflogs_routes)
    app.register_blueprint(youtube_routes)
    app.register_blueprint(twitch_routes)
    app.register_blueprint(ajax_routes)
    app.register_blueprint(auth_routes)


@app.route('/home')
def home():
    """
    Home page for logged-in users.
    :return: Home page.
    """
    if "user" not in session:
        return redirect(url_for("auth.index"))

    if "auths" not in session:
        session["auths"] = app.config["MONGO_CLIENT"].get_auth_keys(session["user"])

    return render_template('home.html', username=session["user"], auths=session["auths"])


@app.route('/reports')
def reports():
    """
    Page for selecting an FFLogs report.
    :return: Reports page.
    """
    if "user" not in session:
        return redirect(url_for("auth.index"))

    return render_template('reports.html', auths=session["auths"], username=session["user"])


@app.route('/report/')
def report():
    """
    Page for viewing report details.
    :return: Report details page.
    """
    if "user" not in session:
        return redirect(url_for("auth.index"))

    # check auths
    if "twitch" not in session["auths"] or "youtube" not in session["auths"] or "fflogs" not in session["auths"]:
        return redirect(url_for("home"))

    # report code should be given as an argument
    if not request.args.get("code"):
        return redirect(url_for("home"))

    # get all fights in report for given code
    report_status, data = app.config["MONGO_CLIENT"].find_or_load_report(request.args.get("code"),
                                                                         session["auths"]["fflogs"]["token"])

    # TODO we can turn this into a utils function to arbitrarily double-try a function with a re-auth attempt inbetween.
    if report_status == 401:
        refresh_status, refresh_data = app.config["FFLOGS_CLIENT"].try_refresh_fflogs_token(
            refresh_token=session["auths"]["fflogs"]["refresh_token"])
        if refresh_status != 200:
            # jank auth, reset and redirect
            del session["auths"]["fflogs"]
            app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
            return redirect(url_for("home"))
        else:
            session["auths"]["fflogs"]["token"] = refresh_data[0]
            session["auths"]["fflogs"]["refresh_token"] = refresh_data[1]
            app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
        # re-query
        report_status, data = app.config["MONGO_CLIENT"].find_or_load_report(request.args.get("code"),
                                                                             session["auths"]["fflogs"]["token"])

    # simply redirect home if we get an error after a potential 401 retry
    if report_status != 200:
        return redirect(url_for("home"))

    return render_template('report.html', data=json_util.dumps(data).replace("\"", "\\\""),
                           title=data['title'],
                           code=request.args.get("code"),
                           auths=session["auths"],
                           username=session["user"])


if __name__ == '__main__':
    app.run()
