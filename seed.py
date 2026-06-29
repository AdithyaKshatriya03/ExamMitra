import json
from database import exams_collection

with open("Competitive_Employment_Exams_Dataset_2026_27.json", "r", encoding="utf-8") as f:
    data = json.load(f)

exams = data["India"]

exams_collection.delete_many({})
exams_collection.insert_many(exams)

print(f"✅ Inserted {len(exams)} exams into MongoDB successfully!")