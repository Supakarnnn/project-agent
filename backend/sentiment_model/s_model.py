from typing import List
from agent.model import sentiment_llm


async def detect_sentiment(messages: List[str]) -> str:
    if not messages:
        return "neutral"

    conversation = "\n".join(f"- {m}" for m in messages if m.strip())
    if not conversation:
        return "neutral"

    prompt = f"""You are a Thai Sentiment Analysis expert.
    Analyze the OVERALL sentiment of this customer's conversation and classify as: positive, negative, or neutral.

    Rules:
    - "positive" = clearly expresses happiness, satisfaction, praise, or excitement.
    - "negative" = clearly expresses anger, disappointment, complaint, or frustration.
    - "neutral" = everything else: questions, facts, news, ads, product info, general statements.
    Focus on the most recent messages but use earlier messages for context.
    Reply with EXACTLY one word only.

    Customer messages:
    {conversation}

    Sentiment:"""

    response = await sentiment_llm.ainvoke(prompt)
    result = response.content.strip().lower()

    if "positive" in result:
        return "positive"
    elif "negative" in result:
        return "negative"
    else:
        return "neutral"