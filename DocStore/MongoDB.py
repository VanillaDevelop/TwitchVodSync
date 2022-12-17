from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(host=os.getenv("MONGODB_URI"), tls=True, tlsCertificateKeyFile=os.getenv("MONGODB_CERT"))
db = client.VodSync
auth_collection = db.auths


def store_auth_keys(user: str, auths: dict):
    auths["user"] = user
    auth_collection.insert_one(auths)


def get_auth_keys(user: str) -> dict:
    """
    Returns stored authentication keys for given user key (email)
    :param user: The e-mail of the user
    :return: Auth keys stored for this user.
    """
    auth = auth_collection.find_one({"user": user})
    if not auth:
        return dict()
    else:
        return auth
