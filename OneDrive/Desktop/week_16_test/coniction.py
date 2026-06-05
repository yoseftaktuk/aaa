from pymongo import MongoClient
from settings import settings



class Mongo_connection:
    def __init__(self):
        try:
            self.client = MongoClient(
                host=settings.MONGO_HOST,
                port=settings.MONGO_PORT,
                username=settings.MONGO_USERNAME,
                password=settings.MONGO_PASSWORD,
                authSource=settings.MONGO_AUTH_SOURCE
            )
        except ConnectionRefusedError as e:
            return str(e)    
        self.db = self.client[settings.MONGO_DB]
        self.db.create_collection(name=settings.MONGO_COLLECTION)  
        self.collection = self.db[settings.MONGO_COLLECTION]
        return self.collection.admin._command('ping')
        
        
    