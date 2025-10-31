import math

def cal_confidence(total_logprob: float) -> float:

    prob = math.exp(total_logprob)
    confidence = round(prob, 2)
    return confidence
