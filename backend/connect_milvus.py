from pymilvus import connections, list_collections, Collection, utility
from pymilvus.exceptions import MilvusException
from typing import Any, Dict, List, Optional
import os, dotenv

dotenv.load_dotenv()

MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT= os.getenv("MILVUS_PORT")

def connect_milvus():
    connections.connect(alias="default", host=os.environ.get("MILVUS_HOST"), port=os.environ.get("MILVUS_PORT"))
# print(utility.list_collections())

