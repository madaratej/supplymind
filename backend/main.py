import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.normalize import normalize_signal
from memory.hindsight_client import recall, retain
from agent.scorer import parse_evidence, score_suppliers

app = FastAPI(title="SupplyMind")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

SIGNALS = {}

class SignalIn(BaseModel):
    text: str

class DecisionIn(BaseModel):
    decision: str
    reason: str = ""

class OutcomeIn(BaseModel):
    actual_delay_days: int
    actual_cost_lakh: float
    supplier_rating: int
    quality_pass: bool
    notes: str = ""

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/signals")
def create_signal(s: SignalIn):
    sid = str(uuid.uuid4())[:8]
    SIGNALS[sid] = {"id": sid, "text": s.text, "status": "new"}
    return SIGNALS[sid]

@app.post("/signals/{sid}/analyze")
def analyze_signal(sid: str):
    if sid not in SIGNALS:
        raise HTTPException(404, "signal not found")
    sig = SIGNALS[sid]
    normalized = normalize_signal(sig["text"])
    sig["normalized"] = normalized

    query = f"{normalized.get('cause','')} {normalized.get('disruption_type','')} {normalized.get('location','')} {' '.join(normalized.get('materials',[]))}"
    memories = recall(query)
    sig["memories"] = memories
    sig["status"] = "analyzed"
    return {"normalized": normalized, "memory_count": len(memories), "memories": memories}

@app.post("/signals/{sid}/recommend")
def recommend(sid: str):
    if sid not in SIGNALS:
        raise HTTPException(404, "signal not found")
    sig = SIGNALS[sid]
    if "memories" not in sig:
        raise HTTPException(400, "run /analyze first")

    evidence = parse_evidence(sig["memories"])
    ranked = score_suppliers(evidence)

    if not ranked:
        sig["recommendation"] = {"text": "No comparable history in memory. Generic guidance: monitor and activate nearest qualified alternate.", "confidence": "None", "cited_ids": []}
        return sig["recommendation"]

    top = ranked[0]
    text = (
        f"Activate {top['supplier']}. Expected delay ~{top['avg_response_hours']}h response, "
        f"~{top['avg_cost_lakh']} lakh INR cost. Confidence: {top['confidence']} "
        f"(based on {top['cases_used']} case(s))."
    )
    avoid = [s for s in ranked if s["quality_incidents"] > 0]
    if avoid:
        text += " Avoid: " + ", ".join(a["supplier"] for a in avoid) + " (quality issues in history)."

    rec = {"text": text, "ranked_suppliers": ranked, "cited_ids": top["cited_ids"], "confidence": top["confidence"]}
    sig["recommendation"] = rec
    sig["status"] = "recommended"
    return rec

@app.post("/signals/{sid}/decision")
def decide(sid: str, d: DecisionIn):
    if sid not in SIGNALS:
        raise HTTPException(404, "signal not found")
    sig = SIGNALS[sid]
    sig["decision"] = d.dict()
    sig["status"] = "decided"

    rec = sig.get("recommendation", {})
    text = (
        f"[DECISION for {sid}] Manager {d.decision} the recommendation "
        f"'{rec.get('text','')}'. Reason: {d.reason}"
    )
    retain(text, context="manager decision")
    return {"retained": True}

@app.post("/signals/{sid}/outcome")
def outcome(sid: str, o: OutcomeIn):
    if sid not in SIGNALS:
        raise HTTPException(404, "signal not found")
    sig = SIGNALS[sid]
    sig["outcome"] = o.dict()
    sig["status"] = "closed"

    text = (
        f"[OUTCOME for {sid}] Actual delay {o.actual_delay_days} days, cost {o.actual_cost_lakh} lakh INR, "
        f"supplier rating {o.supplier_rating}/5, quality_pass={o.quality_pass}. Notes: {o.notes}"
    )
    retain(text, context="disruption outcome")
    return {"retained": True}

@app.get("/signals")
def list_signals():
    return list(SIGNALS.values())

@app.get("/signals/{sid}")
def get_signal(sid: str):
    if sid not in SIGNALS:
        raise HTTPException(404, "signal not found")
    return SIGNALS[sid]
