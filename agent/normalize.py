import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("MODEL_NAME", "openai/gpt-oss-20b")

SYSTEM_PROMPT = """You are a supply chain signal parser. Given a short disruption
description, return ONLY a JSON object with these fields:
{
  "disruption_type": "port_closure|port_congestion|price_spike|quality_failure|road_disruption",
  "location": "city name",
  "port": "port name or null",
  "cause": "short cause phrase",
  "materials": ["material1"],
  "severity": "low|medium|high"
}
Return ONLY the JSON object, no other text, no markdown fences."""

def normalize_signal(text: str) -> dict:
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0,
    )
    raw = resp.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)
