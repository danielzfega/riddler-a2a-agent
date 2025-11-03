# Iris — AI Task Tracking & Summary Bot for Slack

Iris is an intelligent Slack bot that:
- tracks project announcements 
- detects intern tracks (Frontend / Backend / PM / Design etc.), and automatically sends structured AI task summaries directly to users based on their said track(s).

Powered by FastAPI + Slack Bolt SDK + HuggingFace Transformers  
🧠 AI Model: `sshleifer/distilbart-cnn-12-6` (summarization)

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
/register-track | Indicate the track(s) (Frontend, Backend, PM etc.) you want to be notified of
---

## 🏗️ Architecture

- **FastAPI backend**
- **Slack Bolt SDK (async)**
- **HuggingFace Summarizer**
- **SQLModel + Postgres (or SQLite)**
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
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
HUGGINGFACE_MODEL=sshleifer/distilbart-cnn-12-6
DATABASE_URL=postgresql+psycopg://user:password@localhost/iris-slack-bot
HOST_URL=http://localhost:8000



```
## Cloning the repository
```bash
git clone https://github.com/danielzfega/iris-slack-bot
cd iris-slack-bot


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
uvicorn
slack-bolt
transformers
sqlmodel
psycopg2-binary     # if using Postgres
python-dotenv
requests



```
## Install dependencies
```bash
pip install -r requirements.txt


```
## Start the development server
```bash
uvicorn main:fastapi_app --reload


```
## Public URL Setup (Development)
Use ngrok to test Slack events:
```bash
ngrok http 8000

```
## Update Slack Event URL:
```bash
https://<ngrok-id>.ngrok.io/slack/events

```
## Sample Task Summary
Sample output given by bot

Frontend Task
 - Build the dashboard UI using React, Tailwind
 - Include login state & API calls
 - Deadline: Thur, Oct 30
 - API: GET /user/profile

---

## Bot outputs
- Summary
- Endpoints
- Deliverables
- Deadline
- Resource Link