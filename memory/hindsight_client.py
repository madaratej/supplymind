import os
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

BANK = os.getenv("HINDSIGHT_BANK_ID", "supplymind-demo-hyd")
client = Hindsight(base_url=os.getenv("HINDSIGHT_URL", "http://localhost:8888"))


def retain(text, context="", timestamp=None):
    kwargs = {"bank_id": BANK, "content": text}
    if context:
        kwargs["context"] = context
    if timestamp:
        kwargs["timestamp"] = timestamp
    return client.retain(**kwargs)


def recall(query):
    res = client.recall(bank_id=BANK, query=query)
    return [r.text for r in res.results]
