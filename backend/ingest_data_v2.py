from typing import List, Dict, Any, Set
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_maria_session
from agent.model import embedding_model
from langchain_milvus import Milvus
from pymilvus import connections, utility, Collection
import os, json

MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
MILVUS_URL = os.getenv("MILVUS_URL")
COLLECTION_NAME = os.getenv("MILVUS_PRODUCT_COLLECTION")
MILVUS_PRODUCT_DETAIL_COLLECTION = os.getenv("MILVUS_PRODUCT_DETAIL_COLLECTION")
MILVUS_PROMOTION_COLLECTION= os.getenv("MILVUS_PROMOTION_COLLECTION")
BATCH_SIZE = 1000

def fetch_products_batch(db: Session, limit=1000, offset=0) -> List[Dict[str, Any]]:
    q = text("""
        SELECT
             id,
             code,
             name,
             name_eng,
             detail,
             cost,
             brand,
             category_l1,
             category_l2,
             key_features,
             key_ingredients,
             suitable_for_concern,
             size_volume,
             usage_instructions,
             notes
        FROM tbl_material
        ORDER BY id
        LIMIT :limit OFFSET :offset
    """)
    return [dict(r) for r in db.execute(q, {"limit": limit, "offset": offset}).mappings().all()]

def build_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    
    return {
        "id": str(row["id"]),
        "code": row.get("code"),
        "name": row.get("name"),
        "name_eng": row.get("name_eng"),
        "detail": row.get("detail"),
        "cost": float(row.get("cost") or 0),
        "brand": row.get("brand"),
        "category_l1": row.get("category_l1"),
        "category_l2": row.get("category_l2"),
        "key_features": row.get("key_features"),
        "key_ingredients": row.get("key_ingredients"),
        "suitable_for_concern": row.get("suitable_for_concern"),
        "size_volume": row.get("size_volume"),
        "usage_instructions": row.get("usage_instructions"),
        "notes": row.get("notes"),
        
        "raw": json.dumps(row, ensure_ascii=False),
    }

def build_text(row: Dict[str, Any]) -> str:
    """ build for rag"""
    def s(x): return "" if x is None else str(x).strip()
    return "\n".join([
        f"ชื่อ: {s(row.get('name'))}",
        f"ชื่ออังกฤษ: {s(row.get('name_eng'))}",
        f"แบรนด์: {s(row.get('brand'))}",
        f"รายละเอียด: {s(row.get('detail'))}",
        f"จุดเด่น: {s(row.get('key_features'))}",
        f"ช่วยแก้ไข: {s(row.get('suitable_for_concern'))}",
    ])

def get_vectorstore() -> Milvus:
    conn_args = {"uri": MILVUS_URL}
    return Milvus(
        embedding_function=embedding_model,
        collection_name=COLLECTION_NAME,
        connection_args=conn_args,
    )

def connect_pymilvus():
    try:
        connections.connect(alias="default", uri=MILVUS_URL)
    except Exception as e:
        print(f"[Milvus] connect warning: {e}")

def upsert_rows(vs: Milvus, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    texts = [build_text(r) for r in rows]
    metadatas = [build_metadata(r) for r in rows]
    ids = [str(r["id"]) for r in rows]

    try:
        vs.delete(ids)
    except Exception as e:
        print(f"[Milvus] delete skip: {e}")
    vs.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    return len(rows)

def ingest_all_product(batch_size: int = BATCH_SIZE) -> int:
    total = 0
    vs = get_vectorstore()
    db = get_maria_session()
    try:
        offset = 0
        while True:
            chunk = fetch_products_batch(db, limit=batch_size, offset=offset)
            if not chunk:
                break
            total += upsert_rows(vs, chunk)
            offset += batch_size
            print(f"Inserted {total}")
    finally:
        db.close()
    return total


def detail_get_vectorstore() -> Milvus:
    conn_args = {"uri": MILVUS_URL}
    return Milvus(
        embedding_function=embedding_model,
        collection_name=MILVUS_PRODUCT_DETAIL_COLLECTION,
        connection_args=conn_args,
    )

def build_detail_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(row["id"]),
        "code": row.get("code"),
        "name": row.get("name"),
        "name_eng": row.get("name_eng"),
        "cost": float(row.get("cost") or 0),
        "detail": row.get("detail"),
        "brand": row.get("brand"),
        "category_l1": row.get("category_l1"),
        "category_l2": row.get("category_l2"),
        "key_features": row.get("key_features"),
        "key_ingredients": row.get("key_ingredients"),
        "suitable_for_concern": row.get("suitable_for_concern"),
        "size_volume": row.get("size_volume"),
        "usage_instructions": row.get("usage_instructions"),
        "notes": row.get("notes"),
        
        "raw": json.dumps(row, ensure_ascii=False),
    }

def build_detail_text(row: Dict[str, Any]) -> str:
    """ build for rag"""
    def s(x): return "" if x is None else str(x).strip()
    return "\n".join([
        f"ชื่อ: {s(row.get('name'))}",
        f"ชื่ออังกฤษ: {s(row.get('name_eng'))}",
    ])

def upsert_rows_detail(vs: Milvus, rows: List[Dict[str, Any]]) -> int:
    if not rows:
        return 0

    texts = [build_detail_text(r) for r in rows]
    metadatas = [build_detail_metadata(r) for r in rows]
    ids = [str(r["id"]) for r in rows]

    try:
        vs.delete(ids)
    except Exception as e:
        print(f"[Milvus] delete skip: {e}")
    vs.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    return len(rows)

def ingest_detail_product(batch_size: int = BATCH_SIZE) -> int:
    total = 0
    vs = detail_get_vectorstore()
    db = get_maria_session()
    try:
        offset = 0
        while True:
            chunk = fetch_products_batch(db, limit=batch_size, offset=offset)
            if not chunk:
                break
            total += upsert_rows_detail(vs, chunk)
            offset += batch_size
            print(f"Inserted {total}")
    finally:
        db.close()
    return total


if __name__ == "__main__":
    n = ingest_detail_product()
    print(f"Done. Inserted {n} products into Milvus collection '{MILVUS_PRODUCT_DETAIL_COLLECTION}'.")