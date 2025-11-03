# Riddler: A2A Compliant AI Agent for Telex

Riddler is an AI-powered riddle and brain-teaser companion built for Telex. It:
- generates clever riddles on demand
- remembers your session so you can ask for hints or answers
- gives fresh questions every time you talk to it

Powered by FastAPI + Gemini LLM models 
🧠 AI Model: `gemini-2.0-flash` (riddle generation)

---


## ✨ Commands

| Command | Purpose |
|--------|-----------|
/a2a/riddler | generates riddles, handles hints and answers
---

## 🏗️ Architecture

- **FastAPI backend**
- **Gemini**
- **Uvicorn server**

Riddler is powered by FastAPI and uses Google Gemini 2.0 Flash for language generation. Session memory is handled in-app using a task-bound store, ensuring each Telex task ID has its own riddle state.

The core flow is simple:
• Telex sends a message update
• FastAPI receives the JSON-RPC request
• The agent extracts user intent
• It either serves a new riddle, hint, or answer
• A Telex-formatted JSON-RPC response is returned

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
