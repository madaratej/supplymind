import re
from statistics import mean

def parse_evidence(memory_texts: list[str]) -> list[dict]:
    """Turn raw Hindsight memory text into structured evidence records."""
    records = []
    for text in memory_texts:
        rec = {"raw": text}
        m = re.search(r"\[(D\d+)\]", text)
        rec["id"] = m.group(1) if m else None

        m = re.search(r"[Aa]lternate supplier ([A-Za-z .]+?) (?:responded|\()", text)
        rec["alternate_supplier"] = m.group(1).strip() if m else "Unknown"

        m = re.search(r"responded in (\d+) hours", text)
        rec["response_hours"] = int(m.group(1)) if m else 24

        m = re.search(r"Delay: (\d+) days", text)
        rec["delay_days"] = int(m.group(1)) if m else 10

        m = re.search(r"cost: ([\d.]+) lakh", text)
        rec["cost_lakh"] = float(m.group(1)) if m else 10.0

        m = re.search(r"success=([YNP])", text)
        flag = m.group(1) if m else "P"
        rec["success"] = 1.0 if flag == "Y" else (0.5 if flag == "P" else 0.0)
        rec["quality_incident"] = 1 if "Failed quality" in text or "failed inspection" in text else 0

        records.append(rec)
    return records


def score_suppliers(records: list[dict]) -> list[dict]:
    """Group evidence by supplier, score each, return ranked list."""
    groups: dict[str, list[dict]] = {}
    for r in records:
        key = r["alternate_supplier"]
        groups.setdefault(key, []).append(r)

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
