# Catwalk Live

**Catwalk Live** is an **MCP (Model Context Protocol) Remote Platform** designed to orchestrate and manage secure connections between LLMs and external tools/services.

## 🚀 Tech Stack

- **Frontend**: Next.js 15 (React 19), TailwindCSS
- **Backend**: FastAPI (Python 3.11)
- **Database**: SQLite (Local Dev) / PostgreSQL (Production)
- **Encryption**: Fernet (Symmetric Encryption for credentials)
- **Infrastructure**: Docker, Fly.io

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env file
cp ../.env.example .env  # Ensure you set ENCRYPTION_KEY

# Run Migrations
alembic upgrade head

# Start Server
uvicorn app.main:app --reload
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## 🔐 Credentials & Security
This project uses **Fernet** symmetric encryption to store sensitive API keys (e.g., OpenAI, GitHub) in the `credentials` database table. Keys are never logged in plain text.

## 📈 Project Status
See [context/PROJECT_STATUS.md](context/PROJECT_STATUS.md) for the detailed roadmap.
- **Phase 1**: Foundation (Done)
- **Phase 2**: Analysis Engine (Done)
- **Phase 3**: Credential Management (Done)
- **Phase 4**: Frontend UI (Next)
