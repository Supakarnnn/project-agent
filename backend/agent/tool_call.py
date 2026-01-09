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
        return "เครื่องมือมีปัญหาชั่วคราว"
    
@tool
async def product_detail_search(name: str) -> str:
    """
    ค้นหา product_id, ข้อมูล, จุดเด่น, ส่วนผสม, ช่วยแก้ไข, การใช้งาน ของสิ้นค้าจากชื่อสิ้นค้า
    - name = ชื่อสิ้นค้า (ภาษาไทย, Eng)
    """
    print(f"LLM uses product_detail_search: q={name}")
    db = get_maria_session()
    try:
        row = db.execute(
            text("""
                SELECT id,name,name_eng,detail,brand,key_features,key_ingredients,suitable_for_concern,usage_instructions,size_volume,cost,stock_qty,notes,category_l1,category_l2
                FROM tbl_material
                WHERE name LIKE :n OR name_eng LIKE :n
                LIMIT 1
            """),
            {"n": f"%{name}%"}
        ).mappings().first()

        product_data = {
            "product_id": row["id"],
            "ชื่อ": row["name"],
            "ชื่อ (Eng)": row["name_eng"],
            "รายละเอียด": row["detail"],
            "แบรนด์": row["brand"],
            "ประเภทสินค้า": row["category_l1"],
            "ชนิดสินค้า": row["category_l2"],
            "จุดเด่น": row["key_features"],
            "ส่วนประกอบสำคัญ": row["key_ingredients"],
            "ช่วยแก้ไข": row["suitable_for_concern"],
            "คำแนะนำการใช้งาน": row["usage_instructions"],
            "ขนาด": row["size_volume"],
            "ราคา (ต่อ 1 ชิ้น)": row["cost"],
            "คงเหลือในระบบ": row["stock_qty"],
            "หมายเหตุ": row["notes"]
        }

        final_output = {
            "success": True,
            "message": "ดึงข้อมูลสำเร็จ",
            "order": product_data
        }

        print("[product_detail_search] OUTPUT:", final_output)

        return json.dumps(final_output, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"เกิดข้อผิดพลาด: {str(e)}")
        return f"เครื่องมือมีปัญหาชั่วคราว"

    finally:
        db.close()
       
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
    เครื่องมือสำหรับ ติดตามรายละเอียดใบสั่งซื้อสิ้นค้าหรือคำสั่งซื้อ
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
    """เครื่องมือสำหรับสร้างคำสั่งซื้อสิ้นค้า"""
    print("LLM is trying to use create_order")
    # print(data.model_dump())

    check = val_address(
    province=data.province,
    district=data.district,
    subdistrict=data.subdistrict,
    zipcode=data.zipcode
    )

    # print("INPUT:", {
    #     "province": data.province,
    #     "district": data.district,
    #     "subdistrict": data.subdistrict,
    #     "zipcode": data.zipcode
    # })
    # print("CHECK RESULT:", check)

    if not check["ok"]:
        return json.dumps({
            "success": False,
            "error": "ที่อยู่ไม่ถูกต้อง/ไม่พบในฐานข้อมูล",
            "reason": check["reason"]
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
def create_ticket(data: CreateTicketInput, session_id: str) -> str:
    """เครื่องมือสำหรับสร้าง ticket ผ่าน API
    *ใช้เครื่องมือนี้เฉพาะตอนที่คุณให้บริการลูกค้าไม่ได้หรือลูกค้าต้องการคุยกับเจ้าหน้าที่ที่เป็นคน*
    Input: data = ข้อมูลตั๋ว, session_id = session id ของแชทที่กำลังสนทนา
    Output: code = หมายเลขตั๋ว
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

        if external_raw.get("success") is True:
            external_ok = True
            ticket_code = external_raw.get("code")
            # print(external_raw)
            # print(ticket_code)
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