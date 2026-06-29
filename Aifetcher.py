# ===================================================
# ExamMitra AI Fetcher -- Fully Automated Version
# Uses: requests only (NO google package needed)
# ===================================================

import requests
import json
import re
import time
import urllib.parse
from datetime import datetime
from database import exams_collection

# ----------------------------
# API KEYS
# ----------------------------
from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# ----------------------------
# GROQ URL -- Pure HTTP
# ----------------------------
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MONTHS = {
    "jan":1,"feb":2,"mar":3,"apr":4,"may":5,"jun":6,
    "jul":7,"aug":8,"sep":9,"oct":10,"nov":11,"dec":12
}

EXAM_FIELDS = [
    "Exam Name", "Full Form", "Conducting Body", "Category",
    "Posts / Services", "Eligibility", "Frequency", "Mode",
    "Stages", "Website (Display)", "Exam Date(s)",
    "Application / Last Date", "Result / Expiry Date",
    "Status", "Official URL"
]

EXAM_TOPICS = [
    "UPSC CSE CDS NDA CAPF ESE latest active and upcoming notifications",
    "SSC CGL CHSL MTS JE CPO GD Constable latest active and upcoming notifications",
    "IBPS PO Clerk SBI PO RBI Grade B latest active and upcoming banking notifications",
    "RRB NTPC Group D ALP JE latest active and upcoming railway notifications",
    "DRDO ISRO HAL BHEL PSU latest active and upcoming recruitment notifications",
    "KPSC Karnataka MPSC Maharashtra TNPSC Tamil Nadu latest active and upcoming exams",
    "NDA CDS AFCAT Coast Guard defence latest active and upcoming notifications",
    "BPSC Bihar UPPSC UP state exam latest active and upcoming notifications"
]


def parse_date(date_str):
    if not date_str or str(date_str).strip() in ["TBD","Rolling","--",""]:
        return None
    try:
        s = str(date_str).lower().strip()
        s = s.split(";")[0].split(",")[0].strip()
        m = re.search(r'(\d{1,2})\s+([a-z]{3})\s+(\d{4})', s)
        if m:
            return datetime(int(m.group(3)), MONTHS.get(m.group(2)[:3],1), int(m.group(1)))
        m2 = re.search(r'([a-z]{3})\s+(\d{4})', s)
        if m2:
            return datetime(int(m2.group(2)), MONTHS.get(m2.group(1)[:3],1), 28)
    except:
        return None
    return None


def is_expired(exam):
    app_date = parse_date(exam.get("Application / Last Date",""))
    return app_date and app_date < datetime.now()


def fetch_news(query):
    try:
        safe_q = urllib.parse.quote(query)
        url = (
            "https://newsapi.org/v2/everything"
            f"?q={safe_q}&language=en&sortBy=publishedAt&pageSize=3"
            f"&apiKey={NEWS_API_KEY}"
        )
        res  = requests.get(url, timeout=10)
        data = res.json()
        if data.get("status") == "ok":
            articles = data.get("articles", [])
            print(f"  [NEWS] {len(articles)} articles found")
            return articles
        else:
            print(f"  [NEWS] {data.get('message','limit reached')} -- Gemini only")
            return []
    except Exception as e:
        print(f"  [NEWS] Skipped: {e}")
        return []


def fetch_and_patch_with_news(exam_name: str) -> dict:
    articles = fetch_news(exam_name)
    if not articles:
        return {"message": "No news articles found", "patch": {}}

    news_text = "\n".join([
        f"Title: {a.get('title','')}\nDesc: {a.get('description','')}\nURL: {a.get('url','')}"
        for a in articles[:5]
    ])

    prompt = f"""You are an expert on Indian govt competitive exams.
Based ONLY on the following news articles about "{exam_name}", identify any updated information.
Return ONLY a JSON object (not an array) with fields that have changed or need updating.
Only include fields you are confident about from the news. If nothing has changed, return {{}}.

Allowed field names:
"Exam Name", "Full Form", "Conducting Body", "Category", "Posts / Services",
"Eligibility", "Frequency", "Mode", "Stages", "Website (Display)", "Exam Date(s)",
"Application / Last Date", "Result / Expiry Date", "Status", "Official URL"

Status must be: "Currently Active" OR "Upcoming" only.
Dates format: DD Mon YYYY like 18 Feb 2026.

News articles:
{news_text}

Return ONLY a valid JSON object. No markdown. No extra text."""

    try:
        payload = {
            "model": "llama3-70b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        res  = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        data = res.json()
        if res.status_code != 200:
            err = data.get("error", {}).get("message", "unknown")[:80]
            return {"message": f"Groq error: {err}", "patch": {}}

        text  = data["choices"][0]["message"]["content"].strip()
        
        # In rare cases Llama outputs code blocks even in json mode
        text  = re.sub(r"```json|```", "", text).strip()
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if not match:
            return {"message": "No patch data returned", "patch": {}}

        patch = json.loads(match.group())
        return {
            "message": f"News patch generated from {len(articles)} articles",
            "patch": patch,
            "news_used": [a.get("title","") for a in articles[:5]]
        }
    except Exception as e:
        return {"message": f"Error: {e}", "patch": {}}


def call_groq(topic, news_context=""):
    for attempt in range(2):
        try:
            news_text = ""
            if news_context:
                news_text = f"\n\nLatest news:\n{news_context[:1500]}"

            prompt = f"""You are an expert on Indian government competitive exams.
Fetch both ACTIVE and UPCOMING exam notifications for the following topic.
For exams that are yet to be officially announced, set the Status strictly to "Upcoming" and put expected months or "TBD" for dates.
For exams where the official notification is out and applications are open, set the Status strictly to "Currently Active".
Do not include exams whose application deadlines have already passed in the past.
Topic: {topic}{news_text}

Return a JSON object containing a single key "exams" which is an array with EXACTLY these 15 fields per exam object:
{{
  "exams": [
    {{
      "Exam Name": "UPSC CSE",
      "Full Form": "Civil Services Examination",
      "Conducting Body": "UPSC",
      "Category": "Central Govt",
      "Posts / Services": "IAS, IPS, IFS, IRS & 24 other services",
      "Eligibility": "Graduate (any discipline), Age 21-32",
      "Frequency": "Annual",
      "Mode": "Offline",
      "Stages": "Prelims Mains Interview",
      "Website (Display)": "upsc.gov.in",
      "Exam Date(s)": "25 May 2026 (Prelims); Oct 2026 (Mains)",
      "Application / Last Date": "18 Feb 2026",
      "Result / Expiry Date": "Mains Result: Apr 2027; Final Result: Jun 2027",
      "Status": "Currently Active",
      "Official URL": "https://upsc.gov.in"
    }}
  ]
}}
RULES:
1. ALL 15 fields must be present
2. Status: Must be "Currently Active" OR "Upcoming" ONLY.
3. Mode: Online (CBT) OR Offline OR Online/Offline OR Online (GATE-based)
4. Dates: DD Mon YYYY or Expected Mon YYYY or TBD.
5. Eligibility must include age like Graduate Age 21-32
6. Website Display domain only like upsc.gov.in
7. Upcoming exams should have realistic expected dates, not highly speculative ones.
8. Return ONLY valid JSON object with the "exams" key. No extra markdown."""

            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "response_format": {"type": "json_object"}
            }

            res  = requests.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            data = res.json()

            if res.status_code == 429:
                err_msg = data.get("error", {}).get("message", "Unknown error")
                if attempt == 0:
                    print(f"  [GROQ] Rate limited: {err_msg}")
                    print(f"  [GROQ] Retrying in 10s...")
                    time.sleep(10)
                    continue
                else:
                    print(f"  [GROQ] Rate limit exceeded -- skipping topic")
                    return []

            if res.status_code != 200:
                err = data.get("error", {}).get("message", "unknown")[:80]
                print(f"  [GROQ] Error {res.status_code}: {err}")
                return []

            if "choices" not in data:
                print(f"  [GROQ] No response received")
                return []

            text  = data["choices"][0]["message"]["content"].strip()
            
            # Remove markdown formatting if Llama improperly includes it
            text  = re.sub(r"```json|```", "", text).strip()
            match = re.search(r'\{.*\}', text, re.DOTALL)

            if not match:
                print("  [GROQ] No JSON object found")
                return []

            result = json.loads(match.group())
            exams = result.get("exams", [])
            print(f"  [GROQ] {len(exams)} exams fetched OK")
            return exams

        except json.JSONDecodeError as e:
            print(f"  [ERROR] JSON parse error: {e}")
            return []
        except Exception as e:
            print(f"  [ERROR] {e}")
            return []
    return []


def validate_and_fix(exam):
    if not exam.get("Exam Name","").strip():
        return None
    if exam.get("Status") not in ["Currently Active","Upcoming"]:
        exam["Status"] = "Upcoming"
    valid_modes = ["Online (CBT)","Offline","Online/Offline","Online (GATE-based)","Merit-based / Online"]
    if exam.get("Mode") not in valid_modes:
        exam["Mode"] = "Online (CBT)"
    return {field: exam.get(field,"") for field in EXAM_FIELDS}


def save_exam(exam):
    try:
        exam = validate_and_fix(exam)
        if not exam:
            return None
        name = exam["Exam Name"].strip()
        if len(name) < 3:
            return None
        if is_expired(exam):
            print(f"  [>> SKIPPED] {name} (Deadline Expired)")
            return "skipped"
        existing = exams_collection.find_one({"Exam Name": name})
        if existing:
            exams_collection.update_one(
                {"Exam Name": name},
                {"$set": {**exam, "updatedAt": datetime.now().isoformat(), "source": "AI Auto-Updated"}}
            )
            print(f"  [-- UPDATED] {name}")
            return "updated"
        else:
            exam["addedAt"]   = datetime.now().isoformat()
            exam["source"]    = "AI Auto-Added"
            exam["autoAdded"] = True
            exams_collection.insert_one(exam)
            print(f"  [++ NEWLY ADDED] {name}")
            return "added"
    except Exception as e:
        print(f"  [ERROR] Save failed: {e}")
        return None


def delete_expired_exams():
    print("\n[CLEANUP] Checking expired exams...")
    all_exams = list(exams_collection.find({}, {"_id": 0}))
    deleted   = []
    today     = datetime.now()
    for exam in all_exams:
        app_date = parse_date(exam.get("Application / Last Date",""))
        if app_date and app_date < today:
            exams_collection.delete_one({"Exam Name": exam["Exam Name"]})
            deleted.append(exam["Exam Name"])
            print(f"  [xx DELETED] {exam['Exam Name']} -- deadline was: {exam.get('Application / Last Date','?')}")
    print(f"  [DONE] Deleted {len(deleted)} expired exam(s).")
    return deleted


def update_statuses():
    print("\n[STATUS] Updating exam statuses...")
    all_exams = list(exams_collection.find({}, {"_id": 0}))
    updated   = []
    today     = datetime.now()
    for exam in all_exams:
        app_date  = parse_date(exam.get("Application / Last Date",""))
        exam_date = parse_date(exam.get("Exam Date(s)",""))
        current   = exam.get("Status","")
        new_status = None
        if app_date and app_date >= today:
            new_status = "Currently Active"
        elif exam_date and exam_date >= today:
            new_status = "Upcoming"
        if new_status and new_status != current:
            exams_collection.update_one(
                {"Exam Name": exam["Exam Name"]},
                {"$set": {"Status": new_status, "updatedAt": today.isoformat()}}
            )
            updated.append(f"{exam['Exam Name']} -> {new_status}")
            print(f"  [** STATUS UPDATE] {exam['Exam Name']}: {current} -> {new_status}")
    print(f"  [DONE] Updated {len(updated)} status(es).")
    return updated


def sync_to_json():
    print("\n[SYNC] Updating JSON backup file...")
    try:
        all_exams = list(exams_collection.find({}, {"_id": 0}))
        with open("Competitive_Employment_Exams_Dataset_2026_27.json", "w", encoding="utf-8") as f:
            json.dump(all_exams, f, indent=4)
        print(f"  [DONE] Synced {len(all_exams)} exams to JSON file.")
    except Exception as e:
        print(f"  [ERROR] JSON sync failed: {e}")



def run_ai_fetch():
    print(f"\n{'='*60}")
    print("ExamMitra AI Fetcher -- Automated Run")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    deleted = delete_expired_exams()
    updated = update_statuses()

    total_added = total_updated = total_skipped = 0

    print(f"\n[AI] Processing {len(EXAM_TOPICS)} topics...\n")

    for i, topic in enumerate(EXAM_TOPICS):
        print(f"[{i+1}/{len(EXAM_TOPICS)}] {topic[:55]}...")
        # Add "application date" to force the News API to pull articles discussing the schedule calendar
        short_query  = " ".join(topic.split()[:2]) + " application date"
        articles     = fetch_news(short_query)
        news_context = "\n".join([
            f"Title: {a.get('title','')}\nDesc: {a.get('description','')}"
            for a in articles[:3]
        ])
        exams = call_groq(topic, news_context)
        for exam in exams:
            result = save_exam(exam)
            if result == "added":     total_added   += 1
            elif result == "updated": total_updated += 1
            elif result == "skipped": total_skipped += 1
        time.sleep(15)

    total_in_db = exams_collection.count_documents({})
    sync_to_json()

    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"Expired deleted    : {len(deleted)}")
    print(f"Statuses updated   : {len(updated)}")
    print(f"Brand New added    : {total_added}")
    print(f"Existing updated   : {total_updated}")
    print(f"Skipped (expired)  : {total_skipped}")
    print(f"Total in DB now    : {total_in_db}")
    print(f"{'='*60}\n")
    return {
        "deleted": len(deleted), "added": total_added,
        "updated": total_updated, "skipped": total_skipped,
        "total_in_db": total_in_db,
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    run_ai_fetch()