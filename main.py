from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import Response
from apscheduler.schedulers.background import BackgroundScheduler
from model import User, LoginUser
from database import users_collection, exams_collection
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


from contextlib import asynccontextmanager

# ─────────────────────────────
# SCHEDULER  — auto runs on startup
# ─────────────────────────────
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    from Aifetcher import delete_expired_exams, update_statuses, run_ai_fetch

    # Expire old notifications every 24 hours
    scheduler.add_job(delete_expired_exams, "interval", hours=24, id="auto_expire",
                      next_run_time=datetime.now())   # runs immediately on startup too

    # Refresh statuses every 6 hours
    scheduler.add_job(update_statuses, "interval", hours=6, id="auto_status")

    # AI full-fetch every 24 hours (offset 1h from expiry check)
    scheduler.add_job(run_ai_fetch, "interval", hours=24, id="auto_ai_fetch")

    scheduler.start()
    print("[SCHEDULER] Started -- auto-expire(24h) | auto-status(6h) | AI-fetch(24h)")
    
    yield
    
    scheduler.shutdown()
    print("[SCHEDULER] Stopped.")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────
# HOME
# ─────────────────────────────
@app.get("/")
def home():
    return {"message": "ExamMitra Backend is running successfully"}


# Suppress browser favicon 404 warning
@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)


# ─────────────────────────────
# REGISTER
# ─────────────────────────────
@app.post("/register")
def register_user(user: User):
    if user.password != user.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    existing_user = users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    new_user = {
        "name":     user.name,
        "email":    user.email,
        "phone":    user.phone,
        "password": user.password,
        "blocked":  False
    }
    users_collection.insert_one(new_user)
    return {"message": "User registered successfully"}


# ─────────────────────────────
# LOGIN
# ─────────────────────────────
@app.post("/login")
def login_user(user: LoginUser):
    existing_user = users_collection.find_one({"email": user.email})
    if not existing_user:
        raise HTTPException(status_code=400, detail="User not found")
    if existing_user["password"] != user.password:
        raise HTTPException(status_code=400, detail="Invalid password")
    if existing_user.get("blocked") == True:
        raise HTTPException(
            status_code=403,
            detail="Your account has been blocked by admin. Contact: exammitra@gmail.com"
        )
    return {
        "message": "Login successful",
        "user": {
            "name":  existing_user.get("name",  ""),
            "email": existing_user.get("email", ""),
            "phone": existing_user.get("phone", "")
        }
    }


# ─────────────────────────────
# GET ALL EXAMS
# ─────────────────────────────
@app.get("/exams")
def get_exams():
    exams = list(exams_collection.find({}, {"_id": 0}))
    return {"exams": exams}


# ─────────────────────────────
# GET SINGLE EXAM (for JSON editing)
# ─────────────────────────────
@app.get("/exams/{exam_name}")
def get_exam(exam_name: str):
    exam = exams_collection.find_one({"Exam Name": exam_name}, {"_id": 0})
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")
    return {"exam": exam}


# ─────────────────────────────
# ADMIN LOGIN
# ─────────────────────────────
from dotenv import load_dotenv
import os

load_dotenv()

ADMIN_EMAIL    = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

@app.post("/admin/login")
def admin_login(user: LoginUser):
    if user.email != ADMIN_EMAIL or user.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    return {"message": "Admin login successful", "role": "admin"}


# ─────────────────────────────
# ADMIN — EXAM CRUD
# ─────────────────────────────
def sync_data():
    try:
        from Aifetcher import sync_to_json
        sync_to_json()
    except Exception as e:
        print(f"Sync error: {e}")

@app.post("/admin/exams/add")
def add_exam(exam: dict):
    existing = exams_collection.find_one({"Exam Name": exam.get("Exam Name")})
    if existing:
        raise HTTPException(status_code=400, detail="Exam already exists")
    exam["addedAt"] = datetime.now().isoformat()
    exams_collection.insert_one(exam)
    sync_data()
    return {"message": "Exam added successfully"}

@app.put("/admin/exams/update/{exam_name}")
def update_exam(exam_name: str, exam: dict):
    exam.pop("_id", None)
    exam["updatedAt"] = datetime.now().isoformat()
    result = exams_collection.update_one(
        {"Exam Name": exam_name},
        {"$set": exam}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Exam not found")
    sync_data()
    return {"message": "Exam updated successfully"}

@app.delete("/admin/exams/delete/{exam_name}")
def delete_exam(exam_name: str):
    result = exams_collection.delete_one({"Exam Name": exam_name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Exam not found")
    sync_data()
    return {"message": "Exam deleted successfully"}


# ─────────────────────────────
# ADMIN — JSON EDIT (full replace in JSON format)
# ─────────────────────────────
@app.put("/admin/exams/json-edit/{exam_name}")
def json_edit_exam(exam_name: str, patch: dict):
    """
    Edit any fields of an exam using raw JSON.
    Only provided fields are updated (partial patch).
    Example body: {"Status": "Upcoming", "Application / Last Date": "30 May 2026"}
    """
    patch.pop("_id", None)
    patch["updatedAt"] = datetime.now().isoformat()
    patch["source"]    = "Admin JSON Edit"
    result = exams_collection.update_one(
        {"Exam Name": exam_name},
        {"$set": patch}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Exam not found")
    updated_exam = exams_collection.find_one({"Exam Name": exam_name}, {"_id": 0})
    sync_data()
    return {"message": "Exam updated via JSON edit", "exam": updated_exam}


# ─────────────────────────────
# ADMIN — USER MANAGEMENT
# ─────────────────────────────
@app.get("/admin/users")
def get_all_users():
    users = list(users_collection.find({}, {"_id": 0, "password": 0}))
    return {"users": users}

@app.delete("/admin/users/delete/{email}")
def delete_user(email: str):
    result = users_collection.delete_one({"email": email})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


# ─────────────────────────────
# ADMIN — BLOCK / UNBLOCK USER
# ─────────────────────────────
@app.put("/admin/users/block/{email}")
def block_user(email: str):
    user = users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    users_collection.update_one(
        {"email": email},
        {"$set": {"blocked": True, "blockedAt": datetime.now().isoformat()}}
    )
    return {"message": f"User {email} blocked successfully"}

@app.put("/admin/users/unblock/{email}")
def unblock_user(email: str):
    user = users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    users_collection.update_one(
        {"email": email},
        {"$set": {"blocked": False, "unblockedAt": datetime.now().isoformat()}}
    )
    return {"message": f"User {email} unblocked successfully"}


# ─────────────────────────────
# ADMIN — AI ENDPOINTS
# ─────────────────────────────
@app.post("/admin/ai/fetch")
def ai_fetch(background_tasks: BackgroundTasks):
    """Manually trigger AI fetch in background (auto-runs every 24h via scheduler)"""
    def run():
        from Aifetcher import run_ai_fetch
        run_ai_fetch()
    background_tasks.add_task(run)
    return {"message": "AI Fetcher started in background!"}

@app.get("/admin/ai/status")
def ai_status():
    """Get current database stats + next scheduled job times"""
    jobs = {job.id: str(job.next_run_time) for job in scheduler.get_jobs()}
    return {
        "total_exams":    exams_collection.count_documents({}),
        "active_exams":   exams_collection.count_documents({"Status": "Currently Active"}),
        "upcoming_exams": exams_collection.count_documents({"Status": "Upcoming"}),
        "ai_added_exams": exams_collection.count_documents({"autoAdded": True}),
        "total_users":    users_collection.count_documents({}),
        "blocked_users":  users_collection.count_documents({"blocked": True}),
        "scheduler_jobs": jobs
    }

@app.delete("/admin/exams/cleanup")
def cleanup_expired():
    """Manually delete all expired exams (also runs automatically every 24h)"""
    from Aifetcher import delete_expired_exams
    deleted = delete_expired_exams()
    sync_data()
    return {"message": f"Deleted {len(deleted)} expired exams", "deleted": deleted}

@app.put("/admin/exams/update-status")
def update_all_statuses():
    """Manually update all exam statuses (also runs automatically every 6h)"""
    from Aifetcher import update_statuses
    updated = update_statuses()
    sync_data()
    return {"message": f"Updated {len(updated)} statuses", "updated": updated}

@app.get("/admin/exams/expired")
def get_expired_exams():
    """List all expired exams without deleting them"""
    from Aifetcher import parse_date
    today   = datetime.now()
    exams   = list(exams_collection.find({}, {"_id": 0}))
    expired = []
    for ex in exams:
        d = parse_date(ex.get("Application / Last Date", ""))
        if d and d < today:
            ex["expiredDays"] = (today - d).days
            expired.append(ex)
    return {"expired": expired, "count": len(expired)}


# ─────────────────────────────
# ADMIN — NEWS API PATCH
# ─────────────────────────────
@app.get("/admin/ai/news-patch/{exam_name}")
def preview_news_patch(exam_name: str):
    """
    Preview what News API + Gemini suggest as updates for an exam.
    Returns a JSON patch dict — does NOT apply changes yet.
    """
    from Aifetcher import fetch_and_patch_with_news
    result = fetch_and_patch_with_news(exam_name)
    return result

@app.put("/admin/ai/news-patch/{exam_name}")
def apply_news_patch(exam_name: str):
    """
    Fetch latest news for an exam, generate JSON patch via Gemini,
    and automatically apply it to the database.
    """
    from Aifetcher import fetch_and_patch_with_news
    result = fetch_and_patch_with_news(exam_name)
    patch  = result.get("patch", {})

    if not patch:
        return {"message": result.get("message", "No changes to apply"), "applied": False}

    patch.pop("_id", None)
    patch["updatedAt"] = datetime.now().isoformat()
    patch["source"]    = "AI News Patch"

    db_result = exams_collection.update_one(
        {"Exam Name": exam_name},
        {"$set": patch}
    )
    if db_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Exam not found in DB")

    updated_exam = exams_collection.find_one({"Exam Name": exam_name}, {"_id": 0})
    sync_data()
    return {
        "message": f"News patch applied — {len(patch)-2} field(s) updated",
        "applied": True,
        "fields_updated": [k for k in patch if k not in ("updatedAt","source")],
        "news_used": result.get("news_used", []),
        "exam": updated_exam
    }