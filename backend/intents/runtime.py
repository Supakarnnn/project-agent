from typing import Dict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

async def get_session_state(db: AsyncSession, session_id: str) -> Dict:
    result = await db.execute(text("""
        SELECT active_intent, dialog_status, last_activity_at
        FROM chat_sessions
        WHERE id = :sid
        LIMIT 1
    """), {"sid": session_id})
    row = result.mappings().first()

    if not row:
        return {"active_intent": None, "status": "idle", "last_updated": None}

    return {
        "active_intent": row["active_intent"],
        "status": row["dialog_status"] or "idle",
        "last_updated": row["last_activity_at"],
    }


async def save_session_state(db: AsyncSession, session_id: str, state: Dict) -> None:
    await db.execute(text("""
        UPDATE chat_sessions
        SET
          active_intent = :ai,
          dialog_status = :st
        WHERE id = :sid
    """), {
        "sid": session_id,
        "ai": state.get("active_intent"),
        "st": state.get("status") or "idle",
    })
    await db.commit()
