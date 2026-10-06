# 🏫 School Operations Agent Platform

An AI-powered school management platform that combines a web application, Telegram bot, and LLM-based document parsing to manage classes, assignments, student progress, and parent communication.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                     │
│  Landing │ Register │ Login │ Role-based Dashboards      │
│  Admin │ Teacher │ Student │ Parent │ Document Review     │
└──────────────────┬──────────────────────────────────────┘
                   │ HTTP / WebSocket
┌──────────────────▼──────────────────────────────────────┐
│                  Backend (FastAPI)                        │
│                                                          │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ Auth    │  │ Services │  │ AI/LLM   │  │ Telegram │ │
│  │ JWT+    │  │ Business │  │ Document │  │ Bot      │ │
│  │ RBAC    │  │ Logic    │  │ Parser + │  │ Handlers │ │
│  └─────────┘  │ State    │  │ Intent   │  └──────────┘ │
│               │ Machines │  │ Engine   │                │
│  ┌─────────┐  └──────────┘  └──────────┘  ┌──────────┐ │
│  │ WebSocket│                              │ Scheduler│ │
│  │ Live    │                              │ Reminders│ │
│  │ Updates │                              │ APSched  │ │
│  └─────────┘                              └──────────┘ │
└──────────────────┬──────────────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│              PostgreSQL (port 5463)                       │
│  schools │ users │ grade_classes │ assignments            │
│  submissions │ documents │ feedback │ reminders           │
│  audit_events │ invite_tokens │ school_policies           │
└─────────────────────────────────────────────────────────┘
```


## Features & Recent Updates

- **Multimodal Assignment Submissions**: Students can submit photos and documents via Telegram. The AI automatically extracts text from images and updates the submission.
- **Individual Assignments**: Teachers can create assignments targeted at specific students (via Web Dashboard or Telegram).
- **Targeted Class Materials**: Teachers can upload class materials targeted to specific classes or students. Students receive immediate Telegram notifications.
- **Role-Based Document Filtering**: Students and guardians only see documents relevant to them.
- **Parent-Teacher Communication**: Parents can send messages to teachers via Telegram; messages are properly tagged and routed.

*(Note: Telegram voice/audio note parsing for commands is currently experimental and may not work properly. Text and photo submissions are fully supported).*

## Prerequisites

- **Python 3.12+**
- **Node.js 20+** & npm
- **PostgreSQL 15+** (running on port 5463 via Docker)
- **OpenAI API key** (for document parsing and intent detection)
- **Telegram Bot Token** (create via [@BotFather](https://t.me/BotFather))

## Quick Start

### 1. Database (PostgreSQL via Docker)

```bash
# Start PostgreSQL
docker-compose up -d

# Verify it's running
docker ps  # should show school-ops-db on port 5463
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings:
#   - JWT_SECRET_KEY (generate a random key)
#   - OPENAI_API_KEY (from OpenAI dashboard)
#   - TELEGRAM_BOT_TOKEN (from @BotFather)

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.local.example .env.local

# Start dev server
npm run dev
```

### 4. Access

- **Web App**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **Health Check**: http://localhost:8000/health

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JWT_SECRET_KEY` | ✅ | — | Secret key for JWT token signing |
| `DATABASE_URL` | ❌ | `postgresql+asyncpg://...@localhost:5463/school_ops` | Async database URL |
| `OPENAI_API_KEY` | ❌ | — | OpenAI API key for AI features |
| `TELEGRAM_BOT_TOKEN` | ❌ | — | Telegram bot token |
| `CORS_ORIGINS` | ❌ | `["http://localhost:3000"]` | Allowed CORS origins |
| `UPLOAD_DIR` | ❌ | `./uploads` | File upload directory |

## Domain Model

### Actors & Access Boundaries

| Actor | Can Do | Limited To |
|-------|--------|------------|
| **Admin** | Register school, manage classes, invite teachers, upload policies, view audit | Own school only |
| **Teacher** | Create assignments, review submissions, give feedback, upload documents | Assigned classes only |
| **Student** | View assignments, submit work, report progress/blocked | Own submissions only |
| **Guardian** | View child progress digest, opt in to notifications | Linked children only |
| **System/Agent** | Parse documents, classify intents, send reminders | Through explicit tools only |

### State Machines

**Assignment**: `DRAFT → PENDING_APPROVAL → ACTIVE → COMPLETED/CANCELLED`

**Submission**: `NOT_STARTED → IN_PROGRESS → BLOCKED/SUBMITTED → REVISION_REQUESTED → RESUBMITTED → COMPLETED`

## Demo Walkthrough

Follow this sequence to exercise the full system:

1. **Register** a school at http://localhost:3000/register
2. **Create 2 classes** in the admin dashboard
3. **Invite a teacher** → copy invite link → register via link
4. **Invite 2 students + 1 guardian** → register via invite links
5. **Upload a roster CSV** → review AI-parsed data → resolve duplicates
6. **Upload an assignment PDF** → AI parses it → review → approve
7. **Link Telegram** → students use `/link <code>` in the bot
8. **Student reports progress** via Telegram → teacher dashboard updates live
9. **Student says "I'm stuck"** → blocked alert on teacher dashboard
10. **Trigger reminders** → POST to `/api/reminders/trigger`
11. **Student submits work** via Telegram or web
12. **Teacher gives feedback** → request revision or approve
13. **Try wrong-context access** → verify 403 rejection
14. **Check audit timeline** → all events with correlation IDs

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/auth/register` | Public | Register school + admin |
| POST | `/api/auth/login` | Public | Login |
| GET | `/api/auth/me` | Bearer | Get current user |
| POST | `/api/classes` | Admin | Create class |
| GET | `/api/classes` | Auth | List classes |
| POST | `/api/invites` | Admin/Teacher | Create invite |
| POST | `/api/invites/{token}/accept` | Public | Accept invite |
| POST | `/api/assignments` | Teacher/Admin | Create assignment |
| GET | `/api/assignments` | Auth | List assignments |
| PUT | `/api/assignments/{id}/state` | Teacher/Admin | Update state |
| PUT | `/api/submissions/{id}` | Student | Update submission |
| POST | `/api/submissions/{id}/feedback` | Teacher | Give feedback |
| POST | `/api/documents/upload` | Auth | Upload document |
| POST | `/api/documents/{id}/parse` | Auth | Trigger AI parsing |
| POST | `/api/documents/{id}/approve` | Teacher/Admin | Approve parse |
| GET | `/api/audit` | Admin | Audit timeline |
| GET | `/api/dashboard` | Auth | Role-based dashboard |
| POST | `/api/reminders/trigger` | Admin/Teacher | Manual reminder trigger |

## Testing

```bash
cd backend

# Run all tests
python -m pytest tests/ -v

# Run specific suites
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_assignment_states.py -v
python -m pytest tests/test_submission_states.py -v
python -m pytest tests/test_safety.py -v
python -m pytest tests/test_intent_engine.py -v
```

## Architecture Decision Records

- [ADR-001: ORM and Auth Library Choices](docs/ADR-001-orm-and-auth-libraries.md) — Why SQLAlchemy + pwdlib + PyJWT
- [ADR-002: LLM as Proposed Action](docs/ADR-002-llm-as-proposed-action.md) — Why AI output requires human approval
- [ADR-003: State Machine Enforcement](docs/ADR-003-state-machine-enforcement.md) — Why state transitions are enforced in the service layer

## Known Limitations

1. **Single-process WebSocket**: The in-memory `ConnectionManager` works for single-worker Uvicorn. For multi-worker deployment, use Redis Pub/Sub.
2. **No file content storage for Telegram submissions**: Currently stores metadata only; file download from Telegram API not implemented.
3. **APScheduler single-worker**: Must run with `--workers 1` or in a dedicated process to avoid duplicate job execution.
4. **No email notifications**: Only Telegram and web dashboard notifications are implemented.
5. **SQLite for tests**: Tests use SQLite in-memory, which may miss PostgreSQL-specific issues.
6. **No refresh token rotation**: Refresh tokens are stateless; token blacklisting on logout is not implemented.

## Out of Scope

- Enterprise SSO / SAML / OAuth providers
- Full billing / subscription management
- Native mobile apps
- Complex LMS integrations (Canvas, Moodle)
- Multi-region deployment / geo-replication
- Polished visual design / design system
