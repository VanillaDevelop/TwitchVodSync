from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(host=os.getenv("MONGODB_URI"))
db = client.VodSync

