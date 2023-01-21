import uuid
from flask import redirect, url_for, session, request, Blueprint, current_app
twitch_routes = Blueprint('twitch', __name__)


@twitch_routes.route('/auth/twitch/challenge', methods=['POST'])
def auth_challenge():
    """
    When button to start Twitch auth is clicked, generate a state and store it in the session, then redirect.
    :return: Redirect to Twitch auth page.
    """
    state = str(uuid.uuid4())
    session['twitch_state'] = state

    # call twitch auth url with state
    url = current_app.config["TWITCH_CLIENT"].get_auth_url(state, current_app.config["HOST_URL"] +
                                                           url_for("twitch.auth_verify"))
    return redirect(url)


@twitch_routes.route('/auth/twitch/verify')
async def auth_verify():
    """
    Twitch auth callback. Verify the state and store the token in the session.
    :return: Redirect to home page.
    """
    if "twitch_state" not in session:
        return redirect(current_app.config["HOST_URL"] + url_for("home"))

    code = request.args.get('code')
    state_matches = session["twitch_state"] == request.args.get('state')
    del session["twitch_state"]

    if "user" not in session or "auths" not in session or not code or not state_matches:
        return redirect(current_app.config["HOST_URL"] + url_for("home"))

    # try to get a token with the code
    status_token, data = current_app.config["TWITCH_CLIENT"].try_obtain_token(code, current_app.config["HOST_URL"]
                                                                              + url_for("twitch.auth_verify"))
    # store twitch token and refresh token user auths if successful
    if status_token == 200:
        status_name, name = current_app.config["TWITCH_CLIENT"].try_get_username(data[0])
        if status_name == 200:
            session["auths"]["twitch"] = {
                "token": data[0],
                "refresh_token": data[1],
                "username": name
            }
            current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
    return redirect(current_app.config["HOST_URL"] + url_for("home"))


@twitch_routes.route('/auth/twitch/signout', methods=['POST'])
def auth_signout():
    """
    Sign out of Twitch.
    :return: Redirect to home page.
    """
    # signout from twitch session => delete the data stored by the twitch auth flow, then return home
    if "user" in session and "auths" in session and "twitch" in session["auths"]:
        del session["auths"]["twitch"]
        current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
    return redirect(url_for('home'))
