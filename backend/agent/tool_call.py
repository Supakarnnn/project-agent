import os
import inspect
import string, json, random
from typing import Optional, List
from langchain.tools import tool
from agent.model import embedding_model
from langchain_milvus import Milvus
from sqlalchemy import text
import requests
from datetime import datetime, timedelta
from agent.module import CreateOrderInput, CreateTicketInput
import dotenv
from database import get_maria_session

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
    print(f"LLM uses product_search: q={query}, min={min_price}, max={max_price}")
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
            product_id = m.get("id")
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
            lines.append(f"- product_id {product_id} | {name} | {name_eng} | รายละเอียด: {detail} | แบรนด์: {brand} | หมวดหมู่:{category_l1},{category_l2} | จุดเด่น: {key_features} | ช่วยแก้ไข: {suitable_for_concern} | ขนาด: {size_volume} | ราคา:{cost} | (similarity={sim:.2f})")

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
    ค้นหา product_id, ข้อมูล, จุดเด่น, ส่วนผสม, ช่วยแก้ไข, การใช้งาน ของสิ้นค้าจากชื่อสิ้นค้า
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
            product_id = m.get("id")
            name = m.get("name") or "(ไม่มีชื่อ)"
            name_eng = m.get("name_eng") or "(ไม่มีชื่อ)"
            detail = m.get("detail")
            key_features = m.get("key_features")
            key_ingredients = m.get("key_ingredients")
            suitable_for_concern = m.get("suitable_for_concern")
            usage_instructions = m.get("usage_instructions")
            cost = m.get("cost")
            notes = m.get("notes")
            lines.append(f"- product_id {product_id} | {name} | {name_eng} | ราคา: {cost}| รายละเอียด: {detail} | จุดเด่น: {key_features} | ส่วนผสม: {key_ingredients} | ช่วยแก้ปัญหา: {suitable_for_concern} | การใช้งาน: {usage_instructions} | หมายเหตุ: {notes} (similarity={sim:.2f})")

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
def track_order_tool(order_id: str, name: str) -> str:
    """
    เครื่องมือสำหรับ ติดตามใบสั่งซื้อสิ้นค้าหรือคำสั่งซื้อ
    - order_id = code หรือ รหัสใบสั่งซื้อ (SO.XXXXXX-XXXXX)
    - name = ชื่อ-สกุล ลูกค้า 
    """
    print(f"LLM is try using track_order_tool with {order_id} and {name}")
    db = get_maria_session()

    try:
        row = db.execute(
            text("""
                SELECT 
                    name,tel,code,shipping,pay_amount,shipping_code,
                    address,province,district,subdistrict,zipcode,postatus
                FROM tbl_so
                WHERE code = :c AND name = :n
                LIMIT 1
            """),
            {"c": order_id, "n": name}
        ).mappings().first()

        order_data = {
            "name": row["name"],
            "tel": row["tel"],
            "code": row["code"],
            "shipping": float(row["shipping"]) if row["shipping"] else None,
            "pay_amount": float(row["pay_amount"]) if row["pay_amount"] else None,
            "total_amount (ราคาสิ้นค้า + ค่าจัดส่ง)": float(row["shipping"]) + float(row["pay_amount"]),
            "shipping_code": row["shipping_code"],
            "address": row["address"],
            "province": row["province"],
            "district": row["district"],
            "subdistrict": row["subdistrict"],
            "zipcode": str(row["zipcode"]),
            "status": row["postatus"],
        }

        final_output = {
            "success": True,
            "message": "ดึงข้อมูลสำเร็จ",
            "order": order_data
        }

        print("[track_order_tool] OUTPUT:", final_output)

        return json.dumps(final_output, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {str(e)}")
        return f"เกิดข้อผิดพลาด: {str(e)}"

    finally:
        db.close()
    

@tool
def cancel_order():
    """เครื่องมือสำหรับยกเลิกคำสั่งซื้อสิ้นค้า"""
    print("LLM is trying to use cancel_order")
    return "ถ้าลูกค้าจะยกเลิกสั่งซื้อสิ้นค้า ให้คุณสร้าง ticket ให้ลูกค้าด้วย เครื่องมือ create_ticket เพื่อให้เจ้าหน้าที่ที่เป็นมนุษย์ให้บริการแทน"


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
    return tools

@tool
def create_order(data: CreateOrderInput) -> str:
    """เครื่องมือสำหรับสร้างคำสั่งซื้อสิ้นค้าผ่าน API"""
    print("LLM is trying to use create_order")
    # print(data.model_dump())

    def generate_shipping_code(prefix="FLASH", suffix="TH", length=9):
        digits = ''.join(random.choices(string.digits, k=length))
        return f"{prefix}{digits}{suffix}"

    now = datetime.now()
    po_date = now.strftime("%Y-%m-%d")
    recalldate = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    shipping_code = generate_shipping_code()

    URL = os.getenv("CREATE_ORDER_API")
    TOKEN = os.getenv("CREATE_ORDER_TOKEN")

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "name": data.name,
        "tel": data.tel,
        "po_date": po_date,

        "discount": data.discount,
        "discountdetail": data.discountdetail,
        "vat": "0",
        "shipping": 50,
        "pay_amount": data.pay_amount,
        "pay_by": data.pay_by,
        "is_payment": "รอชำระเงิน",
        "payment_date": "",

        "shipping_by": "Flash Express",
        "shipping_date": "",
        "shipping_code": shipping_code,

        "dod": "",
        "remark": "",
        "poaddress": data.poaddress,
        "province": data.province,
        "district": data.district,
        "subdistrict": data.subdistrict,
        "zipcode": data.zipcode,

        "postatus": "รอชำระเงิน",
        "group_id": 1,
        "recalltime": 1,
        "recalldate": recalldate,

        "billing_address": data.billing_address or "",
        "billing_province": data.billing_province or "",
        "billing_district": data.billing_district or "",
        "billing_subdistrict": data.billing_subdistrict or "",
        "billing_zipcode": data.billing_zipcode or "",
        "tax_id": data.tax_id or "",
        "taxtype": data.taxtype or "",
        "media_slot": data.media_slot or "",
        "tax_name": data.tax_name or "",

        "channel": "Online",
        "calllist_id": 0,
        "call_uni_id": "",
        "social_id": "",
        "account_id": "",
        "revised_ref_id": None,

        "sodetail": [item.model_dump() for item in data.sodetail],
    }
    db = get_maria_session()
    try:
        resp = requests.post(URL, headers=headers, json=payload)
        response_data = resp.json()

        shipping_code = response_data.get("value", {}).get("shipping_code")
        so_code = None
        result = db.execute(
            text("""
                SELECT code
                FROM tbl_so
                WHERE shipping_code = :sc
                LIMIT 1
            """),{"sc": shipping_code}
        ).fetchone()
        if result:
                so_code = result[0]

        final_output = {
            "api_response": response_data,
            "Order number": so_code
        }
        return json.dumps(final_output, ensure_ascii=False, indent=2)

    except Exception as e:
        return f"เกิดข้อผิดพลาดในการส่งคำสั่งซื้อ: {str(e)}"
    
    finally:
        db.close()
    
@tool
def how_to_check_out():
    """เครื่องมือสำหรับบอกขั้นตอนการชำระเงิน"""
    print("LLM is trying to use how_to_check_out")
    DATA = """
ขั้นตอนการชำระเงิน
1. ไปที่หน้าชำระเงิน (ด้านขวาบนของหน้าจอ หัวข้อ 'Payment')
2. นำ รหัสคำสั่งซื้อ (SO.XXXXXX-XXXXX) กรอกตรงช่องชำระเงินด้วย รหัสคำสั่งซื้อ
3. ทำการชำระเงิน
4. เมื่อชำระเงินแล้วให้กดปุ่ม "ยืนยันการชำระเงิน"
"""
    return DATA

@tool
def create_ticket(data: CreateTicketInput) -> str:
    """เครื่องมือสำหรับสร้าง ticket ผ่าน API
    *ใช้เครื่องมือนี้เฉพาะตอนที่คุณให้บริการลูกค้าไม่ได้หรือลูกค้าต้องการคุยกับเจ้าหน้าที่ที่เป็นคน*
    Output: code = หมายเลขตั๋ว
    """

    print("LLM is trying to use create_ticket")
    print(data.model_dump())

    URL = os.getenv("CREATE_TICKET_API")
    TOKEN = os.getenv("CREATE_ORDER_TOKEN")

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "status": "Open",
        "category_fullname": data.category_fullname,
        "channel": "inbound call",
        "channel_detail": "Hotline 02-123-4567",
        "form_name": "default",
        "assign": {
            "id": 1
        },
        "group_emp": 1,
        "customer": data.customer.model_dump(),
        "detail": data.detail
    }

    try:
        resp = requests.post(URL, headers=headers, json=payload)
        response_data = resp.json()
        return json.dumps(response_data, ensure_ascii=False)
    
    except requests.RequestException as e:
        return f"สร้าง ticket ล้มเหลว: {str(e)}"