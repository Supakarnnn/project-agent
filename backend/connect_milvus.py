from pymilvus import connections, list_collections, Collection
from pymilvus.exceptions import MilvusException
import os, dotenv

dotenv.load_dotenv()

def connect_milvus():
    connections.connect(alias="default", host=os.environ.get("MILVUS_HOST"), port=os.environ.get("MILVUS_PORT"))

# if connections.has_connection("default"):
#     print("milvus connected")
# else:
#     print("cant connect milvus")


