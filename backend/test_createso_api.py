# test_create_order_manual.py
import dotenv
import os
import requests, random, string
from datetime import datetime,timedelta
from agent.module import CreateOrderInput, SoDetail, CreateTicketInput
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

dotenv.load_dotenv()

def _call_create_ticket_api(data: CreateTicketInput) -> dict:

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
    print("PAYLOAD:", payload)

    resp = requests.post(URL, headers=headers, json=payload)

    print("=== DEBUG RESPONSE ===")
    print("RAW TEXT:", resp.text)

    resp = requests.post(URL, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    data = CreateTicketInput(
        category_fullname="สอบถาม > โปรโมชัน",
        customer={
            "name": "สมชาย น้อยใจ",
            "tel": "06302398451",
            "email": "somchainoyjai@gmail.com",
            "birthdate": "2002-01-11",
            "national_id": "1254568741235",
        },
        detail="อยากสอบถามเรื่องปัญหาสิ้นค้าชำรุดเสียหายระหว่างจัดส่ง",
    )

    resp = _call_create_ticket_api(data)
    print("API response:")
    print(resp)

