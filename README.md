# Smart Job Application Tracker

Automates and organizes the job hunt with **AI-powered email parsing**, Gmail integration, and intelligent job tracking. Built with Python/FastAPI, React (Vite), PostgreSQL, and Google's Gemini AI.

## 🚀 New: Gemini AI Integration

**Intelligent Email Analysis**: The app now uses Google's Gemini AI to automatically parse job application emails with high accuracy.

### Key Features:
- **🤖 AI-Powered Parsing**: Automatically extracts company names, job titles, and application status
- **⏰ Time-Based Filtering**: Control token usage by only analyzing recent emails (1-30 days)
- **🔄 Smart Fallback**: Automatically falls back to regex parsing if AI is unavailable
- **💰 Free Tier**: Uses Gemini 1.5 Flash with generous free limits
- **🎯 Token Control**: Built-in limits prevent excessive API usage

### Quick Gemini Setup:
```bash
# Run the setup script
cd backend
python setup_gemini.py

# Or manually create .env file
echo "GEMINI_API_KEY=your_api_key_here" > backend/.env

# Restart backend
docker compose restart backend
```

**Get your free API key**: [Google AI Studio](https://makersuite.google.com/app/apikey)

## Stack
- **Backend**: FastAPI, Uvicorn, Pydantic Settings
- **Frontend**: React + TypeScript (Vite)
- **Database**: PostgreSQL with SQLAlchemy
- **AI**: Google Gemini API for intelligent email parsing
- **Integrations**: Gmail API, Google Calendar API (planned)

## Quickstart

### Docker (recommended for easy startup)

```bash
# Build images and start services
docker compose up --build

# Stop
docker compose down
```

- **API**: http://localhost:8000/health
- **Web**: http://localhost:5173
- **Postgres**: localhost:5432 (jobtracker/jobtracker)

### Prerequisites
- Python 3.10+
- Node 18+
- GitHub repo set up (already configured)

### Setup
```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend && npm install && cd ..
```

### Run the app
```bash
cd frontend
npm run dev
```
- **API**: http://localhost:8000/health
- **Web**: http://localhost:5173

## 🎯 Features

### Current
- ✅ **Job Application CRUD**: Create, read, update, delete job applications
- ✅ **Gmail Integration**: Parse job application emails automatically
- ✅ **Gemini AI Analysis**: Intelligent email parsing with AI
- ✅ **Time-Based Filtering**: Control which emails to analyze
- ✅ **Smart Fallback**: Regex parsing when AI unavailable
- ✅ **Modern UI**: Beautiful React interface with Gemini controls

### Planned
- 🔄 **Google Calendar Integration**: Create events/reminders for interviews/OAs
- 🔄 **Notion Sync**: Mirror applications to a Notion database
- 🔄 **Analytics Dashboard**: Response rate, company segments, timelines
- 🔄 **Auth & User Accounts**: Multi-user support

## 🧪 Testing Gemini AI

### Check Status
```bash
curl http://localhost:8000/gemini/status
```

### Test Analysis
```bash
curl -X POST "http://localhost:8000/gemini/test" \
  -d "subject=Thank you for applying to Google" \
  -d "body=We received your application for Software Engineer Intern..."
```

### Advanced Email Processing
```bash
# Process emails from last 3 days with AI
curl -X POST "http://localhost:8000/gmail/process-advanced?days_threshold=3&use_gemini=true&max_results=25"
```

## 📚 Documentation

- **Gemini Setup**: [backend/README_GEMINI_SETUP.md](backend/README_GEMINI_SETUP.md)
- **Gmail Setup**: [backend/README_GMAIL_SETUP.md](backend/README_GMAIL_SETUP.md)

## Development
- **Linting/formatting** (to add): Ruff/Black for Python, ESLint/Prettier for web
- **DB migrations** (to add): Alembic scripts
- **Env config**: use .env (examples to follow)

## Learning Goals
- Real-world API integrations (OAuth 2.0, AI APIs, webhooks/polling)
- Background jobs and rate limits
- Full-stack typing and validation
- CI/CD basics
- AI integration and prompt engineering
