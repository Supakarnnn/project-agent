from sqlalchemy import text

ORDER_COMPLETION_SQL = text("""
WITH intent_sessions AS (
  SELECT id AS session_id
  FROM chat_sessions
  WHERE active_intent = 'create_order'
),
ai_create_order AS (
  SELECT DISTINCT session_id
  FROM chat_messages
  WHERE used_tools @> '["create_order"]'::jsonb
)
SELECT
  COUNT(*) AS intent_sessions,
  (SELECT COUNT(*) FROM ai_create_order) AS ai_create_order,
  ROUND(
    (SELECT COUNT(*) FROM ai_create_order)::numeric
    / NULLIF(COUNT(*), 0) * 100
  , 2) AS complete_rate
FROM intent_sessions;
""")

TICKET_CREATE_SQL = text("""
WITH all_sessions AS (
  SELECT id AS session_id
  FROM chat_sessions
),
handoff_sessions AS (
  SELECT DISTINCT session_id
  FROM chat_messages
  WHERE used_tools @> '["create_ticket"]'::jsonb
)
SELECT
  (SELECT COUNT(*) FROM all_sessions) AS total_sessions,
  (SELECT COUNT(*) FROM handoff_sessions) AS handoff_sessions,
  ROUND(
    (SELECT COUNT(*) FROM handoff_sessions)::numeric
    / NULLIF((SELECT COUNT(*) FROM all_sessions), 0)
    * 100
  , 2) AS handoff_rate
;

""")

AVG_AI_CON_SQL = text("""
SELECT
  COUNT(*) AS ai_message_count,
  ROUND(AVG(ai_confident)::numeric, 4) AS avg_ai_confident
FROM chat_messages
WHERE ai_message IS NOT NULL
  AND ai_message <> ''
  AND ai_confident IS NOT NULL;
                      
""")

#============Keyword & Topic Frequency func============#
UNPROCESSED_MESSAGES = text("""
SELECT m.human_message
FROM chat_messages as m
LIMIT :limit;
""")

INSERT_MESSAGE_INSIGHT = text("""
INSERT INTO message_insights (topic, keywords, model_name)
VALUES (CAST(:topic AS jsonb), CAST(:keywords AS jsonb), :model_name)
""")

SYS_PROMPT = """
You are a customer message summarization system for creating dashboards.
Respond only in JSON format. No other text is allowed.
Topic should be an array of 3-8 words/phrases (Thai acceptable), focusing on customer Topic.
Keywords should be an array of 3-8 words/phrases (Thai acceptable), focusing on customer Keywords.
Do not use filler words such as ค่ะ ครับ คับ คะ นะ หน่อย ขอบคุณ ได้ไหม.
If the message is unclear, set the topic to "อื่นๆ".
"""

KEYWORD_TOPIC = text("""
SELECT topic, keywords
FROM message_insights
ORDER BY created_at DESC
LIMIT 1
""")
#=======================================================#

AVG_SESSION_TIME = text("""
SELECT
  COUNT(*) AS session_used,
  ROUND(AVG(message_count)::numeric, 2) AS avg_message_count,
  ROUND(AVG(total_duration_sec)::numeric, 2) AS avg_session_duration_sec,
  ROUND(AVG(total_duration_sec) / 60.0, 2) AS avg_session_duration_min
FROM chat_sessions
WHERE message_count > 0
  AND total_duration_sec IS NOT NULL;
""")