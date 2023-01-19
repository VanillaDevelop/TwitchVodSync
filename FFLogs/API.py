import time
from typing import Tuple, Optional
import requests
from requests import Response


def get_username(token: str) -> Optional[dict]:
    """
    Query for the username of the user who this access token belongs to.
    :param token: The FFLogs API access token.
    :return: A dictionary containing id and name keys for the user who this access token belongs to.
    If this call fails (status code != 200), None is returned.
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

    status, data = __call_user_endpoint(token, query)
    if status == 200:
        return data.json()['data']['userData']['currentUser']
    else:
        return None


def get_report_data(token: str, code: str) -> Tuple[int, Optional[dict]]:
    """
    Load a report from FFLogs.
    :param token: The FFLogs API access token.
    :param code: The report code.
    :return: A tuple of (status, data) if successful, otherwise (status, None).
    """

    # get basic report
    status, data = __load_base_report(token, code)
    if status != 200:
        return status, None
    # append death data
    if not __append_death_info(token, data):
        return 800, None
    # append player data
    if not __append_player_info(token, data):
        return 800, None
    # If all data was loaded successfully, append the current time to the data and return it.
    data["loaded_at"] = time.time()
    return 200, data


def try_update_report(token: str, previous_report: dict, unknown=False) -> Tuple[int, Optional[dict]]:
    """
    Try and refresh an existing report with additional data.
    :param token: The FFLogs API access token.
    :param previous_report: The previous state of the report.
    :param unknown: Whether to keep or dismiss encounters with ID 0 (default: False).
    :return: A tuple of (status, data) if successful, otherwise (status, None).
    """
    # get basic report
    status, data = __load_base_report(token, previous_report["code"], unknown)
    if status != 200:
        return status, None
    # append data from previous report
    data["player_data"] = previous_report["player_data"]
    data["deaths"] = previous_report["deaths"]
    data["last_queried_death_timestamp"] = previous_report["last_queried_death_timestamp"]
    # update death data
    if not __append_death_info(token, data):
        return 800, None
    # update player data
    if not __append_player_info(token, data):
        return 800, None
    # If all data was loaded successfully, append the current time to the data and return it.
    data["loaded_at"] = time.time()
    return 200, data


def query_for_encounter_name(token: str, eid: int) -> Tuple[int, Optional[str]]:
    """
    Gets the name of a given encounter ID.
    :param token: The FFLogs API access token.
    :param eid: The encounter ID to query for.
    :return: A tuple of (status code, encounter name) if successful, otherwise (status code, None).
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
    status, data = __call_client_endpoint(token, query)
    if status == 200:
        try:
            name = data.json()['data']['worldData']['encounter']['name']
            return 200, name
        except (TypeError, KeyError):
            # If we get 200 but the name isn't in the data, just place it as unknown zone.
            # For example, this happens with dungeons. (They do not have an "encounter name").
            return 200, "Unknown Zone"
    else:
        return status, None


def __load_base_report(token: str, code: str, unknown: bool = False) -> Tuple[int, Optional[dict]]:
    """
    Try to load the basic report structure for a given code.
    :param token: The FFLogs API access token.
    :param code: The report code.
    :param unknown: Whether to keep or dismiss encounters with ID 0.
    :return: A tuple of (status, data) if successful, otherwise (status, None).
    """

    query = """
    query
    {
        reportData
        {
            report(code: \"""" + code + """\")
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
    status, data = __call_client_endpoint(token, query)
    if status != 200:
        return status, None
    else:
        data = data.json()['data']['reportData']['report']
        # if there is no data in the report, return a custom error code.
        if not data:
            return 800, None

        # remove trash fights unless unknown fights should be included
        if not unknown:
            data["fights"] = [fight for fight in data["fights"] if fight["encounterID"] != 0]

        # change the timestamps from milliseconds to seconds
        data["startTime"] = round(data["startTime"] / 1000, 0)
        data["endTime"] = round(data["endTime"] / 1000, 0)
        for fight in data["fights"]:
            fight["startTime"] = data["startTime"] + round(fight["startTime"] / 1000, 0)
            fight["endTime"] = data["startTime"] + round(fight["endTime"] / 1000, 0)

        # append report ID to data
        data["code"] = code

        # order fights by their end time (latest pull first)
        data["fights"].sort(key=lambda x: x["endTime"], reverse=True)

        # return the data
        return 200, data


def __append_death_info(token: str, report_data: dict) -> bool:
    """
    Append death information to a given report.
    :param token: The FFLogs API access token.
    :param report_data: The report data (collected by the __load_base_report function).
    :return: True if successful, false if not. If true, the death data is appended to report_data.
    """

    # Deal with the special case when there are no valid fights in the report.
    if len(report_data["fights"]) == 0:
        report_data["deaths"] = []
        report_data["last_queried_death_timestamp"] = 0
        return True

    # if we already queried for previous pulls, we can get it from the report data
    if "last_queried_death_timestamp" in report_data and report_data["last_queried_death_timestamp"] > 0:
        previous_timestamp = report_data["last_queried_death_timestamp"]
    else:
        # Otherwise, we start at the earliest pull in the report.
        previous_timestamp = int(report_data["fights"][-1]["startTime"] - report_data["startTime"]) * 1000

    # this is the last timestamp for which we need to query
    last_timestamp = int(report_data["fights"][0]["endTime"] - report_data["startTime"]) * 1000

    deaths = []
    previous_status = 200

    # iterate over deaths until we reach the last timestamp
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
        previous_status, data = __call_client_endpoint(token, death_query)
        if previous_status != 200:
            break

        data = data.json()["data"]["reportData"]["report"]["events"]
        if "data" in data:
            for death in data["data"]:
                deaths.append({
                    "timestamp": report_data["startTime"] + round(death["timestamp"] / 1000, 0),
                    "targetID": death["targetID"],
                    "fight": death["fight"],
                })
        if data["nextPageTimestamp"]:
            previous_timestamp = data["nextPageTimestamp"]
        else:
            previous_timestamp = None

    # if one of the queries failed, return false
    if previous_status != 200:
        return False

    # append the death data to the report data
    report_data["last_queried_death_timestamp"] = last_timestamp
    if "deaths" not in report_data:
        report_data["deaths"] = deaths
    else:
        report_data["deaths"] = report_data["deaths"] + deaths
    return True


def __append_player_info(token: str, report_data: dict) -> bool:
    """
    Append player information to a given report.
    :param token: The FFLogs API access token.
    :param report_data: The report data (collected by the __load_base_report function, and with appended deaths).
    :return: True if successful, false if not. If true, player_data is appended to report_data.
    """

    # Requires the report to have death data appended.
    if "deaths" not in report_data:
        return False

    # If there are no deaths, we can just return an empty list.
    if len(report_data["deaths"]) == 0:
        report_data["player_data"] = {}
        return True

    # get and parse the time range
    end_time = int(report_data["fights"][0]["endTime"] - report_data["startTime"]) * 1000
    start_time = int(report_data["fights"][-1]["startTime"] - report_data["startTime"]) * 1000

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
    status, data = __call_client_endpoint(token, query)

    if status != 200:
        return False

    # unpack the data
    data = data.json()["data"]["reportData"]["report"]["playerDetails"]["data"]["playerDetails"]
    for role in data:
        for player in data[role]:
            if player["id"] in pids and player["id"] not in player_data:
                player_data[str(player["id"])] = {
                    "name": player["name"],
                    "class": player["type"]
                }

    # If a player name was not found, we just place an unknown player. Not really worth returning failure over.
    player_data = player_data | {pid: {"name": "Unknown", "class": "Unknown"}
                                 for pid in pids if str(pid) not in player_data}

    # append data
    report_data["player_data"] = player_data
    return True


def __call_user_endpoint(token: str, query: str) -> Tuple[int, Optional[Response]]:
    """
    Send a query to the FFLogs user endpoint.
    :param token: The bearer token.
    :param query: The query to send.
    :return: A tuple of (Status Code, Data) if successful, otherwise (Status Code, None)
    """
    url = 'https://www.fflogs.com/api/v2/user'
    r = requests.post(url, json={'query': query}, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        return 200, r
    return r.status_code, None


def __call_client_endpoint(token: str, query: str) -> Tuple[int, Optional[Response]]:
    """
    Send a query to the FFLogs client endpoint.
    :param token: The bearer token.
    :param query: The query to send.
    :return: A tuple of (Status Code, Data) if successful, otherwise (Status Code, None)
    """
    url = 'https://www.fflogs.com/api/v2/client'
    r = requests.post(url, json={'query': query}, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        return 200, r
    return r.status_code, None
