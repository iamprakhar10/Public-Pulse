# Public Pulse

Public Pulse is an **AI-powered civic assistance platform** that helps citizens report public issues to the relevant authorities and helps surface structured, location-based civic data that can be useful for journalists and public-interest reporting.

The project combines **LLM workflows, FastAPI, PostgreSQL, LangGraph, authentication, Gmail OAuth, and analytics** to turn an unstructured complaint into a structured, reviewable, and actionable complaint workflow.

---

## Why Public Pulse?

Reporting a civic problem is often harder than it should be.

A citizen may know that a road is damaged, water supply is irregular, or a public service is failing, but may not know:

- what information is required,
- which authority is responsible,
- how to write a formal complaint,
- where to send it,
- or how similar complaints are distributed across an area.

Public Pulse is being built to reduce that friction.

The system guides the user through the complaint process, extracts structured information from natural-language conversation, prepares a complaint email, asks for human approval, and can send the approved complaint using the user's own Gmail account.

At the same time, complaint data can be aggregated into dashboards so recurring local problems can be explored by location, category, status, and time period.

---

## Core Features

### AI-guided complaint flow

Users can describe a civic issue in natural language.

The system can:

- ask for missing information,
- extract structured complaint details,
- identify location information,
- classify the issue,
- maintain complaint state,
- and prepare the complaint for the next step.

### LangGraph-based workflow

The complaint pipeline uses **LangGraph** to coordinate the multi-step AI workflow.

The graph is designed around stages such as:

1. collecting user information,
2. extracting complaint details,
3. matching structured location/authority data,
4. saving complaint state,
5. generating an email draft,
6. waiting for human approval.

### Human-in-the-loop email approval

AI-generated complaint emails are **not sent automatically**.

Before sending, the user can:

- review the subject,
- review the email body,
- edit the draft,
- and explicitly approve it.

### Gmail OAuth 2.0 integration

Public Pulse supports connecting a user's Google account through **OAuth 2.0**.

This allows approved complaint emails to be sent from the **user's own Gmail account**, rather than from a shared Public Pulse email address.

OAuth state validation is used as part of the authorization flow.

### Authentication

The backend includes:

- user registration,
- password hashing,
- login,
- JWT access tokens,
- protected endpoints,
- and current-user authorization checks.

### Complaint analytics dashboard

The dashboard backend can aggregate civic complaints using filters such as:

- time period,
- category,
- status,
- pincode,
- and location.

This is intended to make recurring civic problems easier to identify and eventually support data-backed local reporting.

---

## Tech Stack

### Backend

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic

### AI / LLM

- LangGraph
- LangChain
- LLM structured outputs

### Authentication & External APIs

- JWT
- OAuth 2.0
- Gmail API

### Frontend

- Streamlit

### Testing & Tooling

- Pytest
- Git / GitHub
- uv

---

## High-Level Architecture

```text
                         ┌──────────────────┐
                         │      User        │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   Streamlit UI   │
                         └────────┬─────────┘
                                  │ HTTP
                                  ▼
                     ┌────────────────────────┐
                     │      FastAPI API       │
                     └───────────┬────────────┘
                                 │
             ┌───────────────────┼───────────────────┐
             │                   │                   │
             ▼                   ▼                   ▼
    ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
    │ Authentication │  │ Complaint      │  │ Dashboard      │
    │ JWT / OAuth    │  │ Services       │  │ Analytics      │
    └────────────────┘  └───────┬────────┘  └────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ LangGraph / LLM  │
                       │ Workflow         │
                       └────────┬─────────┘
                                │
              ┌─────────────────┼──────────────────┐
              │                 │                  │
              ▼                 ▼                  ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │ PostgreSQL   │  │ Authority /  │  │ Gmail API    │
      │ Database     │  │ Location Data│  │ Email Send   │
      └──────────────┘  └──────────────┘  └──────────────┘
```

---

## Complaint Workflow

```text
User reports issue
        ↓
Complaint created
        ↓
AI asks clarifying questions if needed
        ↓
Structured information extracted
        ↓
Location / authority information matched
        ↓
Complaint data saved
        ↓
Email draft generated
        ↓
AWAITING_APPROVAL
        ↓
User reviews / edits draft
        ↓
User approves
        ↓
Email sent through connected Gmail account
```

Complaint statuses used by the project include:

- `DRAFT`
- `AWAITING_APPROVAL`
- `SENT`
- `UNRESOLVED`
- `PARTIALLY_RESOLVED`
- `RESOLVED`

---

## Project Structure

```text
Public-Pulse/
│
├── app/
│   ├── database/
│   ├── routers/
│   ├── schemas/
│   ├── services/
│   ├── scripts/
│   ├── utils/
│   ├── config.py
│   └── main.py
│
├── alembic/
│   └── versions/
│
├── tests/
│
├── alembic.ini
├── pyproject.toml
├── uv.lock
└── README.md
```

---

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/iamprakhar10/Public-Pulse.git
cd Public-Pulse
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Create a PostgreSQL database

```bash
createdb publicpulse
```

### 4. Configure environment variables

Create a `.env` file in the project root.

Example structure:

```env
DATABASE_URL=postgresql://YOUR_USER:YOUR_PASSWORD@localhost:5432/publicpulse

SECRET_KEY=your-secret-key
ALGORITHM=HS256

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

Add any other environment variables required by `app/config.py`.

Do **not** commit real secrets or your `.env` file to GitHub.

### 5. Run database migrations

```bash
uv run alembic upgrade head
```

### 6. Seed local data

```bash
uv run python -m app.scripts.seed_authorities
uv run python -m app.scripts.seed_locations
```

### 7. Start the API

```bash
uv run uvicorn app.main:app --reload
```

---

## Running Tests

```bash
uv run python -m pytest -v
```

The test suite covers areas including:

- authentication,
- complaint CRUD,
- complaint routes,
- complaint workflows,
- email-draft flow,
- and OAuth state validation.

---

## Current Status

Implemented or substantially built:

- [x] User registration and login
- [x] JWT authentication
- [x] Complaint creation and conversation storage
- [x] Structured complaint analysis workflow
- [x] LangGraph complaint workflow
- [x] Complaint email generation
- [x] Human review and email editing
- [x] Complaint approval flow
- [x] Google OAuth / Gmail connection flow
- [x] Gmail-based complaint sending workflow
- [x] Authority and location data support
- [x] Dashboard analytics backend
- [x] Automated backend tests
- [x] Streamlit-based UI work

Still being developed / expanded:

- [ ] Retrieval-Augmented Generation (RAG) for civic rights and public-information knowledge
- [ ] Larger and more reliable civic knowledge base
- [ ] Broader authority coverage
- [ ] Production deployment
- [ ] More complete end-to-end UI polish
- [ ] Resolution tracking and richer public analytics

---

## Planned RAG Knowledge Layer

A planned part of Public Pulse is a **RAG-based civic knowledge system**.

The goal is to allow users to ask questions such as:

- What are my rights in this situation?
- Which authority is responsible?
- What rules apply to this civic service?
- Where can I escalate this complaint?
- What official source supports this information?

The RAG layer is intended to retrieve information from curated and trustworthy civic/government sources rather than rely only on the LLM's internal knowledge.

---

## Example Use Case

A user reports:

> The road near my house has been badly damaged for three months.

Public Pulse can ask for missing details such as city, area, pincode, and other relevant context.

After collecting enough information, the system can structure the complaint, determine the next workflow step, generate an email draft, and present it to the user for approval.

The complaint is only sent after explicit user confirmation.

---

## Roadmap

Future work includes:

- completing the RAG knowledge pipeline,
- collecting reliable government and civic documents,
- improving authority matching,
- expanding beyond the initial city dataset,
- improving dashboard visualizations,
- tracking complaint resolution,
- adding deployment infrastructure,
- and improving the production UI.

---

## Author

**Prakhar Singh**

GitHub: [iamprakhar10](https://github.com/iamprakhar10)

Project Repository: [Public Pulse](https://github.com/iamprakhar10/Public-Pulse)

---

## Disclaimer

Public Pulse is an independent project and is not affiliated with or endorsed by any government authority.

The platform is intended to assist users in organizing and communicating civic complaints. AI-generated content should be reviewed by the user before it is submitted or sent.
