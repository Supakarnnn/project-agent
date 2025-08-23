import os
from langchain.tools import tool
from agent.model import embedding_model
from langchain_milvus import Milvus
import requests
import dotenv

dotenv.load_dotenv()

# @tool
# async def rag_search(query: str) -> str:
#     """ใช้สำหรับค้นหาข้อมูลทั่วไปที่เกี่ยวข้องกับ บริการ, สินค้า, โซลูชั่น, ข้อมูลการติดต่อของบริษัท โดยอิงจากเอกสารที่มีอยู่ในระบบผ่าน RAG (Retrieval-Augmented Generation)"""

#     print(f"LLM is try using rag_search tool, query = {query}")
    
#     vectorstore = Milvus(
#         embedding_function=embedding_model,
#         collection_name="Normal_docs",
#         connection_args={"host": "localhost", "port": "19530"},
#     )
#     retriever = vectorstore.similarity_search_with_score(search_type="similarity", search_kwargs={"k": 3})
#     docs = await retriever.ainvoke(query)

#     if not docs:
#         return "ไม่พบข้อมูลที่เกี่ยวข้อง"

#     content = "\n\n".join([f"- {doc.page_content}" for doc in docs])
#     return f"{content}"


@tool
def test_list_collections():
    """เครื่องมือสำหรับดูข้อมูล collection ใน Milvus Vector Database ผ่าน API"""
    print("LLM is trying to use test_list_collections")
    try:
        response = requests.get("http://localhost:8001/get-collections-ai")
        response.raise_for_status()
        collections = response.json().get("collections", [])
        return ", ".join(str(c) for c in collections)
    
    except Exception:
        return "ไม่มี collection"


def track_order_tool(order_id: str) -> str:
    """เครื่องมือสำหรับ ติดตามการจัดส่งสิ้นค้า"""
    print(f"LLM is try using track_order_tool with {order_id}")
    return f"สถานะของออเดอร์ {order_id} คือ: กำลังจัดส่ง"