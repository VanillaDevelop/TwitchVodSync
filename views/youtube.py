from flask import redirect, url_for, session, request, Blueprint, current_app
youtube_routes = Blueprint('youtube', __name__)


@youtube_routes.route('/auth/youtube/challenge', methods=['POST'])
def auth_challenge():
    """
    When user clicks the YouTube sign in button, redirect him to the YouTube auth page.
    :return: A redirect to the YouTube auth page.
    """
    # when button to start YouTube auth flow is clicked
    # redirect to YouTube auth url
    url = current_app.config["YOUTUBE_CLIENT"].get_auth_url(current_app.config["HOST_URL"]
                                                            + url_for("youtube.auth_verify"))
    return redirect(url)


@youtube_routes.route('/auth/youtube/verify')
def auth_verify():
    """
    When the user is redirected from YouTube, verify the code and store the token.
    :return: Redirect to the home page.
    """
    # Make sure the user is logged in and has an auth object.
    if "user" not in session or "auths" not in session:
        return redirect(current_app.config["HOST_URL"] + url_for("index"))

    # Check we received a code in the request args.
    code = request.args.get('code')
    if not code:
        return redirect(current_app.config["HOST_URL"] + url_for("home"))

    # request token with the provided auth code
    status_code, data = current_app.config["YOUTUBE_CLIENT"].try_obtain_token(
        code, current_app.config["HOST_URL"] + url_for("youtube.auth_verify"))

    # if successful, store access token for user and get his email, then return to home
    if status_code == 200:
        status_name, name = current_app.config["YOUTUBE_CLIENT"].try_get_username(data[0])
        if status_name == 200:
            session["auths"]["youtube"] = {
                "token": data[0],
                "refresh_token": data[1],
                "username": name
            }
            current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])

    return redirect(url_for('home'))


@youtube_routes.route('/auth/youtube/signout', methods=['POST'])
def auth_signout():
    """
    Sign out the user from YouTube.
    :return:
    """
    # Delete the data stored by the YouTube auth flow, then return home
    if "user" in session and "auths" in session and "youtube" in session["auths"]:
        del session["auths"]["youtube"]
        current_app.config["MONGO_CLIENT"].store_auth_keys(session["user"], session["auths"])
    return redirect(url_for('home'))
