from sentence_transformers import SentenceTransformer
import numpy as np
from agent.model import Intent, TrainingPhrase
from typing import List

intent_model = SentenceTransformer("BAAI/bge-m3")

def load_intents(db):
    intent_data = []
    intents = db.query(Intent).all()
    for intent in intents:
        for phrase in intent.training_phrases:
            vector = intent_model.encode(phrase.phrase)
            intent_data.append({
                "intent": intent.name,
                "tool": intent.tool_name,
                "phrase": phrase.phrase,
                "embedding": vector
            })
    return intent_data

def match_intent(user_inputs: List[str], intent_data):
    combined_input = " ".join(user_inputs)
    user_vector = intent_model.encode(combined_input)
    
    best_score = -1
    matched = None

    for item in intent_data:
        sim = np.dot(user_vector, item["embedding"])
        if sim > best_score:
            best_score = sim
            matched = item

    if best_score >= 0.7:
        return matched["intent"], matched["tool"], float(best_score)
    return None, None, float(best_score)