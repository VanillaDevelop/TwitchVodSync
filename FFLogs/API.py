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
    if status == 200:
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
        return 200, data
    else:
        return status, None


def __append_death_info(token, report_data, start_time):
    """
    Append death information for a given report
    :param token: The user access token
    :param report_data: The report data (collected by the get_report_data function)
    :param start_time: The earliest time to collect death data from
    :return: True if successful, false if not. If true, the death data is appended to report_data.
    """

    last_timestamp = report_data["fights"][0]["endTime"] # last pull should be first

    death_query = """
    query
    {
            reportData
            {
                    report(code: \"""" + report_data["code"] + """\")
                    {
                        events(dataType: Deaths, startTime: """ + start_time + """, endTime: """ + last_timestamp + """)
                        {
                            data,
                            nextPageTimestamp
                        }
                    }
            }
    }"""
    
    status, data = __call_client_endpoint(death_query, token)
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
