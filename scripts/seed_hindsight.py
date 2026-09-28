import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from memory.hindsight_client import retain

with open("data/disruptions.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        text = (
            f"[{r['id']}] On {r['date']}, a {r['disruption_type'].replace('_', ' ')} "
            f"occurred in {r['location']} due to {r['cause']}. "
            f"Plant {r['plant']} was affected; material: {r['material']}; "
            f"supplier: {r['supplier']}. Alternate supplier {r['alternate_supplier']} "
            f"responded in {r['response_hours']} hours. Delay: {r['delay_days']} days, "
            f"cost: {r['financial_impact_inr_lakh']} lakh INR. "
            f"Mitigation: {r['mitigation']}. Outcome: {r['outcome']} "
            f"(success={r['success']}). Lesson: {r['lesson']}."
        )
        for attempt in range(5):
            try:
                retain(
                    text,
                    context=f"disruption incident: {r['disruption_type']}",
                    timestamp=f"{r['date']}T00:00:00Z",
                )
                print("retained", r["id"])
                break
            except Exception as e:
                print(f"  retry {r['id']} ({attempt+1}/5) after error: {e}")
                time.sleep(20)
        time.sleep(8)
