import os
import inspect
from typing import Optional, Literal
from langchain.tools import tool
from agent.model import embedding_model
from langchain_milvus import Milvus
import requests
import dotenv

dotenv.load_dotenv()

MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
MILVUS_PRODUCT_COLLECTION = os.getenv("MILVUS_PRODUCT_COLLECTION")

@tool
async def rag_search(query: str, min_price: Optional[int] = None, max_price: Optional[int] = None, item_type: Literal["any","product","promotion"] = "any") -> str:
    """
    ค้นหาสินค้านจาก Milvus คืนผลพร้อม score
    - query = ข้อความที่ต้องการค้นหา
    - min_price, max_price = ถ้ากำหนดจะกรองจาก metadata
    - item_type = ถ้าผู้ใช้ถามหา "โปร/โปรโมชั่น/ส่วนลด/ซื้อ 1 แถม 1" ให้ตั้ง item_type="promotion"
    """
    print(f"LLM uses rag_search: q={query}, min={min_price}, max={max_price}, type={item_type}")
    try:
        collection = MILVUS_PRODUCT_COLLECTION
        vectorstore = Milvus(
            embedding_function=embedding_model,
            collection_name=collection,
            connection_args={"uri": f"http://{MILVUS_HOST}:{MILVUS_PORT}"},
        )

        price = []
        if min_price is not None: price.append(f"PricePerUnit >= {min_price}")
        if max_price is not None: price.append(f"PricePerUnit <= {max_price}")
        if item_type == "product": price.append(f"is_promotion == false")
        elif item_type == "promotion": price.append(f"is_promotion == true")
        expr = " and ".join(price) if price else None

        k = 10
        results = await vectorstore.asimilarity_search_with_score(query, k=k, expr=expr)
        if not results:
            return f"ไม่สิ้นค้าที่เกี่ยวข้องกับ {query}"

        lines = []
        for doc, dist in results:
            sim = 1.0 - float(dist)
            if sim < 0.05:
                continue

            m = doc.metadata or {}
            name = m.get("ProductName") or "(ไม่มีชื่อ)"
            detail = m.get("ProductDetail") or ""
            price = m.get("PricePerUnit")
            stock = m.get("is_stock")
            price_txt = f"{price:.0f} บาท" if isinstance(price, (int, float)) else "-"
            stock_txt = "มีสต๊อก" if stock else "หมดสต๊อก"
            lines.append(f"- {name} | {detail} | {price_txt} | {stock_txt} (similarity={sim:.2f})")

        if not lines:
            return f"ไม่สิ้นค้าที่เกี่ยวข้องกับ {query}"

        output = "นี้คือข้อมูลที่ค้นเจอ **พิจารณาข้อมูลก่อนตอบเสมอและสรุปสิ้นค้าสั้น ๆ ให้ลูกค้า** :\n" + "\n".join(lines)
        print(output)
        return output

    except Exception as e:
        print(e)
        return "เครื่องมือมีปัญหา"

@tool
def for_list_collections():
    """เครื่องมือสำหรับดูข้อมูล collection ใน Milvus Vector Database ผ่าน API"""
    print("LLM is trying to use test_list_collections")
    try:
        response = requests.get("http://localhost:8001/admin/get-collections-ai")
        response.raise_for_status()
        collections = response.json().get("collections", [])
        return ", ".join(str(c) for c in collections)
    
    except Exception:
        return "ไม่มี collection"

@tool
def track_order_tool(order_id: str) -> str:
    """เครื่องมือสำหรับ ติดตามการจัดส่งสิ้นค้า"""
    print(f"LLM is try using track_order_tool with {order_id}")
    return f"สถานะของออเดอร์ {order_id} คือ: กำลังจัดส่ง"

@tool
def create_order():
    """เครื่องมือสำหรับสร้างคำสั่งซื้อสิ้นค้า"""
    print("LLM is trying to use create_order")
    return "ระบบยังไม่พร้อม"

@tool
def cancel_order():
    """เครื่องมือสำหรับยกเลิกคำสั่งซื้อสิ้นค้า"""
    print("LLM is trying to use cancel_order")
    return "ระบบยังไม่พร้อม"


def get_registered_tools():
    tools = {}
    exclude_names = ["tool", "get_registered_tools"]
    for name, obj in globals().items():
        if name in exclude_names:
            continue
        # LangChain tool
        if hasattr(obj, "name") and hasattr(obj, "description"):
            sig = ""
            if hasattr(obj, "func") and inspect.isfunction(obj.func):
                sig = str(inspect.signature(obj.func))
            tools[name] = {
                "parameter": sig,
                "description": obj.description,
                "type": "langchain_tool"
            }
        # normal function
        elif inspect.isfunction(obj):
            sig = str(inspect.signature(obj))
            doc = inspect.getdoc(obj) or ""
            tools[name] = {
                "parameter": sig,
                "description": doc,
                "type": "normal_function"
            }
    return tools