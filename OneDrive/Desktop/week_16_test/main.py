from fastapi import FastAPI
import uvicorn
from coniction import Mongo_connection

app = FastAPI()

my_collection = Mongo_connection()

@app.get()
def test():
    return 

