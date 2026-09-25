def safe_answer(confidence):
    if confidence > 0.8:
        return "answer"
    if confidence > 0.5:
        return "I don't know — ask human"
    return "human review required"
