import os
import fitz
from pydantic import BaseModel, Field
from fastapi import UploadFile
from typing import List

class Product(BaseModel):
    name: str = Field(description="ชื่อของสินค้า (เอาเฉพาะภาษาไทย)")
    name_eng: str = Field(description="ชื่อของสินค้า (เอาเฉพาะภาษาอังกฤษ)")
    detail: str = Field(description="รายละเอียดสินค้า")
    cost: int = Field(description="ราคาสินค้าเป็นตัวเลขเท่านั้น (ไม่ต้องใส่หน่วย)")
    brand: str = Field(description="ยี่ห้อสินค้า")
    category_l1: str = Field(description="หมวดหมู่สินค้าหลัก")
    category_l2: str = Field(description="หมวดหมู่สินค้าย่อย")
    key_features: str = Field(description="คุณสมบัติเด่นของสินค้า")
    key_ingredients: str = Field(description="ส่วนประกอบสำคัญของสินค้า")
    suitable_for_concern: str = Field(description="สิ้นค้าเหมาะสำหรับ")
    size_volume: str = Field(description="ขนาดของสินค้า")
    usage_instructions: str = Field(description="วิธีใช้สินค้า")
    notes: str = Field(description="หมายเหตุ")
    
class ProductList(BaseModel):
    products: List[Product]
    
async def extract_text_from_file(file: UploadFile) -> str:
    file_bytes = await file.read()
    extracted_text = ""
    
    filename = file.filename.lower() if file.filename else ""
    
    try:
        if filename.endswith('.txt'):
            extracted_text = file_bytes.decode('utf-8')

        elif filename.endswith('.pdf'):
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                extracted_text += page.get_text() + "\n"
            doc.close()

        else:
            return f"Error: ระบบรองรับเฉพาะไฟล์ .txt และ .pdf เท่านั้น"

        return extracted_text.strip()

    except Exception as e:
        return f"เกิดข้อผิดพลาดในการอ่านไฟล์: {str(e)}"