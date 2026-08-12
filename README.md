# Public Pulse

Public Pulse is an AI-powered civic complaint platform that helps citizens turn an informal description of a public issue into a structured, reviewable complaint and send it to the relevant authority through their own Gmail account.

The project combines a **FastAPI backend**, **PostgreSQL**, a **LangGraph complaint workflow**, **Groq-hosted LLM inference**, **Google OAuth 2.0 / Gmail API**, and a **Streamlit frontend**. It also includes a public civic dashboard for exploring complaint trends by status, category, pincode, and time period.

> **Current status:** the complaint workflow, Gmail integration, complaint history, and dashboard are implemented. The `app/rag/` and `app/agents/` directories currently contain placeholders for future work; the Rights RAG knowledge layer is planned but not yet implemented.

---

## What Public Pulse Does

A user can:

1. Register and log in.
2. Describe a civic problem in natural language.
3. Continue a conversation while the AI asks for missing details.
4. Have the complaint converted into structured fields.
5. Resolve the city and match the complaint to an authority.
6. Generate a formal complaint email.
7. Review and edit the email.
8. Explicitly approve it.
9. Connect Gmail using OAuth 2.0.
10. Send the approved complaint through the user's own Gmail account.
11. Reopen previous complaints and view their conversation history.
12. Explore aggregate complaint data in the civic dashboard.

The supported complaint categories are:

- Road
- Water
- Electricity
- Sanitation
- Police
- Government school
- Women safety
- Child labour
- Overpricing
- Other

---

## High-Level Architecture

```text
┌──────────────────────┐
│       Browser        │
└──────────┬───────────┘
           │ HTTP
           ▼
┌──────────────────────┐
│  Streamlit Frontend  │
│      Port 8501       │
└──────────┬───────────┘
           │ HTTP / JWT
           ▼
┌──────────────────────┐
│ Uvicorn + FastAPI    │
│      Port 8000       │
└──────────┬───────────┘
           │
     ┌─────┼───────────────────────────────┐
     │     │                               │
     ▼     ▼                               ▼
 PostgreSQL  LangGraph / Groq          Google OAuth
 Database     Complaint Workflow       + Gmail API
```

The Streamlit process serves the browser UI and acts as an HTTP client when calling the FastAPI API. Uvicorn hosts the FastAPI application as a separate process.

---

## Complaint AI Workflow

The complaint workflow is implemented in `app/graphs/`.

```text
START
  │
  ▼
load_conversation
  │
  ▼
analyze_complaint
  │
  ▼
resolve_city
  │
  ▼
find_authority
  │
  ▼
save_complaint
  │
  ├── complete ─────────────► END
  │
  └── incomplete
          │
          ▼
   ask_clarification
          │
          ▼
         END
```

`ComplaintGraphState` carries plain serializable state between nodes rather than SQLAlchemy sessions or ORM objects. This keeps the graph state suitable for future persistence/checkpointing.

The LLM analysis service uses the Groq SDK with structured JSON-schema output and Pydantic validation. The current model used in the complaint analysis code is:

```text
openai/gpt-oss-20b
```

The AI extracts:

- summary
- category
- city
- area
- pincode
- missing fields
- next clarification question
- completion state

The backend then resolves canonical location data and authority records rather than trusting the LLM to invent authority information.

---

## Complaint Lifecycle

```text
DRAFT
  │
  │ enough information collected
  ▼
AWAITING_APPROVAL
  │
  │ user approves email draft
  ▼
APPROVED
  │
  │ Gmail send succeeds
  ▼
SENT
```

The backend also supports:

- `UNRESOLVED`
- `PARTIALLY_RESOLVED`
- `RESOLVED`

Resolution analytics such as `resolved_at`, resolution time, and status history are planned for a later version.

---

## Human-in-the-Loop Email Flow

Public Pulse does **not** automatically send an AI-generated complaint.

```text
Structured complaint
        │
        ▼
AI email draft
        │
        ▼
User reviews subject/body
        │
        ├── edit
        │
        ▼
User explicitly approves
        │
        ▼
APPROVED
        │
        ▼
Send through connected Gmail
        │
        ▼
SENT
```

This preserves user control before an external action is taken.

---

## Gmail OAuth 2.0 Flow

Public Pulse lets users send complaints through their own Gmail account.

Implemented Gmail features include:

- Google OAuth 2.0 authorization
- OAuth state validation
- PKCE
- Google identity verification
- encrypted refresh-token storage
- automatic access-token refresh
- Gmail API sending
- Gmail connection status
- disconnect
- Google token revocation
- redirect back to Streamlit after a successful OAuth callback

```text
Authenticated Public Pulse user
        │
        ▼
GET /gmail/connect
        │
        ├── OAuth state
        └── PKCE code challenge
        │
        ▼
Google consent screen
        │
        ▼
GET /gmail/callback
        │
        ├── validate state
        ├── recover PKCE verifier
        ├── exchange authorization code
        ├── verify Google identity
        └── encrypt refresh token
        │
        ▼
PostgreSQL
```

When an approved complaint is sent:

```text
Encrypted refresh token
        │
        ▼
Decrypt token
        │
        ▼
Refresh Google access token
        │
        ▼
Gmail API
        │
        ▼
Send complaint email
```

---

## Civic Dashboard

The dashboard currently aggregates complaints by:

- total complaint count
- current status
- category
- pincode

Time filtering is based on `Complaint.created_at`.

Supported UI options include:

- All time
- Last 7 days
- Last 30 days
- Last 90 days
- Custom number of days from 1 to 365

Example:

```text
GET /dashboard/summary?days=30
```

means:

> include complaints created within the last 30 days.

A `resolved` count in that response means complaints **created during that period whose current status is resolved**. It does not mean complaints that became resolved during that period.

Planned v2 analytics include:

- `resolved_at`
- resolution rate
- average resolution time
- status history
- canonical area data
- population data
- per-capita area comparison

---

## Streamlit Frontend

The frontend uses sidebar navigation with separate views for:

- Complaint
- My Complaints
- Dashboard
- Gmail

The Streamlit layer is split into focused modules rather than one large file:

- `app.py` — entrypoint and navigation
- `auth.py` — login and registration UI
- `api_client.py` — HTTP communication with FastAPI
- `complaints.py` — complaint conversation UI
- `email_draft.py` — draft review/edit/approve/send flow
- `history.py` — complaint history and reopening
- `dashboard.py` — analytics UI
- `gmail.py` — Gmail connect/status/disconnect UI

JWT access tokens are kept in Streamlit session state and attached to protected FastAPI requests as Bearer tokens.

---

## Project Structure

```text
Public-Pulse/
│
├── app/
│   ├── agents/
│   │   └── .gitkeep
│   │
│   ├── constants/
│   │   └── complaint.py
│   │
│   ├── database/
│   │   ├── authority_crud.py
│   │   ├── base.py
│   │   ├── complaint_crud.py
│   │   ├── crud.py
│   │   ├── db.py
│   │   ├── dependencies.py
│   │   ├── gmail_credential_crud.py
│   │   ├── location_crud.py
│   │   ├── models.py
│   │   └── session.py
│   │
│   ├── graphs/
│   │   ├── complaint_graph.py
│   │   └── complaint_state.py
│   │
│   ├── rag/
│   │   └── .gitkeep
│   │
│   ├── routers/
│   │   ├── auth.py
│   │   ├── complaints.py
│   │   ├── dashboard.py
│   │   ├── gmail.py
│   │   ├── knowledge.py
│   │   └── users.py
│   │
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── complaint.py
│   │   ├── dashboard.py
│   │   ├── gmail.py
│   │   ├── location.py
│   │   └── user.py
│   │
│   ├── scripts/
│   │   ├── backfill_complaint_city_ids.py
│   │   ├── seed_authorities.py
│   │   └── seed_locations.py
│   │
│   ├── services/
│   │   ├── complaint_ai.py
│   │   ├── complaint_approval_workflow.py
│   │   ├── complaint_email_ai.py
│   │   ├── complaint_email_workflow.py
│   │   ├── complaint_send_workflow.py
│   │   ├── complaint_workflow.py
│   │   ├── dashboard.py
│   │   ├── email_sender.py
│   │   ├── gmail_email_sender.py
│   │   ├── gmail_oauth.py
│   │   ├── gmail_oauth_state.py
│   │   ├── google_token_revocation.py
│   │   └── location_resolver.py
│   │
│   ├── utils/
│   │   ├── security.py
│   │   └── token_encryption.py
│   │
│   ├── config.py
│   └── main.py
│
├── frontend/
│   ├── __init__.py
│   ├── api_client.py
│   ├── app.py
│   ├── auth.py
│   ├── complaints.py
│   ├── dashboard.py
│   ├── email_draft.py
│   ├── gmail.py
│   └── history.py
│
├── alembic/
│   └── versions/
│
├── data/
│   └── .gitkeep
│
├── tests/
│   ├── test_auth.py
│   ├── test_authority_crud.py
│   ├── test_complaint_crud.py
│   ├── test_complaint_routes.py
│   ├── test_complaint_send_workflow.py
│   ├── test_config.py
│   ├── test_connection.py
│   ├── test_gmail_connection_routes.py
│   ├── test_gmail_credential_crud.py
│   ├── test_gmail_email_sender.py
│   ├── test_gmail_oauth.py
│   ├── test_gmail_oauth_callback.py
│   ├── test_gmail_oauth_state.py
│   ├── test_gmail_routes.py
│   ├── test_google_token_revocation.py
│   ├── test_location_resolver.py
│   ├── test_token_encryption.py
│   └── test_user_crud.py
│
├── .env.example
├── .gitignore
├── .python-version
├── alembic.ini
├── pyproject.toml
├── uv.lock
└── README.md
```

`app/agents/` and `app/rag/` are currently placeholders. `app/routers/knowledge.py` is also currently empty and is reserved for future knowledge/RAG functionality.

---

## Tech Stack

### Backend

- Python 3.14+
- FastAPI
- Uvicorn
- SQLAlchemy 2.x
- PostgreSQL
- Alembic
- Pydantic v2

### AI

- LangGraph
- Groq Python SDK
- structured JSON-schema LLM outputs
- Pydantic validation

### Authentication & Security

- JWT (`python-jose`)
- `pwdlib` password hashing
- Google OAuth 2.0
- PKCE
- Fernet encryption for stored Google refresh tokens

### Google Integration

- `google-api-python-client`
- `google-auth`
- `google-auth-oauthlib`
- Gmail API

### Frontend

- Streamlit
- Requests
- Pandas

### Testing & Tooling

- pytest
- FastAPI TestClient / HTTPX
- mocks and monkeypatching
- uv
- Ruff
- Git / GitHub

---

## API Overview

### Health

```text
GET /health
```

### Authentication

```text
POST /auth/register
POST /auth/login
POST /auth/token
```

`/auth/login` accepts the application's JSON login schema.

`/auth/token` uses the OAuth2 password form format and supports the OAuth2/Swagger authentication flow.

### Users

```text
GET /users/me
```

### Complaints

```text
POST  /complaints
GET   /complaints
GET   /complaints/{complaint_id}
POST  /complaints/{complaint_id}/messages
POST  /complaints/{complaint_id}/email-draft
PATCH /complaints/{complaint_id}/email-draft
POST  /complaints/{complaint_id}/approve
POST  /complaints/{complaint_id}/send
```

### Gmail

```text
GET    /gmail/connect
GET    /gmail/callback
GET    /gmail/status
DELETE /gmail/disconnect
```

### Dashboard

```text
GET /dashboard/summary
GET /dashboard/summary?days=30
```

---

## Database

The backend uses PostgreSQL through SQLAlchemy.

Important persisted entities include:

- users
- complaints
- complaint messages
- cities
- city aliases
- authorities
- Gmail credentials
- Gmail OAuth transaction state

Alembic is used for database migrations.

---

## Authentication

Users authenticate with email and password.

Passwords are hashed using `pwdlib`'s recommended password hasher and never stored in plaintext.

After login, Public Pulse creates a signed JWT containing the user ID in the `sub` claim.

Protected requests use:

```text
Authorization: Bearer <JWT>
```

The backend derives the current user from the validated token rather than accepting a user ID from the client.

---

## Local Setup

### 1. Clone

```bash
git clone https://github.com/iamprakhar10/Public-Pulse.git
cd Public-Pulse
```

### 2. Install dependencies

The project uses `uv`.

```bash
uv sync
```

The project currently requires Python 3.14 or newer according to `pyproject.toml`.

### 3. Create PostgreSQL databases

Development database:

```bash
createdb publicpulse
```

Separate test database:

```bash
createdb publicpulse_test
```

### 4. Configure environment variables

Copy the example:

```bash
cp .env.example .env
```

The current `.env.example` defines:

```env
# PostgreSQL
DATABASE_URL=
TEST_DATABASE_URL=postgresql://username@localhost/publicpulse_test

# Public Pulse authentication
SECRET_KEY=

# LLM provider
GROQ_API_KEY=

# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/gmail/callback

# Encryption for stored OAuth refresh tokens
TOKEN_ENCRYPTION_KEY=
```

Fill these with your own local values.

Never commit `.env`.

### 5. Apply migrations

```bash
uv run alembic upgrade head
```

### 6. Seed reference data

Seed locations first:

```bash
uv run python -m app.scripts.seed_locations
```

Then authorities:

```bash
uv run python -m app.scripts.seed_authorities
```

If existing complaints need canonical city IDs backfilled:

```bash
uv run python -m app.scripts.backfill_complaint_city_ids
```

---

## Running the Application

Run the backend and frontend in separate terminals from the repository root.

### Terminal 1 — FastAPI

```bash
uv run uvicorn app.main:app --reload
```

API:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### Terminal 2 — Streamlit

```bash
PYTHONPATH=. uv run streamlit run frontend/app.py
```

Frontend:

```text
http://localhost:8501
```

---

## Running Tests

The project uses a separate PostgreSQL test database to keep test cleanup isolated from development data.

Run the complete suite with:

```bash
uv run python -m pytest -v
```

The test suite currently covers areas including:

- authentication
- user CRUD
- complaint CRUD
- complaint routes
- complaint sending workflow
- authority lookup
- location resolution
- token encryption
- Gmail credential CRUD
- OAuth state / PKCE
- Gmail OAuth callback flow
- Gmail connection routes
- Gmail sender
- Google token revocation
- configuration
- database connectivity

There are also manual AI/graph test scripts for selected LLM-dependent workflows.

---

## Current Status

### Implemented

- [x] Registration and login
- [x] JWT authentication
- [x] Protected user and complaint endpoints
- [x] Complaint conversation persistence
- [x] Fixed complaint categories and lifecycle statuses
- [x] LangGraph complaint processing
- [x] Structured LLM extraction
- [x] Clarification-question loop
- [x] Canonical city resolution
- [x] Authority matching
- [x] AI-generated complaint email
- [x] Human review and editing
- [x] Explicit approval
- [x] Gmail OAuth 2.0
- [x] PKCE
- [x] Encrypted refresh-token storage
- [x] Gmail send
- [x] Gmail disconnect and token revocation
- [x] Complaint history and reopening
- [x] Streamlit frontend with sidebar navigation
- [x] Time-filtered civic dashboard
- [x] Separate test database
- [x] Automated backend tests

### Planned

- [ ] Rights RAG using official government/legal sources
- [ ] Populate `app/rag/` knowledge pipeline
- [ ] Knowledge API
- [ ] Resolution timestamps and richer lifecycle analytics
- [ ] Per-capita area comparison
- [ ] Canonical area/population dataset
- [ ] Broader authority/location coverage
- [ ] Production deployment
- [ ] CI/CD
- [ ] Logging and monitoring
- [ ] Additional frontend polish

---

## Planned Rights RAG

The repository already reserves:

```text
app/rag/
app/agents/
app/routers/knowledge.py
data/
```

for future knowledge functionality, but the RAG system is **not implemented yet**.

The intended direction is an official-source civic rights assistant using curated material from government and legal sources.

Example questions:

- Can a shop charge above MRP?
- What can I do if police refuse to record my complaint?
- Where can I report child labour?
- What grievance mechanism applies to an electricity problem?
- What official source explains my options?

The intended RAG flow is:

```text
Official documents
      │
      ▼
Chunking
      │
      ▼
Embeddings
      │
      ▼
Vector store
      │
      ▼
Relevant retrieved context
      │
      ▼
Grounded LLM answer + sources
```

The complaint agent and the future rights RAG solve different problems:

```text
Rights RAG
"What are my rights / options?"

Complaint workflow
"Help me structure and send the complaint."
```

---

## V2 Ideas

The following features are intentionally deferred rather than approximated with unreliable data:

### Resolution analytics

Add dedicated lifecycle timestamps such as:

```text
resolved_at
sent_at
```

or a status-history table to support accurate questions such as:

- resolved in the last 30 days
- average resolution time
- resolution rate

### Per-capita comparison

Raw complaint counts are not enough to compare areas fairly.

A future version can introduce canonical area/population records and calculate metrics such as:

```text
complaints per 1,000 residents
```

This requires trustworthy population data matched to the same geographic unit used for complaint aggregation.

---

## Repository

**GitHub:** https://github.com/iamprakhar10/Public-Pulse

---

## Disclaimer

Public Pulse is an independent portfolio/development project and is not affiliated with or endorsed by a government authority.

AI-generated complaint content should be reviewed by the user before sending. Future rights-information functionality should rely on curated official sources and should not be treated as a substitute for professional legal advice.
