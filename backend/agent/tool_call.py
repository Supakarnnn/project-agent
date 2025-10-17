import os
import inspect
from typing import Optional
from langchain.tools import tool
from agent.model import embedding_model
from langchain_milvus import Milvus
import requests
import dotenv

dotenv.load_dotenv()

MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
MILVUS_PRODUCT_COLLECTION = os.getenv("MILVUS_PRODUCT_COLLECTION")
MILVUS_PRODUCT_DETAIL_COLLECTION = os.getenv("MILVUS_PRODUCT_DETAIL_COLLECTION")
MILVUS_PROMOTION_COLLECTION = os.getenv("MILVUS_PROMOTION_COLLECTION")

@tool
async def product_search(query: str, min_price: Optional[int] = None, max_price: Optional[int] = None) -> str:
    """
    ใช้สำหรับแนะนำหรือค้นหาสินค้านจาก Milvus (คืนผลพร้อม score)
    - query = ข้อความที่ต้องการค้นหา
    - min_price, max_price = ถ้ากำหนดจะกรองจาก metadata
    """
    print(f"LLM uses rag_search: q={query}, min={min_price}, max={max_price}")
    try:
        collection = MILVUS_PRODUCT_COLLECTION
        vectorstore = Milvus(
            embedding_function=embedding_model,
            collection_name=collection,
            connection_args={"uri": f"http://{MILVUS_HOST}:{MILVUS_PORT}"},
        )

        price = []
        if min_price is not None: price.append(f"cost >= {min_price}")
        if max_price is not None: price.append(f"cost <= {max_price}")
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
            name = m.get("name") or "(ไม่มีชื่อ)"
            name_eng = m.get("name_eng") or "(ไม่มีชื่อ)"
            detail = m.get("detail") or ""
            brand = m.get("brand")
            category_l1 = m.get("category_l1")
            category_l2 = m.get("category_l2")
            key_features = m.get("key_features")
            suitable_for_concern = m.get("suitable_for_concern")
            size_volume = m.get("size_volume")
            cost = m.get("cost")
            lines.append(f"- {name} | {name_eng} | รายละเอียด: {detail} | แบรนด์: {brand} | หมวดหมู่:{category_l1},{category_l2} | จุดเด่น: {key_features} | ช่วยแก้ไข: {suitable_for_concern} | ขนาด: {size_volume} | ราคา:{cost} | (similarity={sim:.2f})")

        if not lines:
            return f"ไม่สิ้นค้าที่เกี่ยวข้องกับ {query}"

        output = "นี้คือข้อมูลที่ค้นเจอ **พิจารณาข้อมูลก่อนตอบเสมอและสรุปสิ้นค้าสั้น ๆ ให้ลูกค้า** :\n" + "\n".join(lines)
        print(output)
        return output

    except Exception as e:
        print(e)
        return "เครื่องมือมีปัญหา"
    
@tool
async def product_detail_search(name: str) -> str:
    """
    ค้นหา ข้อมูล, จุดเด่น, ส่วนผสม, ช่วยแก้ไข, การใช้งาน ของสิ้นค้าจากชื่อสิ้นค้า
    - name = ชื่อสิ้นค้า (ภาษาไทย, Eng)
    """
    print(f"LLM uses product_detail_search: q={name}")
    try:
        collection = MILVUS_PRODUCT_DETAIL_COLLECTION
        vectorstore = Milvus(
            embedding_function=embedding_model,
            collection_name=collection,
            connection_args={"uri": f"http://{MILVUS_HOST}:{MILVUS_PORT}"},
        )

        k = 5
        results = await vectorstore.asimilarity_search_with_score(name, k=k)
        if not results:
            return f"ไม่สิ้นค้าที่เกี่ยวข้องกับ {name}"

        lines = []
        for doc, dist in results:
            sim = 1.0 - float(dist)
            if sim < 0.2:
                continue

            m = doc.metadata or {}
            name = m.get("name") or "(ไม่มีชื่อ)"
            name_eng = m.get("name_eng") or "(ไม่มีชื่อ)"
            detail = m.get("detail")
            key_features = m.get("key_features")
            key_ingredients = m.get("key_ingredients")
            suitable_for_concern = m.get("suitable_for_concern")
            usage_instructions = m.get("usage_instructions")
            cost = m.get("cost")
            notes = m.get("notes")
            lines.append(f"- {name} | {name_eng} | ราคา: {cost}| รายละเอียด: {detail} | จุดเด่น: {key_features} | ส่วนผสม: {key_ingredients} | ช่วยแก้ปัญหา: {suitable_for_concern} | การใช้งาน: {usage_instructions} | หมายเหตุ: {notes} (similarity={sim:.2f})")

        if not lines:
            return f"ไม่สิ้นค้าที่เกี่ยวข้องกับ {name}"

        output = "นี้คือข้อมูลที่ค้นเจอ **นำข้อมูลที่ค้นเจอตอบตามคำถามของลูกค้า** :\n" + "\n".join(lines)
        print(output)
        return output

    except Exception as e:
        print(e)
        return "เครื่องมือมีปัญหา"

@tool
async def promotion_search(query: str) -> str:
    """
    ค้นหา โปรโมชั่นที่จัดอยู่ของร้าน
    - name = ข้อความที่ต้องการค้นหาหรือข้อมูลที่ต้องการค้นหา
    """
    print(f"LLM uses promotion_search: q={query}")
    try:
        collection = MILVUS_PROMOTION_COLLECTION
        vectorstore = Milvus(
            embedding_function=embedding_model,
            collection_name=collection,
            connection_args={"uri": f"http://{MILVUS_HOST}:{MILVUS_PORT}"},
        )

        k = 5
        results = await vectorstore.asimilarity_search_with_score(query, k=k)
        if not results:
            return f"ไม่สิ้นค้าที่เกี่ยวข้องกับ {query}"

        lines = []
        for doc, dist in results:
            sim = 1.0 - float(dist)
            if sim < 0.05:
                continue

            m = doc.metadata or {}
            name = m.get("ProductName") or "(ไม่มีชื่อ)"
            name_eng = m.get("ProductName_Eng") or "(ไม่มีชื่อ)"
            detail = m.get("ProductDetail")
            cost = m.get("PricePerUnit")
            lines.append(f"- {name} | {name_eng} | ราคา: {cost}| รายละเอียด: {detail} (similarity={sim:.2f})")

        if not lines:
            return f"ไม่โปรโมชั่นที่เกี่ยวข้องกับ {query}"

        output = "นี้คือข้อมูลที่ค้นเจอ **นำข้อมูลที่ค้นเจอตอบตามคำถามของลูกค้า** :\n" + "\n".join(lines)
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