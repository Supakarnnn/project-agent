from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Message(BaseModel):
    role: Literal["ai", "human", "system"]
    content: str

class RequestMessage(BaseModel):
    messages: List[Message]

class AgentResponse(BaseModel):
    response: str
    plan: Optional[str]
    query: Optional[str]
    report: Optional[str]
    graph: Optional[str]

class CollectionCreate(BaseModel):
    name: str
    dim: int = 1024
    description: Optional[str] = None

class WebURL(BaseModel):
    url: str

class ConfigUpdate(BaseModel):
    model: str
    temperature: Optional[float] = 0.2
    top_p: Optional[float] = 0 
    system_prompt: str

class LoginIn(BaseModel):
    name: str
    password: str

class IntentCreate(BaseModel):
    name: str
    tool_name: str
    description: str

class SoDetail(BaseModel):
    """รายละเอียดสินค้าในคำสั่งซื้อ 1 รายการ"""
    product_id: int = Field(..., description="รหัสสินค้า")
    line: int = Field(..., description="ลำดับบรรทัดในใบสั่งซื้อ")
    QTY: int = Field(..., description="จำนวนชิ้น")

class CreateOrderInput(BaseModel):
    #important
    name: str = Field(..., description="ชื่อผู้สั่งซื้อ")
    tel: str = Field(..., description="เบอร์โทรลูกค้า")

    discount: str = Field(..., description="ส่วนลด (ไม่มีใส่ 0)")
    discountdetail: str = Field(..., description="ส่วนลด (ไม่มีใส่ 0%)")
    pay_amount: float = Field(..., description="ยอดที่ต้องชำระสุดท้าย")
    pay_by: str = Field(..., description="ช่องทางการชำระเงิน เช่น โอนเงิน, เก็บปลายทาง")

    poaddress: str = Field(..., description="ที่อยู่สำหรับจัดส่ง")
    province: str = Field(..., description="จังหวัด")
    district: str = Field(..., description="อำเภอ/เขต")
    subdistrict: str = Field(..., description="ตำบล/แขวง")
    zipcode: str = Field(..., description="รหัสไปรษณีย์")

    #Optional
    billing_address: Optional[str] = Field(None, description="ที่อยู่สำหรับออกบิล/ใบกำกับภาษี (ถ้ามี)")
    billing_province: Optional[str] = None
    billing_district: Optional[str] = None
    billing_subdistrict: Optional[str] = None
    billing_zipcode: Optional[str] = None
    tax_id: Optional[str] = Field(None, description="เลขประจำตัวผู้เสียภาษี (ถ้ามี)")
    taxtype: Optional[str] = Field(None, description="ประเภทภาษี เช่น ภ.พ.20 ฯลฯ")
    media_slot: Optional[str] = Field(None, description="ช่องทาง/แคมเปญการตลาด (ถ้ามี)")
    tax_name: Optional[str] = Field(None, description="ชื่อสำหรับออกใบกำกับภาษี (ถ้ามี)")

    #product list
    sodetail: List[SoDetail] = Field(
        ...,
        description="ลิสต์รายการสินค้าแต่ละบรรทัดในคำสั่งซื้อ"
    )

class ticketCustomer(BaseModel):
    name: str = Field(..., description="ชื่อลูกค้า")
    tel: str = Field(..., description="เบอร์โทรลูกค้า")
    email: str = Field(..., description="อีเมลลูกค้า")
    birthdate: str = Field(..., description="วันเกิดลูกค้า รูปแบบ YYYY-MM-DD")
    national_id: str = Field(..., description="เลขบัตรประชาชนลูกค้า")

class CreateTicketInput(BaseModel):
    category_fullname: str = Field(..., description="หมวดหมู่เคส 1.'สอบถาม > โปรโมชัน' 2.'รับแจ้ง' 3.'ร้องเรียน' 4.'เปิดใบสั่งซื้อ'")
    customer: ticketCustomer = Field(..., description="ข้อมูลลูกค้า")
    detail: str = Field(..., description="รายละเอียดที่ลูกค้าสอบถาม")