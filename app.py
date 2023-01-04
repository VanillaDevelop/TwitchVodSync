import os

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, session, request
from flask_cors import cross_origin
from flask_session import Session
from google.auth.transport import requests as google_auth_request
from google.oauth2 import id_token

import FFLogs.API as FFLogsAPI
import FFLogs.DateUtil as DateUtil
from DocStore import MongoDB
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
    data = MongoDB.find_or_load_report(request.args.get("code"), session["auths"]["fflogs"]["token"])
    # simply redirect home for now if code is invalid
    if not data:
        return redirect(url_for("home"))

    return render_template('report.html', fights=data['fights'],
                           encounternames=FFLogsAPI.get_encounter_dict(session["auths"]["fflogs"]["token"],
                                                                       data["fights"]),
                           start_time=DateUtil.timestamp_to_string(data['startTime']),
                           end_time=DateUtil.timestamp_to_string(data['endTime']),
                           start_epoch=data['startTime'],
                           code=request.args.get("code"),
                           auths=session["auths"],
                           username=session["user"])


@app.route('/ajax/twitch/vod', methods=['GET'])
def ajax_vod_info():
    # method called via ajax to get info on a Twitch VOD
    if not session['twitch_token']:
        return "Not authenticated with Twitch", 400

    video_id = request.args.get("id")
    if not video_id:
        return "No video ID provided", 400

    else:
        r = requests.get(f"https://api.twitch.tv/helix/videos?id={video_id}",
                         headers={"Authorization": f"Bearer {session['twitch_token']}",
                                  "Client-Id": os.getenv("TWITCH_ID")})
        if r.status_code == 200:
            if len(r.json()['data']) == 0:
                return "Video not found", 400

            return {
                "id": video_id,
                "title": r.json()['data'][0]['title'],
                "created_at": r.json()['data'][0]['created_at']
            }
        else:
            if r.status_code == 401:
                # try to refresh the token once if we get 401 (maybe expired)
                # TODO refactor duplicate code
                r = requests.post("https://id.twitch.tv/oauth2/token", data={
                    "client_id": os.getenv("TWITCH_ID"),
                    "client_secret": os.getenv("TWITCH_SECRET"),
                    "refresh_token": session['twitch_refresh_token'],
                    "grant_type": "refresh_token",
                })
                if r.status_code == 200:
                    session['twitch_token'] = r.json()['access_token']
                    session['twitch_refresh_token'] = r.json()['refresh_token']
                    r = requests.get(f"https://api.twitch.tv/helix/videos?id={video_id}",
                                     headers={"Authorization": f"Bearer {session['twitch_token']}",
                                              "Client-Id": os.getenv("TWITCH_ID")})
                    if r.status_code == 200:
                        if len(r.json()['data']) == 0:
                            return "Video not found", 400

                        return {
                            "id": video_id,
                            "title": r.json()['data'][0]['title'],
                            "created_at": r.json()['data'][0]['created_at']
                        }

            return f"Twitch API returned {r.status_code}.", 400


if __name__ == '__main__':
    app.run()
