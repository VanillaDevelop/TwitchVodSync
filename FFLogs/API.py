import requests

encounters = dict()


def get_username(token):
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
