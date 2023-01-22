import uuid
import pkce
from flask import redirect, url_for, session, request, Blueprint, current_app
import FFLogs.API as FFLogsAPI

fflogs_routes = Blueprint('fflogs', __name__)


@fflogs_routes.route('/auth/fflogs/challenge', methods=['POST'])
def auth_challenge():
    """
    When button to start fflogs auth flow is clicked, generate state and call fflogs auth url with state.
    :return: A redirect to the fflogs auth url.
    """
    # generate PKCE challenge pair
    verifier, challenge = pkce.generate_pkce_pair()
    state = str(uuid.uuid4())
    # store state and verifier in session
    session['fflogs_state'] = state
    session['fflogs_verifier'] = verifier

    # redirect user to FFLogs auth page with challenge
    url = current_app.config["FFLOGS_CLIENT"].get_auth_url(challenge, state,
                                                           current_app.config["HOST_URL"] + url_for(
                                                               "fflogs.auth_verify"))
    return redirect(url)


@fflogs_routes.route('/auth/fflogs/verify')
def auth_verify():
    """
    When redirected from FFLogs, verify state and code, then exchange code for token.
    :return: A redirect to the home page.
    """
    # Make sure the user is logged in and has an auths object.
    if "user" not in session or "auths" not in session:
        return redirect(current_app.config["HOST_URL"] + url_for("auth.index"))

    # Check to see if we received state and verifier in the request args.
    if "fflogs_state" not in session or "fflogs_verifier" not in session:
        return redirect(current_app.config["HOST_URL"] + url_for("auth.index"))

    # Delete state and verifier after storing them, and make sure the state matches.
    code = request.args.get('code')
    verifier = session["fflogs_verifier"]
    state_matches = session["fflogs_state"] == request.args.get('state')
    del session["fflogs_state"]
    del session["fflogs_verifier"]

    # Make sure we have a matching state and a request code.
    if not code or not state_matches:
        return redirect(current_app.config["HOST_URL"] + url_for("home"))

    # request token with verifier and provided auth code
    status_code, data = current_app.config["FFLOGS_CLIENT"].try_obtain_token(code, verifier,
                                                                             current_app.config["HOST_URL"] + url_for(
                                                                                 "fflogs.auth_verify"))

    # if successful, store access token for user and get his username and uid, then return to home
    if status_code == 200:
        userdata = FFLogsAPI.get_username(data[0])
        if userdata:
            session["auths"]["fflogs"] = {
                "token": data[0],
                "username": userdata["name"],
                "uid": userdata["id"],
                "refresh_token": data[1]
            }
            current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])

    return redirect(url_for('home'))


@fflogs_routes.route('/auth/fflogs/signout', methods=['POST'])
def auth_signout():
    """
    When button to sign out of fflogs is clicked, remove fflogs auth from user's auths object.
    :return: A redirect to the home page.
    """
    # signout from FFLogs session => delete the data stored by the FFLogs auth flow, then return home
    if "user" in session and "auths" in session and "fflogs" in session["auths"]:
        del session["auths"]["fflogs"]
        current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
    return redirect(url_for('home'))
