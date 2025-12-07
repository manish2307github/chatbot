# 🤖 Multi-Turn Conversational AI Chatbot

A full-stack conversational AI application featuring a Flask backend, Neo4j graph database, intent classification, and a professional React frontend.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Environment Configuration](#environment-configuration)
- [Docker Deployment](#docker-deployment)
- [API Documentation](#api-documentation)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)

---

## 📖 Overview

This project implements a **multi-turn conversational AI chatbot** with:

✅ **Persistent Session Management** - Neo4j stores conversation history  
✅ **Intent Classification** - Keyword-based NLU pipeline  
✅ **Context-Aware Responses** - Retrieves last 6 messages for context  
✅ **Professional UI** - Modern React chat interface  
✅ **Security** - Input validation, sanitization, injection prevention  
✅ **Error Handling** - Graceful degradation with fallback responses  

### Use Cases

- Customer support chatbot
- FAQ assistant
- Order tracking
- Product information
- Return/refund processing

---

## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│         - Chat UI with message history                   │
│         - Session management                             │
│         - Real-time message display                      │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/CORS
┌──────────────────────▼──────────────────────────────────┐
│                  Flask Backend (Python)                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │ DialogueEngine (Orchestrates all components)    │    │
│  │  ├─ Intent Classification (Keyword-based)       │    │
│  │  ├─ Response Generation (Template/DialoGPT)     │    │
│  │  └─ Message Validation & Sanitization           │    │
│  └─────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────┘
                       │ Bolt Protocol
┌──────────────────────▼──────────────────────────────────┐
│              Neo4j Graph Database                        │
│  ├─ Session nodes (conversation metadata)               │
│  ├─ Message nodes (user & bot messages)                 │
│  └─ Relationships (session→messages, message history)   │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Purpose | Technology |
|-----------|---------|-----------|
| **Frontend** | Chat UI & session management | React 18, Tailwind CSS |
| **Backend** | Request handling & NLP pipeline | Flask, Python 3.9+ |
| **Database** | Conversation persistence | Neo4j 5.x |
| **Intent Classifier** | User intent detection | Keyword matching (Rasa-compatible) |
| **Response Generator** | AI responses | DialoGPT or fallback templates |

---

## 📦 Prerequisites

### System Requirements

- **Python 3.9+**
- **pip** (Python package manager)
- **Node.js 16+** (for React development, optional)
- **Docker & Docker Compose** (for containerized deployment)

### External Services

- **Neo4j Database** (local or Neo4j Sandbox)
  - Sandbox: https://sandbox.neo4j.com/ (Free, cloud-based)
  - Local: Docker image or standalone installation

### Development Tools (Optional)

- Git
- Visual Studio Code or PyCharm
- Postman (for API testing)
- Browser DevTools

---

## 🚀 Quick Start

### 1. Clone & Setup (5 minutes)

```bash
# Clone repository
git clone <repository-url>
cd NLP_CHATBOT_ASSIGNMENT

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file in project root:

```env
# Neo4j Configuration
NEO4J_URI=bolt://3.83.182.137:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=alternation-flaps-trigger

# Feature Flags
ENABLE_DIALOGO=false

# Flask Configuration
FLASK_ENV=development
PYTHONUNBUFFERED=1
```

**For Neo4j Sandbox:**
- Visit https://sandbox.neo4j.com/
- Create a free instance
- Copy connection details into .env

### 3. Start Backend

```bash
# Terminal 1: Backend
python app.py
```

Expected output:
```
✓ Neo4j manager initialized
✓ Rasa classifier initialized
✓ Using fallback response generator
✓ Dialogue engine initialized
Running on http://0.0.0.0:5000
```

### 4. Start Frontend

**Option A: Open HTML directly**
```bash
# Open in browser
open frontend/index.html
# Or drag index.html to browser
```

**Option B: Use Python HTTP server**
```bash
# Terminal 2: Frontend
cd frontend
python -m http.server 3000
# Visit http://localhost:3000
```

**Option C: React development**
```bash
# Terminal 2: Frontend
cd frontend
npm start
```

---

## 💻 Installation

### Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd NLP_CHATBOT_ASSIGNMENT
```

### Step 2: Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Key dependencies:**
- Flask 2.3+ (web framework)
- neo4j 5.13+ (database driver)
- torch 2.0+ (for DialoGPT, optional)
- transformers 4.30+ (NLP models, optional)

### Step 4: Configure Neo4j

**Option A: Neo4j Sandbox (Recommended for testing)**

1. Visit https://sandbox.neo4j.com/
2. Create free instance
3. Get connection details
4. Update `.env`:
   ```env
   NEO4J_URI=bolt://[your-instance-id].neo4jsandbox.com:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=[your-password]
   ```

**Option B: Local Neo4j Docker**

```bash
docker run --name neo4j -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

Then update `.env`:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

---

## 📝 Usage

### Running Locally

**Terminal 1 - Backend:**
```bash
python app.py
```

**Terminal 2 - Frontend:**
```bash
# Simple HTTP server
python -m http.server 3000 --directory frontend

# Or open frontend/index.html directly in browser
```

### Testing the Application

1. **Create Session:**
   ```bash
   curl -X POST http://localhost:5000/api/session/create
   ```

2. **Send Message:**
   ```bash
   curl -X POST http://localhost:5000/api/message/send \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "session_xxx",
       "message": "What is my order status?"
     }'
   ```

3. **Get History:**
   ```bash
   curl http://localhost:5000/api/conversation/history/session_xxx
   ```

4. **Health Check:**
   ```bash
   curl http://localhost:5000/api/health
   ```

### Example Conversation

**User:** "What's my order status?"
- Intent: `order_status` (confidence: 0.85)
- Response: "Thank you for asking about your order. Please provide your order number and I'll help you track it."

**User:** "I need to return an item"
- Intent: `return_refund` (confidence: 0.85)
- Response: "We're here to assist with returns and refunds. Please share your order number."

---

## ⚙️ Environment Configuration

### .env File

Create `.env` in project root:

```env
# ============================================
# Neo4j Configuration (REQUIRED)
# ============================================
NEO4J_URI=bolt://3.83.182.137:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password_here

# ============================================
# Feature Flags
# ============================================
# Set to "true" to enable DialoGPT (slow to load)
ENABLE_DIALOGO=false

# ============================================
# Flask Configuration
# ============================================
FLASK_ENV=development
FLASK_DEBUG=True
PYTHONUNBUFFERED=1

# ============================================
# API Configuration
# ============================================
CORS_ORIGINS=*
MAX_MESSAGE_LENGTH=1000
CONTEXT_WINDOW_SIZE=6
```

### Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://localhost:7687` | Database connection string |
| `NEO4J_USER` | `neo4j` | Database username |
| `NEO4J_PASSWORD` | `password` | Database password |
| `ENABLE_DIALOGO` | `false` | Enable DialoGPT model (slow) |
| `FLASK_ENV` | `development` | Flask environment |
| `FLASK_DEBUG` | `True` | Enable debug mode |

---

## 🐳 Docker Deployment

### Using Docker Compose

1. **Verify `docker-compose.yml` exists**

2. **Build and start:**
   ```bash
   docker-compose up --build
   ```

3. **Services will start:**
   - Backend: http://localhost:5000
   - Frontend: http://localhost:3000
   - Neo4j: http://localhost:7474 (if local)


MATCH (s:Session {session_id: "session_46b4ee403f004bc8"})-[:HAS_MESSAGE]->(m:Message)
RETURN m  

4. **View logs:**
   ```bash
   docker-compose logs -f backend
   ```

5. **Stop services:**
   ```bash
   docker-compose down
   ```

### Docker Build Only

```bash
# Build image
docker build -t chatbot-backend .

# Run container
docker run -p 5000:5000 \
  -e NEO4J_URI=bolt://3.83.182.137:7687 \
  -e NEO4J_USER=neo4j \
  -e NEO4J_PASSWORD=your_password \
  chatbot-backend
```

---

## 📡 API Documentation

### Endpoints

#### 1. Create Session
```http
POST /api/session/create
Content-Type: application/json

Response:
{
  "session_id": "session_a1b2c3d4e5f6",
  "status": "created",
  "timestamp": "2025-01-15T10:30:00"
}
```

#### 2. Send Message
```http
POST /api/message/send
Content-Type: application/json

Request:
{
  "session_id": "session_a1b2c3d4e5f6",
  "message": "What is my order status?"
}

Response:
{
  "status": "success",
  "session_id": "session_a1b2c3d4e5f6",
  "bot_response": "Thank you for asking about your order...",
  "intent": "order_status",
  "confidence": 0.85,
  "entities": {}
}
```

#### 3. Get Conversation History
```http
GET /api/conversation/history/{session_id}?limit=50

Response:
{
  "session_id": "session_a1b2c3d4e5f6",
  "messages": [
    {
      "message_id": "msg_xxx",
      "sender": "user",
      "text": "What is my order status?",
      "intent": "order_status",
      "timestamp": "2025-01-15T10:30:00"
    },
    {
      "message_id": "msg_yyy",
      "sender": "bot",
      "text": "Thank you for asking...",
      "intent": "response_to_order_status",
      "timestamp": "2025-01-15T10:30:05"
    }
  ],
  "count": 2
}
```

#### 4. Get Session Context
```http
GET /api/session/context/{session_id}

Response:
{
  "session_id": "session_a1b2c3d4e5f6",
  "metadata": {
    "created_at": "2025-01-15T10:30:00",
    "last_interaction": "2025-01-15T10:35:00",
    "interaction_count": 5,
    "user_intent": "order_status",
    "status": "active"
  }
}
```

#### 5. Health Check
```http
GET /api/health

Response:
{
  "status": "healthy",
  "components": {
    "neo4j": "connected",
    "rasa": "loaded",
    "dialogo": "loaded"
  },
  "timestamp": "2025-01-15T10:40:00"
}
```

### Error Responses

```json
{
  "status": "error",
  "error": "Failed to process message",
  "session_id": "session_xxx"
}
```

---

## 📁 Project Structure

```
NLP_CHATBOT_ASSIGNMENT/
├── app.py                          # Main Flask application
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables
├── .gitignore                     # Git ignore rules
├── docker-compose.yml             # Docker Compose configuration
├── Dockerfile                     # Backend Docker image
├── README.md                      # This file
│
├── frontend/
│   ├── index.html                # React app entry point
│   ├── ChatApp.jsx               # React component
│   └── ChatApp.css               # Styling
│
├── models/
│   └── [DialoGPT models - auto-downloaded]
│
└── logs/
    └── [Application logs]
```

### Key Files

| File | Purpose |
|------|---------|
| `app.py` | Flask backend, API endpoints, NLP pipeline |
| `requirements.txt` | Python package dependencies |
| `.env` | Sensitive configuration (not in git) |
| `frontend/index.html` | React app entry point |
| `docker-compose.yml` | Multi-container orchestration |

---

## 🔧 Troubleshooting

### Issue: "Failed to initialize Neo4j"

**Solution:**
```bash
# 1. Check Neo4j is running
curl http://3.83.182.137:7687/

# 2. Verify .env credentials
cat .env

# 3. Test connection manually
python test_sandbox.py

# 4. For Sandbox - ensure instance is not paused
# Visit https://sandbox.neo4j.com/ and check status
```

### Issue: "Backend not running" in Frontend

**Solution:**
```bash
# 1. Make sure backend is started
python app.py

# 2. Check backend is listening
curl http://localhost:5000/api/health

# 3. Check CORS is enabled in Flask
# Already configured with Flask-CORS
```

### Issue: "Module not found" errors

**Solution:**
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Or for specific package
pip install neo4j==5.13.0
```

### Issue: DialoGPT Loading Slowly

**Solution:**
```bash
# Keep ENABLE_DIALOGO=false (default)
# App uses fallback templates which are instant

# To enable only if needed:
export ENABLE_DIALOGO=true
python app.py
```

### Issue: Port Already in Use

**Solution:**
```bash
# Change port in app.py
# From: app.run(port=5000)
# To:   app.run(port=5001)

# Or kill existing process
# Linux/Mac:
lsof -i :5000 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Issue: CORS Errors

**Solution:**
- Backend has CORS enabled automatically
- If issues persist, check frontend is on same domain or add to CORS_ORIGINS

---

## 📚 Additional Resources

### Documentation
- [Neo4j Python Driver](https://neo4j.com/docs/python-manual/current/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Documentation](https://react.dev/)

### Learning Resources
- [Conversational AI Concepts](https://en.wikipedia.org/wiki/Conversational_AI)
- [Intent Classification](https://www.rasa.com/blog/rasa-nlu-best-practices/)
- [Graph Databases](https://neo4j.com/resources/)

---

## 📄 License

This project is provided as-is for educational purposes.

---

## ✨ Features Summary

### Current Implementation (✅)
- Multi-turn conversation with persistent storage
- Intent classification (5 intents)
- Neo4j session & message management
- Input validation & sanitization
- REST API endpoints
- Professional React UI
- Error handling & graceful degradation
- Docker support

### Future Enhancements (🔄)
- Advanced NLP with trained Rasa models
- DialoGPT integration for natural responses
- Multi-language support
- Analytics & conversation insights
- User authentication
- Admin dashboard
- Real-time WebSocket communication

---

## 👥 Support

For issues or questions:
1. Check [Troubleshooting](#troubleshooting) section
2. Review error logs: `docker-compose logs backend`
3. Test API manually with curl/Postman
4. Verify .env configuration

---

**Last Updated:** January 2025  
**Version:** 1.0  
**Status:** Production Ready ✅