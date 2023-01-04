from typing import Optional

from pymongo import MongoClient
import os
from dotenv import load_dotenv

import FFLogs.API

load_dotenv()

client = MongoClient(host=os.getenv("MONGODB_URI"), tls=True, tlsCertificateKeyFile=os.getenv("MONGODB_CERT"))
db = client.VodSync
auth_collection = db.auths
report_collection = db.reports
metadata_collection = db.metadata


# for mapping FFLogs encounter IDs to names
fflogs_encounters = metadata_collection.find_one({"name": "encounter_dict"})["encounter_mappings"]


def store_auth_keys(user: str, auths: dict) -> None:
    """
    Inserts or updates an auths document for given user(name).
    :param user: The user to store the auth document for.
    :param auths: The known auths for the user.
    """
    auths["user"] = user
    if "_id" in auths:
        auth_collection.replace_one({"_id": auths["_id"]}, auths, upsert=True)
    else:
        auth_collection.insert_one(auths)


def get_auth_keys(user: str) -> dict:
    """
    Returns stored authentication keys for given user key (email)
    :param user: The e-mail of the user
    :return: Auth keys stored for this user. An empty dictionary if none exists.
    """
    auth = auth_collection.find_one({"user": user})
    if not auth:
        return dict()
    else:
        return auth


def find_or_load_report(code: str, fflogs_token: str) -> Optional[dict]:
    """
    Attempt to find a report by code. If it doesn't exist, make one attempt to load it from FFLogs using the provided
    token.
    :param code: The report code.
    :param fflogs_token: The fflogs auth token.
    :return: The report data if it could be found or loaded. Otherwise None.
    """
    report = report_collection.find_one({"code": code})
    if not report:
        report = FFLogs.API.get_report_data(fflogs_token, code)
        if report:
            report_collection.insert_one(report)
    return report


def get_filled_encounter_dict(fights: dict, fflogs_token: str) -> dict:
    """
    Returns the encounter dictionary. Ensures that the encounter ID of all fights provided in the fights parameter
    properly resolve to a name.
    :param fights: The fight list for which the names need to be known.
    :param fflogs_token: The fflogs auth token.
    :return: The encounter ID mapping dictionary. Ensures all encounter IDs within fights resolve to a name.
    """
    for fight in fights:
        eid = fight["encounterID"]
        if str(eid) not in fflogs_encounters and eid != 0:
            name = FFLogs.API.query_for_encounter_name(fflogs_token, eid)
            if name:
                fflogs_encounters[str(eid)] = name
            metadata_collection.replace_one({"name": "encounter_dict"},
                                            {"name": "encounter_dict", "encounter_mappings": fflogs_encounters},
                                            upsert=True)
    return fflogs_encounters