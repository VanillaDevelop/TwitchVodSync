from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(host=os.getenv("MONGODB_URI"), tls=True, tlsCertificateKeyFile=os.getenv("MONGODB_CERT"))
db = client.VodSync
