from pymongo import MongoClient
from config import settings

client = MongoClient(settings.mongodb_url)
db = client[settings.database_name]

def get_db():
    return db