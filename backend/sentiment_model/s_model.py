from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from pythainlp.tokenize import word_tokenize
from pathlib import Path

sentiment_model_path = Path(__file__).resolve().parent / "sen_model"
tokenizer_sent = AutoTokenizer.from_pretrained(sentiment_model_path)
model_sent = AutoModelForSequenceClassification.from_pretrained(sentiment_model_path)
# print("sentiment_model_path)

label_map = {0: "positive", 1: "neutral", 2: "negative"}

def detect_sentiment(text: str) -> str:
    if not text.strip():
        return "neutral"

    tokens = word_tokenize(text, engine="newmm")
    tokenized_text = " ".join(tokens)
    inputs = tokenizer_sent(tokenized_text, return_tensors="pt", truncation=True, padding=True, max_length=512)

    # print(">input to model:", tokenized_text)

    with torch.no_grad():
        outputs = model_sent(**inputs)

    pred = torch.argmax(outputs.logits, dim=1).item()
    sentiment = label_map[pred]

    # print("predict sentiment:", sentiment)
    return sentiment


# text = "ไม่พอใจบริการเลย พนักงานพูดจาไม่ดี"
# sentiment = detect_sentiment(text)
# print(f"Sentiment: {sentiment}")