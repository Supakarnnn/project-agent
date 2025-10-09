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

def collection_summary(name: str) -> Dict[str, Any]:
    """Basic summary info for a collection (schema, num_entities, indexes, partitions, load state)."""
    c = Collection(name)  # lazy
    info: Dict[str, Any] = {
        "name": name,
        "num_entities": 0,
        "loaded": False,
        "schema": None,
        "indexes": [],
        "partitions": [],
    }

    # num entities
    try:
        info["num_entities"] = c.num_entities
    except Exception:
        pass

    # schema
    try:
        info["schema"] = c.schema.to_dict() if c.schema else None
    except Exception:
        pass

    # indexes
    try:
        for idx in (c.indexes or []):
            params = getattr(idx, "params", {}) or {}
            info["indexes"].append({
                "index_name": params.get("index_name"),
                "field": params.get("field_name"),
                "index_type": params.get("index_type"),
                "metric_type": params.get("metric_type"),
                "params": params.get("index_params"),
            })
    except Exception:
        pass

    # partitions
    try:
        for p in c.partitions:
            info["partitions"].append({
                "name": p.name,
                "num_entities": p.num_entities,
            })
    except Exception:
        pass

    # load state
    try:
        info["loaded"] = utility.load_state(name).is_loaded
    except Exception:
        pass

    return info


def primary_key_field(c: Collection) -> Optional[str]:
    try:
        for f in c.schema.fields:
            if getattr(f, "is_primary", False):
                return f.name
    except Exception:
        pass
    return None

