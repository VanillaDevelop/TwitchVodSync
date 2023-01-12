import os

from bson import json_util
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, session, request
from flask_cors import cross_origin
from flask_session import Session
from google.auth.transport import requests as google_auth_request
from google.oauth2 import id_token

import FFLogs.DateUtil as DateUtil
import FFLogs.auth
from DocStore import MongoDB
from views.ajax import ajax_routes
from views.fflogs import fflogs_routes
from views.twitch import twitch_routes
from views.youtube import youtube_routes

load_dotenv()
app = Flask(__name__)
host_url = os.getenv("HOST_URL")
google_id = os.getenv("GOOGLE_CLIENT_ID")

app.config["SESSION_TYPE"] = "mongodb"
app.config["SESSION_MONGODB"] = MongoDB.client
app.config["SESSION_MONGODB_DB"] = "VodSync"
Session(app)

app.register_blueprint(fflogs_routes)
app.register_blueprint(youtube_routes)
app.register_blueprint(twitch_routes)
app.register_blueprint(ajax_routes)


@app.route('/')
@cross_origin(supports_credentials=True, origins="*")
def index():
    if "user" in session:
        return redirect(host_url + url_for("home"))
    else:
        return render_template('index.html', host_url=host_url + url_for("login"),
                               google_client_id=google_id)


@app.route('/login', methods=['POST'])
def login():
    # try to get the user's email to authorize them
    try:
        id_info = id_token.verify_oauth2_token(request.form["credential"], google_auth_request.Request(), google_id)
        if "email" in id_info:
            session["user"] = id_info["email"]
            return redirect(host_url + url_for("home"))
        return redirect(host_url + url_for("index"))
    except ValueError:
        return redirect(host_url + url_for("index"))


@app.route('/logout', methods=['POST'])
def logout():
    # delete login cookie
    if "user" in session and request.method == "POST":
        session.clear()
    return redirect(url_for('index'))


@app.route('/home')
def home():
    if "user" not in session:
        return redirect(url_for("index"))

    if "auths" not in session:
        session["auths"] = MongoDB.get_auth_keys(session["user"])

    return render_template('home.html', username=session["user"], auths=session["auths"])


@app.route('/reports')
def reports():
    if "user" not in session:
        return redirect(url_for("index"))

    return render_template('reports.html', auths=session["auths"], username=session["user"])


@app.route('/report/')
def report():
    if "user" not in session:
        return redirect(url_for("index"))

    # check auths
    if "twitch" not in session["auths"] or "youtube" not in session["auths"] or "fflogs" not in session["auths"]:
        return redirect(url_for("home"))

    # report code should be given as an argument
    if not request.args.get("code"):
        return redirect(url_for("home"))

    # get all fights in report for given code
    report_status, data = MongoDB.find_or_load_report(request.args.get("code"), session["auths"]["fflogs"]["token"])
    if report_status == 401:
        refresh_status, refresh_data = FFLogs.auth.try_refresh_fflogs_token(
            refresh_token=session["auths"]["fflogs"]["refresh_token"])
        if refresh_status != 200:
            # jank auth, reset and redirect
            del session["auths"]["fflogs"]
            MongoDB.store_auth_keys(session["user"], session["auths"])
            return redirect(url_for("home"))
        else:
            session["auths"]["fflogs"]["token"] = refresh_data[0]
            session["auths"]["fflogs"]["refresh_token"] = refresh_data[1]
            MongoDB.store_auth_keys(session["user"], session["auths"])
        # re-query
        report_status, data = MongoDB.find_or_load_report(request.args.get("code"), session["auths"]["fflogs"]["token"])

    # simply redirect home if we get an error after a potential 401 retry
    if report_status != 200:
        return redirect(url_for("home"))

    dict_status, encounternames = MongoDB.get_filled_encounter_dict(data["fights"], session["auths"]["fflogs"]["token"])

    # we assume the key didn't time out between the last call and this, so if anything goes wrong here, we just send
    # the user back (this should happen extremely, EXTREMELY rarely if at all since encounter dict calls are rare)
    if dict_status != 200:
        return redirect(url_for("home"))
    data["encounternames"] = encounternames

    del data["_id"]

    return render_template('report.html', data=json_util.dumps(data).replace("\"", "\\\""),
                           start_time=DateUtil.timestamp_to_string(data['startTime']),
                           end_time=DateUtil.timestamp_to_string(data['endTime']),
                           start_epoch=data['startTime'],
                           title=data['title'],
                           auths=session["auths"],
                           username=session["user"])


if __name__ == '__main__':
    app.run()
