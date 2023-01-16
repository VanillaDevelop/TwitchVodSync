import base64
import time
from typing import Optional

from pymongo import MongoClient
import os
from dotenv import load_dotenv

import FFLogs.API

load_dotenv()

if not os.path.isfile(os.getenv("MONGODB_CERT")):
    with open(os.getenv("MONGODB_CERT"), "w") as f:
        f.write(base64.b64decode(os.getenv("CERTFILE")).decode("utf-8"))

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


def find_or_load_report(code: str, fflogs_token: str, update: bool = False, unknown: bool = False) -> (int, Optional[dict]):
    """
    Attempt to find a report by code. If it doesn't exist, make one attempt to load it from FFLogs using the provided
    token.
    :param code: The report code.
    :param fflogs_token: The fflogs auth token.
    :param update: If True, try to refresh the log if it is found in the database.
    :param unknown: Whether to include unknown encounters (ID=0). Only on update from database.
    :return: A status code, and the report data if it could be found or loaded. Otherwise None.
    """
    report = report_collection.find_one({"code": code})
    status = 200
    if not report:
        status, report = FFLogs.API.get_report_data(fflogs_token, code)
        if status == 200:
            if report is not None:
                report_collection.insert_one(report)
            else:
                status = 800  # random error code to signify that the report is empty
    else:
        if update and time.time() - report["loaded_at"] > 2 * 60:
            old_id = report["_id"]
            status, report = FFLogs.API.try_update_report(fflogs_token, report, unknown=unknown)
            if status == 200:
                report["_id"] = old_id
                report_collection.replace_one({"_id": old_id}, report, upsert=True)

    if report and "_id" in report:
        del report["_id"]
    return status, report


def get_filled_encounter_dict(fights: dict, fflogs_token: str) -> (int, Optional[dict]):
    """
    Returns the encounter dictionary for the encounter ID of all fights provided in the fights parameter.
    :param fights: The fight list for which the names need to be known.
    :param fflogs_token: The fflogs auth token.
    :return: The query status and the encounter ID mapping dictionary. If the status is 200, this function guarantees
    all non-zero encounter IDs within fights resolve to a name.
    """
    status = 200
    for fight in fights:
        eid = fight["encounterID"]
        if str(eid) not in fflogs_encounters:
            if str(eid) == "0":
                fflogs_encounters["0"] = "Undefined Zone"
                continue
            status, name = FFLogs.API.query_for_encounter_name(fflogs_token, eid)
            if status == 200:
                fflogs_encounters[str(eid)] = name
                metadata_collection.replace_one({"name": "encounter_dict"},
                                                {"name": "encounter_dict", "encounter_mappings": fflogs_encounters},
                                                upsert=True)
            else:
                break
    required_keys = set([fight["encounterID"] for fight in fights])
    return status, {k: v for k, v in fflogs_encounters.items() if int(k) in required_keys}
