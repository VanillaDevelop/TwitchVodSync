import requests


def get_username(token):
    query = """query {
                   userData
                   {
                       currentUser
                       {
                           name
                       }
                   }
               }"""
    r = __call_user_endpoint(query, token)
    if r:
        return r.json()['data']['userData']['currentUser']['name']
    else:
        return None


def __call_user_endpoint(query, token):
    url = 'https://www.fflogs.com/api/v2/user'
    r = requests.post(url, json={'query': query}, headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        return r
    return None
