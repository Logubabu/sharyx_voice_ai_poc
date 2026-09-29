# Voice AI WebCall POC - Backend

Python backend powered by **Pipecat** real-time voice framework and FastAPI.

## Setup Instructions

### 1. Create Virtual Environment
```bash
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
```

### 4. Run Server
```bash
python -m app.main
```
The server will run at `http://localhost:8000`.
