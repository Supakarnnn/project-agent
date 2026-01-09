from sqlalchemy import text
from sqlalchemy.orm import Session
import json

SESSION_TIMEOUT_MIN = 15

def autoclose_inactive_sessions(db):
    q = text("""
            WITH to_close AS (
            SELECT id, started_at, last_activity_at
            FROM chat_sessions
            WHERE status = 'open'
                AND (now() - last_activity_at) > (:gap * interval '1 minute')
            )
            UPDATE chat_sessions AS s
            SET
                status = 'closed',
                dialog_status = 'closed',
                closed_at = c.last_activity_at + (:gap * interval '1 minute'),
                total_duration_sec = EXTRACT(
                    EPOCH FROM ((c.last_activity_at + (:gap * interval '1 minute')) - s.started_at)
                )::INT
            FROM to_close AS c
            WHERE s.id = c.id
            RETURNING s.id
        """)
    db.execute(q, {"gap": SESSION_TIMEOUT_MIN})
    db.commit()


def get_or_create_session(db, external_session_id: str | None):
    """ 
        ถ้าเจอแถว open → reuse 
        ถ้าเจอแถว closed → re-open (รีเซ็ตเวลา/ตัวนับ) เพื่อคง uuid เดิม
        ถ้าไม่เจอเลย → insert ใหม่ด้วย id=esid และ external_session_id=esid
        ถ้าไม่มี esid → insert ใหม่ด้วย id สุ่มของ DB แล้ว external_session_id = id::text
    """
    esid = (external_session_id or "").strip() or None

    if esid:
        # 1) ลองหาโดย ID (open)
        row = db.execute(text("""
            SELECT id FROM chat_sessions
            WHERE id = CAST(:esid AS uuid) AND status = 'open'
            ORDER BY started_at DESC LIMIT 1
        """), {"esid": esid}).mappings().first()
        if row:
            # ให้ external_session_id ตรงกับ id เสมอ
            db.execute(text("""
                UPDATE chat_sessions
                SET external_session_id = id::text
                WHERE id = :sid AND external_session_id IS DISTINCT FROM id::text
            """), {"sid": row["id"]})
            db.commit()
            return row["id"]

        # 2) ลองหาโดย ID (closed) → re-open เพื่อคง uuid เดิม
        row = db.execute(text("""
            SELECT id FROM chat_sessions
            WHERE id = CAST(:esid AS uuid) AND status = 'closed'
            ORDER BY started_at DESC LIMIT 1
        """), {"esid": esid}).mappings().first()
        if row:
            db.execute(text("""
                UPDATE chat_sessions
                SET status='open',
                    started_at = now(),
                    last_activity_at = now(),
                    closed_at = NULL,
                    message_count = 0,
                    total_duration_sec = 0,
                    external_session_id = id::text
                WHERE id = :sid
            """), {"sid": row["id"]})
            db.commit()
            return row["id"]

        # 3) (กันเคสเก่า) หาโดย external_session_id เดิมที่ open
        row = db.execute(text("""
            SELECT id FROM chat_sessions
            WHERE external_session_id = :esid AND status = 'open'
            ORDER BY started_at DESC LIMIT 1
        """), {"esid": esid}).mappings().first()
        if row:
            # บังคับให้ external ตรง id
            db.execute(text("""
                UPDATE chat_sessions
                SET external_session_id = id::text
                WHERE id = :sid AND external_session_id IS DISTINCT FROM id::text
            """), {"sid": row["id"]})
            db.commit()
            return row["id"]

        # 4) ไม่เจอเลย → สร้างใหม่ โดยใช้ esid เป็น id
        created = db.execute(text("""
            INSERT INTO chat_sessions (id, external_session_id)
            VALUES (CAST(:esid AS uuid), :esid)
            RETURNING id
        """), {"esid": esid}).mappings().first()
        db.commit()
        return created["id"]

    # ไม่มี esid → ให้ DB สร้าง id เอง แล้วตั้ง external = id::text
    created = db.execute(text("""
        INSERT INTO chat_sessions (external_session_id)
        VALUES (gen_random_uuid()::text)   -- จะถูกแทนด้วยค่าจริงทีหลังทันที
        RETURNING id
    """)).mappings().first()

    db.execute(text("""
        UPDATE chat_sessions
        SET external_session_id = id::text
        WHERE id = :sid
    """), {"sid": created["id"]})
    db.commit()
    return created["id"]


def update_session_activity(db, session_id: str, add_msg_count: int = 1):
    db.execute(text("""
        UPDATE chat_sessions
        SET last_activity_at = now(),
            message_count = message_count + :n
        WHERE id = :sid AND status = 'open'
    """), {"sid": session_id, "n": add_msg_count})
    db.commit()


def close_session_now(db, session_id: str):
    db.execute(text("""
        UPDATE chat_sessions
        SET status = 'closed',
            closed_at = now(),
            total_duration_sec = EXTRACT(EPOCH FROM (now() - started_at))::INT
        WHERE id = :sid AND status = 'open'
    """), {"sid": session_id})
    db.commit()

def chat_message_log(
    db: Session,
    *,
    session_id: str,
    human_message: str | None,
    ai_message: str | None,
    sentiment: str | None,
    intent_name: str | None,
    intent_score: float | None,
    used_tools: list | None,
    ai_confident: float | None,
):
    db.execute(
        text("""
            INSERT INTO public.chat_messages
            (session_id, human_message, ai_message, sentiment,
            intent_name, intent_score, ai_confident, used_tools)
            VALUES
            (:session_id, :human_message, :ai_message, :sentiment,
            :intent_name, :intent_score, :ai_confident, CAST(:used_tools AS jsonb))
        """),
        {
            "session_id": session_id,
            "human_message": human_message,
            "ai_message": ai_message,
            "sentiment": sentiment,
            "intent_name": intent_name,
            "intent_score": intent_score,
            "ai_confident": ai_confident,
            "used_tools": json.dumps(used_tools or []),
        }
    )
    db.commit()
