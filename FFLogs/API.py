import time
from typing import Tuple, Optional

import requests
from requests import Response

from FFLogs import DateUtil


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

    status, data = __call_user_endpoint(query, token)
    if status == 200:
        return data.json()['data']['userData']['currentUser']
    else:
        return None


def get_report_data(token, code):
    """
    Get info about fights in report
    :param token: The user access token
    :param code: The report code
    :return: A tuple of (status, data) if successful, otherwise (status, None).
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
                title
            }
        }
    }"""
    status, data = __call_client_endpoint(query, token)
    if status != 200:
        return status, None

    data = data.json()['data']['reportData']['report']
    # if there is any data (i.e. the report actually exists)
    if data:
        # append report ID to data as well as timestamp of acquisition
        data["loaded_at"] = time.time()
        data["code"] = code
        # add fight start times and end times as formatted timestamps
        DateUtil.append_timestamps(data["startTime"], data["fights"])
        # order fights by their end time (latest pull first)
        data["fights"].sort(key=lambda x: x["endTime"], reverse=True)
        # append death data
        if not __append_death_info(token, data):
            return 800, None
        # append player data
        if not __append_player_info(token, data):
            return 800, None
        return 200, data


def __append_death_info(token, report_data):
    """
    Append death information for a given report
    :param token: The user access token
    :param report_data: The report data (collected by the get_report_data function)
    :return: True if successful, false if not. If true, the death data is appended to report_data.
    """

    # if we already queried for previous pulls, we can get it from the report data
    if "last_queried_death_timestamp" in report_data:
        previous_timestamp = int(report_data["last_queried_death_timestamp"])
    else:
        previous_timestamp = report_data["fights"][-1]["startTime"]

    last_timestamp = int(report_data["fights"][0]["endTime"])  # last pull should be first

    deaths = []
    previous_status = 200

    while previous_status == 200 and previous_timestamp is not None and previous_timestamp < last_timestamp:
        death_query = """
        query
        {
                reportData
                {
                        report(code: \"""" + report_data["code"] + """\")
                        {
                            events(dataType: Deaths, startTime: """ + str(previous_timestamp) + """,endTime: """ \
                      + str(last_timestamp) + """)
                            {
                                data,
                                nextPageTimestamp
                            }
                        }
                }
        }"""
        previous_status, data = __call_client_endpoint(death_query, token)
        if previous_status != 200:
            break

        data = data.json()["data"]["reportData"]["report"]["events"]
        for death in data["data"]:
            deaths.append({
                "timestamp": death["timestamp"],
                "targetID": death["targetID"],
                "fight": death["fight"],
            })
            if data["nextPageTimestamp"]:
                previous_timestamp = data["nextPageTimestamp"]
            else:
                previous_timestamp = None

    if previous_status != 200:
        return False

    report_data["last_queried_death_timestamp"] = last_timestamp
    if "deaths" not in report_data:
        report_data["deaths"] = deaths
    else:
        report_data["deaths"].append(deaths)
    return True


def __append_player_info(token, report_data):
    """
    Append player information for a given report
    :param token: The user access token
    :param report_data: The report data (collected by the get_report_data function, and appended deaths)
    :return: True if successful, false if not. If true, player data is appended to report_data.
    """

    # requires the report to have death data appended
    if "deaths" not in report_data:
        return False

    # get the time range
    end_time = int(report_data["fights"][0]["endTime"])
    start_time = int(report_data["fights"][-1]["startTime"])

    # get player ids who died
    pids = set([death["targetID"] for death in report_data["deaths"]])

    # get already existing player data (if any)
    player_data = report_data["player_data"] if "player_data" in report_data else {}

    # only query if there is unknown player
    if len([pid for pid in pids if str(pid) not in player_data]) == 0:
        return True

    query = """
    query
    {
        reportData
        {
            report(code: \"""" + report_data["code"] + """\")
            {
                playerDetails(startTime: """ + str(start_time) + """, endTime: """ + str(end_time) + """)
            }
        }
    }"""
    status, data = __call_client_endpoint(query, token)

    if status != 200:
        return False

    data = data.json()["data"]["reportData"]["report"]["playerDetails"]["data"]["playerDetails"]
    for role in data:
        for player in data[role]:
            if player["id"] in pids and player["id"] not in player_data:
                player_data[str(player["id"])] = {
                    "name": player["name"],
                    "class": player["type"]
                }

    # sanity check (should always be false? maybe if the API fails)
    if len([pid for pid in pids if str(pid) not in player_data]) != 0:
        return False

    # append data
    report_data["player_data"] = player_data
    return True


def query_for_encounter_name(token, eid):
    """
    Gets the name of a given encounter ID.
    :param token: The FFLogs API access token to query for the encounter name.
    :param eid: The encounter ID to query for.
    :return: A tuple of (status code, encounter name) if successful, otherwise (status code, None)
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
    status, data = __call_client_endpoint(query, token)
    if status == 200:
        return 200, data.json()['data']['worldData']['encounter']['name']
    else:
        return status, None


def __call_user_endpoint(query: str, token: str) -> Tuple[int, Optional[Response]]:
    """
    Send a query to the FFLogs user endpoint.
    :param query: The query to send.
    :param token: The bearer token.
    :return: A tuple of (Status Code, Data) if successful, otherwise (Status Code, None)
    """
    url = 'https://www.fflogs.com/api/v2/user'
    r = requests.post(url, json={'query': query}, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        return 200, r
    return r.status_code, None


def __call_client_endpoint(query: str, token: str) -> Tuple[int, Optional[Response]]:
    """
    Send a query to the FFLogs client endpoint.
    :param query: The query to send.
    :param token: The bearer token.
    :return: A tuple of (Status Code, Data) if successful, otherwise (Status Code, None)
    """
    url = 'https://www.fflogs.com/api/v2/client'
    r = requests.post(url, json={'query': query}, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        return 200, r
    return r.status_code, None
