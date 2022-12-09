import os
import uuid

import requests
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, session, request
from flask_session import Session

import FFLogs.API as FFLogsAPI
import FFLogs.DateUtil as DateUtil
from DocStore import MongoDB
from views.fflogs import fflogs_routes

load_dotenv()
app = Flask(__name__)
host_url = os.getenv("HOST_URL")

app.config["SESSION_TYPE"] = 'mongodb'
app.config["SESSION_MONGODB"] = MongoDB.client
app.config["SESSION_MONGODB_DB"] = 'VodSync'
Session(app)

app.register_blueprint(fflogs_routes)


@app.route('/')
def index():
    if "fflogs_username" in session:
        return redirect(host_url + url_for("home"))
    else:
        return render_template('index.html', host_url=host_url, google_client_id=os.getenv("GOOGLE_CLIENT_ID"))


@app.route('/home')
def home():
    if "fflogs_username" not in session:
        return redirect(url_for("index"))

    if "recent_reports" not in session:
        session["recent_reports"] = FFLogsAPI.get_fights_by_user(session["fflogs_token"], session["fflogs_uid"])

    return render_template('home.html', username=session["fflogs_username"], reports=session["recent_reports"])


@app.route('/report/')
def report():
    # require access token
    if not session["token"]:
        return redirect(url_for("home"))

    # report code should be given as an argument
    if not request.args.get("code"):
        return redirect(url_for("home"))

    # get all fights in report for given code
    data = FFLogsAPI.get_report_data(session["token"], request.args.get("code"))
    # simply redirect home for now if code is invalid
    if not data:
        return redirect(url_for("home"))

    # add fight start times and end times as formatted timestamps
    DateUtil.append_timestamps(data['startTime'], data['fights'])
    return render_template('report.html', fights=data['fights'],
                           encounternames=FFLogsAPI.get_encounter_dict(session["token"], data['fights']),
                           start_time=DateUtil.timestamp_to_string(data['startTime']),
                           end_time=DateUtil.timestamp_to_string(data['endTime']),
                           start_epoch=data['startTime'],
                           code=request.args.get("code"),
                           twitch_token=session["twitch_token"] if "twitch_token" in session else None)


@app.route('/auth/twitch_challenge', methods=['POST'])
def auth_twitch():
    # when button to start twitch out flow is clicked
    # generate state, and store the report we came from
    state = str(uuid.uuid4())
    session['state_twitch'] = state
    session['redirect_to_log'] = request.form.get("code")

    # call twitch auth url with state
    url = f"""https://id.twitch.tv/oauth2/authorize?""" \
          f"""client_id={os.getenv("TWITCH_ID")}""" \
          f"""&response_type=code""" \
          f"""&state={state}""" \
          f"""&scope=""" \
          f"""&redirect_uri={host_url + url_for("auth_twitch_verify")}"""
    return redirect(url)


@app.route('/auth/twitch')
def auth_twitch_verify():
    # when redirected from Twitch
    # compare state, request token with auth code provided
    if session['state_twitch'] == request.args.get('state'):
        r = requests.post("https://id.twitch.tv/oauth2/token", data={
            "client_id": os.getenv("TWITCH_ID"),
            "client_secret": os.getenv("TWITCH_SECRET"),
            "code": request.args.get('code'),
            "redirect_uri": host_url + url_for("auth_twitch_verify"),
            "grant_type": "authorization_code",
        })
        # store twitch token and refresh token in session
        if r.status_code == 200:
            session['twitch_token'] = r.json()['access_token']
            session['twitch_refresh_token'] = r.json()['refresh_token']

        log = session['redirect_to_log']
        del session['redirect_to_log']
        del session['state_twitch']

        return redirect(host_url + url_for("report") + "?code=" + log)

    return redirect(host_url)


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
