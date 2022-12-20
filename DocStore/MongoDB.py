from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(host=os.getenv("MONGODB_URI"), tls=True, tlsCertificateKeyFile=os.getenv("MONGODB_CERT"))
db = client.VodSync
auth_collection = db.auths


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
