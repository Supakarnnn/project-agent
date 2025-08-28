from pymilvus import connections, list_collections, Collection
from pymilvus.exceptions import MilvusException
import os, dotenv

dotenv.load_dotenv()

def connect_milvus():
    connections.connect(alias="default", host=os.environ.get("MILVUS_HOST"), port=os.environ.get("MILVUS_PORT"))

# from pymilvus import connections

# connections.connect("default", host="172.18.1.225", port="443")

# from pymilvus import utility
# print(utility.list_collections())