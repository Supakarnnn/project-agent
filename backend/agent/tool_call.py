import os
import dotenv
import inspect
import string, json, random
from typing import Optional, List
from langchain.tools import tool
from agent.model import embedding_model, save_ticket_pg
from langchain_milvus import Milvus
from sqlalchemy import text
import requests
from datetime import datetime, timedelta
from agent.module import CreateOrderInput, CreateTicketInput
from database import get_maria_session, get_db_session
from agent.check_address_data import val_address

dotenv.load_dotenv()

MILVUS_HOST = os.getenv("MILVUS_HOST")
MILVUS_PORT = os.getenv("MILVUS_PORT")
MILVUS_PRODUCT_COLLECTION = os.getenv("MILVUS_PRODUCT_COLLECTION")
MILVUS_PRODUCT_DETAIL_COLLECTION = os.getenv("MILVUS_PRODUCT_DETAIL_COLLECTION")
MILVUS_PROMOTION_COLLECTION = os.getenv("MILVUS_PROMOTION_COLLECTION")

@tool
async def suggest_product_search(query: str, min_price: Optional[int] = None, max_price: Optional[int] = None) -> str:
    """
    Used for product recommendations or searches (returns results with score)
    - query: Descriptive search term in Thai (e.g., 'เซรั่มแก้สิวสำหรับผิวแพ้ง่าย').
    - min_price, max_price: Optional price range filter.
    Note: The results provide a general product overview.
    """
    print(f"LLM uses suggest_product_search: q={query}, min={min_price}, max={max_price}")
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

        k = 7
        results = await vectorstore.asimilarity_search_with_score(query, k=k, expr=expr)
        if not results:
            return f"ไม่สิ้นค้าที่เกี่ยวข้องกับ {query}"

        lines = []
        for doc, dist in results:
            sim = 1.0 - float(dist)
            if sim < 0.15:
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
        return "เครื่องมือมีปัญหาชั่วคราว"
    
@tool
async def product_detail_search(name: str) -> str:
    """
    Retrieve comprehensive product specifications, including the official product_id, 
    key properties , active ingredients, How to use, size_volume, cost, stock_qty, notes and usage instructions.
    - name: The specific product name in Thai or English.
    
    DATA INTEGRITY: Never guess the product_id, usage details, or usage instructions; use only this tool's output.
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
            usage_instructions = m.get("usage_instructions")
            size_volume = m.get("size_volume")
            cost = m.get("cost")
            lines.append(f"- product_id {product_id} | {name} | {name_eng} | รายละเอียด: {detail} | แบรนด์: {brand} | หมวดหมู่:{category_l1},{category_l2} | จุดเด่น: {key_features} | ช่วยแก้ไข: {suitable_for_concern} | วิธีใช้: {usage_instructions} | ขนาด: {size_volume} | ราคา:{cost}")

        if not lines:
            return f"ไม่สิ้นค้าที่เกี่ยวข้องกับ {name}"

        output = "นี้คือข้อมูลที่ค้นเจอ :\n" + "\n".join(lines)
        print(output)
        return output

    except Exception as e:
        print(e)
        return "เครื่องมือมีปัญหาชั่วคราว"
       
@tool
async def promotion_search(query: str) -> str:
    """
    Search for active store promotions, seasonal discounts, or specific marketing campaigns.
    - query: Search terms in Thai related to offers (e.g., 'โปรโมชั่นเดือนนี้', 'ส่วนลดสินค้าสิว', 'แถมฟรี').
    
    Use this tool when the customer asks about deals, discounts, or special offers.
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
    Track and retrieve detailed order status and shipping updates.
    - order_id: The official Sales Order number (Format: 'SO.XXXXXX-XXXXX').
    - name: The customer's full name (Firstname and Lastname).
    
    CRITICAL PRIVACY RULE: Both 'order_id' and 'name' are MANDATORY. 
    If the customer has not provided their full name yet, you MUST ask for it first. 
    DO NOT call this tool if the 'name' is missing or incomplete.
    """
    URL = os.getenv("TRACK_ORDER_API")
    TOKEN = os.getenv("CREATE_ORDER_TOKEN")

    print(f"LLM is try using track_order_tool with {order_id} and {name}")

    headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        }
    payload = {"code": order_id, "name": name}
    try:
        resp = requests.post(URL, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()

    except Exception as e:
        return f"[track_order_tool] เรียก API ไม่สำเร็จ: {e}"
    
    if not data or data.get("success") is not True:
        return f"[track_order_tool] ไม่พบข้อมูลคำสั่งซื้อ (code={order_id}, name={name})"
    
    v = data.get("value") or {}
    customer = v.get("customer") or {}

    so_name = v.get("name") or customer.get("name") or "-"
    tel = (v.get("tel") or customer.get("tel") or "").strip() or "-"
    code = v.get("code") or "-"
    pay_amount = v.get("pay_amount") or "-"
    shipping = v.get("shipping") or "-"
    pay_by = v.get("pay_by") or "-"
    is_payment = v.get("postatus") or "-"

    shipping_code = v.get("shipping_code") or "-"
    address = v.get("address") or "-"

    items = v.get("sodetail") or []
    if items:
        item_lines = []
        for i, it in enumerate(items, start=1):
            pname = it.get("ProductName") or "-"
            qty = it.get("QTY") or "-"
            item_lines.append(f"{i}) {pname} x{qty}")
        items_text = "\n".join(item_lines)
    else:
        items_text = "- ไม่มีรายการสินค้า -"

    summary = (
        "สรุปคำสั่งซื้อจากระบบ CRM\n"
        f"- ชื่อลูกค้า: {so_name}\n"
        f"- เบอร์โทร: {tel}\n"
        f"- รหัสคำสั่งซื้อ (SO): {code}\n"
        f"- ยอดชำระ: {pay_amount} บาท\n"
        f"- ค่าส่ง: {shipping} บาท\n"
        f"- วิธีชำระเงิน: {pay_by}\n"
        f"- สถานะชำระเงิน: {is_payment}\n"
        f"- เลขพัสดุ: {shipping_code}\n"
        f"- ที่อยู่จัดส่ง: {address}\n"
        "รายการสินค้า:\n"
        f"{items_text}"
    )

    return summary
  
@tool
def cancel_order():
    """Tool for cancelling an order."""
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
    """Submit a final purchase order to the system.
    - data: An object containing customer details, shipping address, and order items.
    
    CRITICAL: Every 'product_id' in the 'sodetail' list MUST be an exact integer retrieved 
    from a successful 'product_detail_search' call in the current session.
    STRICTLY PROHIBITED: Do not guess, assume, or fabricate any product_id.
    """
    print("LLM is trying to use create_order")
    print(data.model_dump())

    check = val_address(
    province=data.province, #กรุงเทพ
    district=data.district, #บางกอกน้อย เขต
    subdistrict=data.subdistrict, #อรุณอมรินทร์ แขวง
    zipcode=data.zipcode
    )

    print("INPUT:", {
        "province": data.province,
        "district": data.district,
        "subdistrict": data.subdistrict,
        "zipcode": data.zipcode
    })
    print("CHECK RESULT:", check)

    if not check["ok"]:
        return json.dumps({
            "success": False,
            "error": "ที่อยู่ไม่ถูกต้อง ให้ลูกค้าเช็ค เขต แขวง และ รหัสไปรษณีย์",
            "result": check["reason"]
        }, ensure_ascii=False, indent=2)
    
    else:
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
        print("REAL_PAYLOAD_SENDING:", json.dumps(payload, ensure_ascii=False))
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
            print("final_output", final_output)
            return json.dumps(final_output, ensure_ascii=False, indent=2)

        except Exception as e:
            return f"เกิดข้อผิดพลาดในการส่งคำสั่งซื้อ: {str(e)}"
        
        finally:
            db.close()

@tool
def create_ticket(data: CreateTicketInput, session_id: str) -> str:
    """
    Create an official support ticket for issues that require manual intervention by a human agent.
    USAGE CRITERIA (Use ONLY when):
    1. The customer explicitly requests to talk to a human or "Admin".
    2. The issue involves complex requests like refunds, order cancellations, or complaints that tools cannot handle.
    3. You have reached a dead-end and cannot assist the customer further with available tools.
    
    Input: data = ticket information, session_id = session ID of the current chat.
    Returns: A ticket reference number (e.g., 'SR.XXXXX-XXXXX').
    """

    print("LLM is trying to use create_ticket")
    print(session_id)
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

    external_ok = False
    external_raw = None
    external_error = None
    ticket_code = None

    try:
        resp = requests.post(URL, headers=headers, json=payload)
        resp.raise_for_status()
        external_raw = resp.json()
        # print("=== CREATE TICKET API RESPONSE ===")
        # print(json.dumps(external_raw, ensure_ascii=False, indent=2))
        # print("==================================")

        if external_raw.get("success") is True:
            external_ok = True
            ticket_code = external_raw.get("code")
            print("ticket_code:", ticket_code)
        else:
            external_error = external_raw.get("msg")
    
    except requests.RequestException as e:
        external_error = str(e)
        return f"สร้าง ticket ล้มเหลว: {str(e)}"

    #==========================================#
    if external_ok:
        db = None
        try:
            db = get_db_session()
            db_result = save_ticket_pg(
                db=db,
                session_id=session_id,
                data=data,
                ticket_code=ticket_code,
            )
            # print(db_result)

        except Exception as e:
            db_result = {"ok": False, "error": str(e)}

        finally:
            if db is not None:
                db.close()

        result = {
            "external": {
                "ok": external_ok,
                "error": external_error,
                "raw": external_raw,
            },
            "db": db_result
        }
        print(result)
        return json.dumps(result, ensure_ascii=False)
    #==========================================#

#@tool
#def check_address(district: str, subdistrict:str, zipcode: int, province:str) -> str:


@tool
def get_brands(category_l1: str = None, category_l2: str = None) -> str:
    """
    ค้นหา brand ตาม category
    - category_l1: หมวดหมู่หลัก (Skincare, Makeup, Hair Care, Supplements, Personal Care)
    - category_l2: หมวดหมู่ย่อย (Serum, Sunscreen, Lipstick, Vitamic C, Lotion, Essence, Ampoule, Moisturizer, Hair Treatment, Hair Serum, Hair Oil, Blush, Antioxidant, Cleanser, Body Serum, Mouthwash)
    ถ้าไม่ระบุ parameter จะคืน brand ทั้งหมด
    """
    print("LLM is trying to use get_brand")
    query = "SELECT DISTINCT brand FROM tbl_material WHERE 1=1"
    
    # Use a dictionary for named parameters
    params = {}
    
    if category_l1:
        query += " AND LOWER(category_l1) = LOWER(:category_l1)"
        params["category_l1"] = category_l1
    
    if category_l2:
        query += " AND LOWER(category_l2) = LOWER(:category_l2)"
        params["category_l2"] = category_l2
    
    query += " ORDER BY brand"

    db = get_maria_session()
    
    # Pass the params dictionary directly (no brackets)
    results = db.execute(text(query), params).mappings().all()
    brands = [row["brand"] for row in results]
    
    if not brands:
        return "ไม่พบ brand ในหมวดหมู่นี้"
    
    return f"พบ {len(brands)} brand: {', '.join(brands)}"