import os

import requests
from dotenv import load_dotenv
from flask import session, request, Blueprint

import Twitch.auth
import YouTube.auth
from DocStore import MongoDB

load_dotenv()
ajax_routes = Blueprint('ajax', __name__)

twitch_client_id = os.getenv("TWITCH_ID")


# method called via ajax to get info on a Twitch VOD
@ajax_routes.route('/ajax/twitch/vod', methods=['GET'])
def ajax_vod_twitch():
    if not session["auths"]["twitch"]:
        return "Not authenticated with Twitch", 401

    video_id = request.args.get("id")
    if not video_id:
        return "No video ID provided", 400

    else:
        r = requests.get(f"https://api.twitch.tv/helix/videos?id={video_id}",
                         headers={"Authorization": f"Bearer {session['auths']['twitch']['token']}",
                                  "Client-Id": twitch_client_id})

        if r.status_code == 401:
            # try to refresh the token once if we get 401 (maybe expired)
            refresh_status, refresh_data = Twitch.auth.try_refresh_twitch_token(
                refresh_token=session['auths']['twitch']['refresh_token'])
            if refresh_status != 200:
                # jank auth, reset and redirect
                del session["auths"]["twitch"]
                MongoDB.store_auth_keys(session["user"], session["auths"])
                return "Authorization Issue", 401
            else:
                session["auths"]["twitch"]["token"] = refresh_data[0]
                session["auths"]["twitch"]["refresh_token"] = refresh_data[1]
                MongoDB.store_auth_keys(session["user"], session["auths"])
                r = requests.get(f"https://api.twitch.tv/helix/videos?id={video_id}",
                                 headers={"Authorization": f"Bearer {session['auths']['twitch']['token']}",
                                          "Client-Id": twitch_client_id})

        if r.status_code == 200:
            if len(r.json()['data']) == 0:
                return "Video not found", 400

            return {
                "id": video_id,
                "title": r.json()['data'][0]['title'],
                "created_at": r.json()['data'][0]['created_at']
            }
        else:
            return f"Twitch API returned {r.status_code}.", 400


# method called via ajax to get info on a youtube VOD
@ajax_routes.route('/ajax/youtube/vod', methods=['GET'])
def ajax_vod_youtube():
    if not session["auths"]["youtube"]:
        return "Not authenticated with YouTube", 401

    video_id = request.args.get("id")
    if not video_id:
        return "No video ID provided", 400

    else:
        r = requests.get(f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}",
                         headers={"Authorization": f"Bearer {session['auths']['youtube']['token']}"})

        if r.status_code == 401:
            # try to refresh the token once if we get 401 (maybe expired)
            refresh_status, refresh_data = YouTube.auth.try_refresh_youtube_token(
                refresh_token=session['auths']['youtube']['refresh_token'])
            if refresh_status != 200:
                # jank auth, reset and redirect
                del session["auths"]["youtube"]
                MongoDB.store_auth_keys(session["user"], session["auths"])
                return "Authorization Issue", 401
            else:
                session["auths"]["youtube"]["token"] = refresh_data[0]
                session["auths"]["youtube"]["refresh_token"] = refresh_data[1]
                MongoDB.store_auth_keys(session["user"], session["auths"])
                r = requests.get(f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}",
                                 headers={"Authorization": f"Bearer {session['auths']['youtube']['token']}"})

        if r.status_code == 200:
            data = r.json()['items']
            if len(data) == 0:
                return "Video not found", 400

            return {
                "id": video_id,
                "title": data[0]['snippet']['title'],
                "created_at": data[0]['snippet']['publishedAt']
            }
        else:
            return f"YouTube API returned {r.status_code}.", 400
