import requests


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
                reports(userID:"""+str(uid)+""",page:1)
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
