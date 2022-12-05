import requests

encounters = dict()


def get_username(token):
    """
    Query for the username of the user who this access token belongs to.
    :param token: The FFLogs API Access Token.
    :return: An array of UID and Username of the user who this access token belongs to.
    """
    query = """
    query {
       userData
       {
           currentUser
           {
               id,
               name
           }
       }
   }
   """

    r = __call_user_endpoint(query, token)
    if r:
        return r.json()['data']['userData']['currentUser']
    else:
        return None


def get_fights_by_user(token, uid):
    """
    Get recent reports by a given user
    :param token: The FFLogs Access Token for the query
    :param uid: The userid to get reports by
    :return: Recent reports by this user (The first page)
    """
    query = """
    query
        {
            reportData
            {
                reports(userID:""" + str(uid) + """,page:1)
                {
                    data
                    {
                        code,
                        title,
                        startTime
                    }
                }
            }
        }
    """

    r = __call_client_endpoint(query, token)
    if r:
        return r.json()['data']['reportData']['reports']['data']
    else:
        return None


def get_report_data(token, code):
    """
    Get info about fights in report
    :param token: The user access token
    :param code: The report code
    :return: A list of fights in the report, and metadata on the report.
    """

    query = """
    query
    {
        reportData
        {
            report(code: \"""" + str(code) + """\")
            {
                startTime,
                endTime,
                fights
                {
                    id
                    startTime,
                    endTime,
                    encounterID,
                },
            }
        }
    }"""
    r = __call_client_endpoint(query, token)
    if r:
        return r.json()['data']['reportData']['report']
    else:
        return None


def get_player_dict_by_report(token, code):
    """
    Get player data for a given report
    :param token: The FFLogs API Access Token
    :param code: The code to get the data for.
    :return:
    """
    query = """
    query
    {
        reportData
        {
            report(code: \"""" + str(code) + """\")
            {
                masterData
                {
                    actors(type: "Player")
                    {
                        id,
                        name,
                        server
                    }
                }
            }
        }
    }
    """
    r = __call_client_endpoint(query, token)
    if r:
        player_dict = dict()
        for player in r.json()['data']['reportData']['report']['masterData']['actors']:
            player_dict[player['id']] = player['name']
        return player_dict
    else:
        return None


def get_encounter_dict(token, fights):
    """
    Return the current mapping of encounter IDs to names.
    Ensures that all encounter IDs present in the list of fights are part of the encounter dictionary.
    :param token: The FFLogs access token of the user
    :param fights: The list of fights for which to get the encounter names
    :return: The full encounter dictionary as known by the API.
    """
    for fight in fights:
        eid = fight["encounterID"]
        if eid not in encounters and eid != 0:
            name = __query_for_encounter_name(token, eid)
            if not name:
                return None
            else:
                encounters[eid] = name
    return encounters


def __query_for_encounter_name(token, eid):
    """
    Gets the name of a given encounter ID.
    :param token: The FFLogs API access token to query for the encounter name.
    :param eid: The encounter ID to query for.
    :return: The name of the encounter.
    """
    query = """
    query
    {
        worldData
        {
            encounter(id:""" + str(eid) + """)
            {
                name
            }
        }
    }
    """
    r = __call_client_endpoint(query, token)
    if r:
        return r.json()['data']['worldData']['encounter']['name']
    else:
        return None


def __call_user_endpoint(query, token):
    url = 'https://www.fflogs.com/api/v2/user'
    r = requests.post(url, json={'query': query}, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        return r
    return None


def __call_client_endpoint(query, token):
    url = 'https://www.fflogs.com/api/v2/client'
    r = requests.post(url, json={'query': query}, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        return r
    return None
