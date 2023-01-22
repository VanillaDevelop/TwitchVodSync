import requests
from bson import json_util
from flask import session, request, Blueprint, current_app

ajax_routes = Blueprint('ajax', __name__)


@ajax_routes.route('/ajax/twitch/vod', methods=['GET'])
def ajax_vod_twitch():
    """
    Get info on a Twitch VOD
    :return: JSON data corresponding to the Twitch VOD if the call was successful.
    """
    if "auths" not in session or "twitch" not in session["auths"]:
        return "Not authenticated with Twitch", 401

    video_id = request.args.get("id")
    if not video_id:
        return "No video ID provided", 400

    r = requests.get(f"https://api.twitch.tv/helix/videos?id={video_id}",
                     headers={"Authorization": f"Bearer {session['auths']['twitch']['token']}",
                              "Client-Id": current_app.config["TWITCH_CLIENT"].get_client_id()})

    if r.status_code == 401:
        # try to refresh the token once if we get 401 (maybe expired)
        refresh_status, refresh_data = current_app.config["TWITCH_CLIENT"].try_refresh_twitch_token(
            refresh_token=session['auths']['twitch']['refresh_token'])
        if refresh_status != 200:
            # jank auth, reset and throw error. User will have to re-auth.
            del session["auths"]["twitch"]
            current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
            return "Authorization Issue. Please manually re-authorize.", 401
        else:
            session["auths"]["twitch"]["token"] = refresh_data[0]
            session["auths"]["twitch"]["refresh_token"] = refresh_data[1]
            current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
            r = requests.get(f"https://api.twitch.tv/helix/videos?id={video_id}",
                             headers={"Authorization": f"Bearer {session['auths']['twitch']['token']}",
                                      "Client-Id": current_app.config["TWITCH_CLIENT"].get_client_id()})

    if r.status_code == 200:
        if len(r.json()['data']) == 0:
            return "Video not found", 400

        return {
            "id": video_id,
            "title": r.json()['data'][0]['title'],
            "username": r.json()['data'][0]['user_name'],
            "created_at": r.json()['data'][0]['created_at']
        }
    else:
        return f"Twitch API returned {r.status_code}.", 400


@ajax_routes.route('/ajax/youtube/vod', methods=['GET'])
def ajax_vod_youtube():
    """
    Get info on a YouTube VOD.
    :return: JSON data corresponding to the YouTube VOD if the call was successful.
    """
    if "auths" not in session or "youtube" not in session["auths"]:
        return "Not authenticated with YouTube", 401

    video_id = request.args.get("id")
    if not video_id:
        return "No video ID provided", 400

    r = requests.get(f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}",
                     headers={"Authorization": f"Bearer {session['auths']['youtube']['token']}"})

    if r.status_code == 401:
        # try to refresh the token once if we get 401 (maybe expired)
        refresh_status, refresh_data = current_app.config["YOUTUBE_CLIENT"].try_refresh_youtube_token(
            refresh_token=session['auths']['youtube']['refresh_token'])
        if refresh_status != 200:
            # jank auth, reset and throw error. User will have to re-auth.
            del session["auths"]["youtube"]
            current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
            return "Authorization Issue", 401
        else:
            session["auths"]["youtube"]["token"] = refresh_data[0]
            session["auths"]["youtube"]["refresh_token"] = refresh_data[1]
            current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
            r = requests.get(f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}",
                             headers={"Authorization": f"Bearer {session['auths']['youtube']['token']}"})

    if r.status_code == 200:
        data = r.json()['items']
        if len(data) == 0:
            return "Video not found", 400

        return {
            "id": video_id,
            "title": data[0]['snippet']['title'],
            "created_at": data[0]['snippet']['publishedAt'],
            "username": data[0]['snippet']['channelTitle']
        }
    else:
        return f"YouTube API returned {r.status_code}.", 400


@ajax_routes.route('/ajax/fflogs/report', methods=['GET'])
def ajax_fflogs_report():
    """
    Get info on a FFLogs report.
    :return: JSON data corresponding to the FFLogs report if the call was successful.
    """
    if "auths" not in session or "fflogs" not in session["auths"]:
        return "Not authenticated with FFLogs", 401

    report = request.args.get("code")
    if not report:
        return "No report code provided.", 400

    else:
        status, data = current_app.config["MONGO_CLIENT"].find_or_load_report(report,
                                                                              session["auths"]["fflogs"]["token"],
                                                                              update=request.args.get(
                                                                                  "update") == "True",
                                                                              unknown=request.args.get(
                                                                                  "unknown") == "True")
        if status == 401:
            # try to refresh the token once if we get 401 (maybe expired)
            refresh_status, refresh_data = current_app.config["FFLOGS_CLIENT"].try_refresh_fflogs_token(
                refresh_token=session['auths']['fflogs']['refresh_token'])
            if refresh_status != 200:
                # jank auth, reset and throw error. User will have to re-auth.
                del session["auths"]["fflogs"]
                current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
                return "Authorization Issue", 401
            else:
                session["auths"]["fflogs"]["token"] = refresh_data[0]
                session["auths"]["fflogs"]["refresh_token"] = refresh_data[1]
                current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
                status, data = current_app.config["MONGO_CLIENT"].find_or_load_report(report,
                                                                                      session["auths"]["fflogs"][
                                                                                          "token"],
                                                                                      update=request.args.get(
                                                                                          "update") == "True",
                                                                                      unknown=request.args.get(
                                                                                          "unknown") == "True")

        if status == 200:
            return json_util.dumps(data)
        else:
            return f"FFLogs API returned {status}.", 400
