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
BATCH_SIZE = 1000

def fetch_products_batch(db: Session, limit=1000, offset=0) -> List[Dict[str, Any]]:
    q = text("""
        SELECT
          id,
          ProductName_Eng,
          ProductName,
          ProductDetail,
          PricePerUnit,
          is_stock,
          barcode
        FROM tbl_product
        ORDER BY id
        LIMIT :limit OFFSET :offset
    """)
    return [dict(r) for r in db.execute(q, {"limit": limit, "offset": offset}).mappings().all()]


def build_text(row: Dict[str, Any]) -> str:
    def s(x): return "" if x is None else str(x).strip()
    return "\n".join([
        f"ชื่อ: {s(row.get('ProductName'))}",
        f"ชื่ออังกฤษ: {s(row.get('ProductName_Eng'))}",
        f"รายละเอียด: {s(row.get('ProductDetail'))}",
    ])

def build_metadata(row: Dict[str, Any]) -> Dict[str, Any]:
    barcode = str(row.get("barcode") or "")
    return {
        "id": str(row["id"]),
        "ProductName": row.get("ProductName"),
        "ProductName_Eng": row.get("ProductName_Eng"),
        "ProductDetail": row.get("ProductDetail"),
        "PricePerUnit": float(row.get("PricePerUnit") or 0),
        "is_stock": str(row.get("is_stock")).strip().upper() in ("T","TRUE","1","YES","Y"),
        "barcode": barcode,
        "is_promotion": barcode.upper().startswith("PT"),
        "raw": json.dumps(row, ensure_ascii=False),
    }

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
    vs.add_texts(texts=texts, metadatas=metadatas, ids=ids)
    return len(rows)

def ingest_all(batch_size: int = BATCH_SIZE) -> int:
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
            print(f"[Ingest] Inserted {total} rows so far...")
    finally:
        db.close()
    return total


if __name__ == "__main__":
    n = ingest_all()
    print(f"Done. Inserted {n} products into Milvus collection '{COLLECTION_NAME}'.")

    
