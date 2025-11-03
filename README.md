# Riddler: A2A Compliant AI Agent for Telex

Riddler is an AI-powered riddle and brain-teaser companion built for Telex. It:
- generates clever riddles on demand
- remembers your session so you can ask for hints or answers
- gives fresh questions every time you talk to it

Powered by FastAPI + Gemini LLM models 
🧠 AI Model: `gemini-2.0-flash` (riddle generation)

---

## ✨ Features

| Feature | Description |
|--------|-----------|
📌 Track registration | Users select roles via `/register-track` modal  
🧠 AI summarization | Turns task announcements into readable breakdowns highlighting core deliverables
🔔 Smart notifications | Sends tasks only to relevant team members  
📎 Slack-native | Works fully inside Slack channels + DMs  
🧵 Thread-safe | Handles real Slack events + modals  
📦 DB storage | Saves user track preferences (SQLModel)

## ✨ Commands

| Command | Purpose |
|--------|-----------|
/a2a/riddler | Indicate the track(s) (Frontend, Backend, PM etc.) you want to be notified of
---

## 🏗️ Architecture

- **FastAPI backend**
- **Gemini**
- **Uvicorn server**

---

---
## Create a .env file
- Create a .env file in the project root:
```bash
cp .env.example .env

```
## ⚙️ Environment variables
- Then edit .env with your preferred database connection string.
```env
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-2.0-flash

#Telex
TELEX_BASE_URL=https://api.telex.im

# FastAPI
PORT=4001




```
## Cloning the repository
```bash
git clone https://github.com/danielzfega/riddler-a2a-agent
cd riddler-a2a-agent


```
## Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate     # On macOS/Linux
venv\Scripts\activate        # On Windows


```
## List of dependencies - Sample requirements.txt
```txt
fastapi
uvicorn[standard]
httpx
python-dotenv
pydantic
google-genai




```
## Install dependencies
```bash
pip install -r requirements.txt


```
## Start the development server
```bash
uvicorn main:app --reload --port 4001


```
## Live URL
```bash
https://riddler-a2a-agent.up.railway.app/
