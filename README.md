# 📚 ExamMitra — AI-Powered Competitive Exam Notification Platform

> An intelligent platform that automatically fetches, tracks, and notifies Indian government job aspirants about upcoming competitive exams using AI and real-time news data.

---

## 🌟 Features

- 🤖 **AI-Powered Fetching** — Uses Groq LLM (Llama 3.3 70B) to automatically fetch and structure exam data
- 📰 **Real-Time News Integration** — NewsAPI integration to patch and update exam details from latest news
- 🔔 **Exam Notifications** — Tracks UPSC, SSC, IBPS, RRB, and state-level exams
- 📅 **Auto Scheduling** — APScheduler runs AI fetch every 24h, status updates every 6h, and cleanup every 24h
- 👤 **User Authentication** — Register, login, and manage user accounts
- 🛡️ **Admin Panel** — Full CRUD for exams, user management, block/unblock users
- 🔄 **Status Tracking** — Auto-updates exam status (Upcoming / Currently Active / Expired)
- 🗃️ **MongoDB Storage** — Two collections: users and exams

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| Database | MongoDB |
| AI Model | Groq LLM — Llama 3.3 70B |
| News API | NewsAPI |
| Scheduler | APScheduler |
| Frontend | Bootstrap 5, HTML, CSS, JavaScript |
| Environment | python-dotenv |

---

## 📁 Project Structure

```
ExamMitra/
├── exammitra_backend/
│   ├── Aifetcher.py         # AI fetching + News API integration
│   ├── main.py              # FastAPI app + 21 REST API endpoints
│   ├── database.py          # MongoDB connection
│   ├── model.py             # Pydantic models
│   ├── seed.py              # Database seeding script
│   ├── run_fix.py           # Utility script
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Environment variables template
│   └── Competitive_Employment_Exams_Dataset_2026_27.json
│
└── exammitra_frontend/
    └── (HTML, CSS, JS files)
```

---

## ⚙️ API Endpoints (21 Total)

### User
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Register new user |
| POST | `/login` | User login |
| GET | `/exams` | Get all exams |
| GET | `/exams/{exam_name}` | Get single exam |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/login` | Admin login |
| POST | `/admin/exams/add` | Add new exam |
| PUT | `/admin/exams/update/{name}` | Update exam |
| DELETE | `/admin/exams/delete/{name}` | Delete exam |
| GET | `/admin/users` | Get all users |
| DELETE | `/admin/users/delete/{email}` | Delete user |
| PUT | `/admin/users/block/{email}` | Block user |
| PUT | `/admin/users/unblock/{email}` | Unblock user |

### AI
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/admin/ai/fetch` | Trigger AI fetch manually |
| GET | `/admin/ai/status` | Get DB stats + scheduler info |
| GET | `/admin/ai/news-patch/{name}` | Preview news patch |
| PUT | `/admin/ai/news-patch/{name}` | Apply news patch |
| DELETE | `/admin/exams/cleanup` | Delete expired exams |
| PUT | `/admin/exams/update-status` | Update all statuses |

---

## 🚀 How to Run Locally

### 1. Clone the repository
```bash
git clone https://github.com/AdithyaKshatriya03/ExamMitra.git
cd ExamMitra/exammitra_backend
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up environment variables
```bash
cp .env.example .env
```
Edit `.env` and add your actual keys:
```
GROQ_API_KEY=your_groq_api_key
NEWS_API_KEY=your_newsapi_key
ADMIN_EMAIL=your_admin_email
ADMIN_PASSWORD=your_admin_password
```

### 5. Seed the database
```bash
python seed.py
```

### 6. Run the server
```bash
uvicorn main:app --reload
```

### 7. Open in browser
```
http://localhost:8000
```

---

## 🔑 Get API Keys

- **Groq API Key** — [console.groq.com](https://console.groq.com)
- **NewsAPI Key** — [newsapi.org](https://newsapi.org)
- **MongoDB** — Local: `mongodb://localhost:27017`

---

## 👥 Team

| Name | Role |
|------|------|
| Adithya Kshatriya | Backend, Frontend, AI Integration, Frontend, Testing, Database, Documentation |

---

## 📊 Project Stats

- 21 REST API Endpoints
- 2 MongoDB Collections
- 8 Modules
- 3 Scheduled Jobs
- Covers UPSC, SSC, IBPS, RRB, and State Exams

---

## 📄 License

This project is for educational purposes.
