import csv
import os
import re
from statistics import mean

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _load_date_to_id():
    mapping = {}
    with open(os.path.join(_ROOT, "data/disruptions.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            mapping[r["date"]] = r["id"]
    return mapping

def _load_suppliers():
    names = set()
    with open(os.path.join(_ROOT, "data/disruptions.csv"), newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            names.add(r["alternate_supplier"])
    return sorted(names, key=len, reverse=True)

DATE_TO_ID = _load_date_to_id()
SUPPLIERS = _load_suppliers()


def parse_evidence(memory_texts: list[str]) -> list[dict]:
    records = []
    for text in memory_texts:
        rec = {"raw": text}

        m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        rec["id"] = DATE_TO_ID.get(m.group(1)) if m else None

        rec["alternate_supplier"] = "Unknown"
        for name in SUPPLIERS:
            if name in text:
                rec["alternate_supplier"] = name
                break

        m = re.search(r"in\s+(\d+)\s+hours", text)
        rec["response_hours"] = int(m.group(1)) if m else 24

        m = re.search(r"(\d+)\D{0,3}day\s+delay", text)
        rec["delay_days"] = int(m.group(1)) if m else 10

        m = re.search(r"cost(?:\s+of)?\s+([\d.]+)\s*lakh", text, re.IGNORECASE)
        rec["cost_lakh"] = float(m.group(1)) if m else 10.0

        low = text.lower()
        if "failed" in low or "quality issue" in low or "rejected" in low:
            rec["success"] = 0.0
            rec["quality_incident"] = 1
        elif "partially successful" in low or "partial" in low:
            rec["success"] = 0.5
            rec["quality_incident"] = 0
        elif "successful" in low or "delivered" in low or "recovered" in low:
            rec["success"] = 1.0
            rec["quality_incident"] = 0
        else:
            rec["success"] = 0.5
            rec["quality_incident"] = 0

        records.append(rec)
    return records


def score_suppliers(records: list[dict]) -> list[dict]:
    records = [r for r in records if r["alternate_supplier"] != "Unknown"]

    groups: dict[str, list[dict]] = {}
    for r in records:
        groups.setdefault(r["alternate_supplier"], []).append(r)

    scored = []
    for supplier, evidence in groups.items():
        n = len(evidence)
        success = mean(e["success"] for e in evidence)
        speed = 1 - min(mean(e["response_hours"] for e in evidence), 48) / 48
        cost = 1 - min(mean(e["cost_lakh"] for e in evidence), 40) / 40
        quality_pen = 0.25 * sum(e["quality_incident"] for e in evidence)

        raw_score = 0.45 * success + 0.25 * speed + 0.20 * cost - quality_pen
        confidence = "High" if n >= 3 and success >= 0.75 else ("Medium" if n >= 2 else "Low")

        scored.append({
            "supplier": supplier,
            "score": round(raw_score, 3),
            "cases_used": n,
            "success_rate": round(success, 2),
            "avg_response_hours": round(mean(e["response_hours"] for e in evidence), 1),
            "avg_cost_lakh": round(mean(e["cost_lakh"] for e in evidence), 1),
            "confidence": confidence,
            "cited_ids": [e["id"] for e in evidence if e["id"]],
            "quality_incidents": sum(e["quality_incident"] for e in evidence),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored
