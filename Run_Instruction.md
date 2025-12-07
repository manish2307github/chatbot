# 🤖 Multi-Turn Conversational AI Chatbot

A full-stack conversational AI application featuring a Flask backend, Neo4j graph database, intent classification, entity extraction, and a professional React frontend with feedback system.

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
✅ **Intent Classification** - Keyword-based NLU pipeline with 5 intents  
✅ **Entity Extraction** - Extracts order numbers, products, emails, dates, amounts  
✅ **Context-Aware Responses** - Retrieves last 6 messages for context  
✅ **Feedback System** - Users can rate responses with 👍/👎  
✅ **Analytics Dashboard** - Real-time conversation insights  
✅ **Professional UI** - Modern React chat interface with typing indicators  
✅ **Security** - Input validation, sanitization, injection prevention, rate limiting  
✅ **Error Handling** - Graceful degradation with fallback responses  
✅ **Export Functionality** - Download conversation history as JSON  

### Use Cases

- Customer support chatbot
- FAQ assistant
- Order tracking and status inquiries
- Product information queries
- Return/refund processing
- Troubleshooting assistance

---

## 🏗️ Architecture

### System Design

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React)                      │
│         - Chat UI with message history                   │
│         - Session management                             │
│         - Real-time feedback system                      │
│         - Analytics display                              │
│         - Export conversations                           │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/CORS
┌──────────────────────▼──────────────────────────────────┐
│                  Flask Backend (Python)                  │
│  ┌─────────────────────────────────────────────────┐    │
│  │ DialogueEngine (Orchestrates all components)    │    │
│  │  ├─ Intent Classification (5 intents)           │    │
│  │  ├─ Entity Extraction (5 entity types)          │    │
│  │  ├─ Response Generation (Context-aware)         │    │
│  │  ├─ Topic Shift Detection                       │    │
│  │  └─ Message Validation & Sanitization           │    │
│  └─────────────────────────────────────────────────┘    │
│  ├─ Rate Limiting (50/hour, 200/day)                    │
│  ├─ Feedback Collection                                  │
│  └─ Analytics Aggregation                               │
└──────────────────────┬──────────────────────────────────┘
                       │ Bolt Protocol
┌──────────────────────▼──────────────────────────────────┐
│              Neo4j Graph Database                        │
│  ├─ Session nodes (metadata, topics_discussed)          │
│  ├─ Message nodes (user & bot, feedback, entities)      │
│  ├─ Relationships (HAS_MESSAGE)                         │
│  └─ Indexes (session_id, message_id unique)            │
└─────────────────────────────────────────────────────────┘
```

### Components

| Component | Purpose | Technology |
|-----------|---------|-----------|
| **Frontend** | Chat UI, feedback, analytics | React 18, Vanilla JS |
| **Backend** | Request handling & NLP pipeline | Flask 2.3+, Python 3. **Set reminder:**
   - Sandbox expires after 10 days
   - Export your data before expiration using the export endpoint

### Issue: Messages Not Showing Context

**Symptoms:**
- Bot responses don't reference previous messages
- No "followup" detection working

**Solutions:**

1. **Verify CONTEXT_WINDOW_SIZE:**
```python
# In app.py Config class:
CONTEXT_WINDOW_SIZE = 6  # Should retrieve last 6 messages
```

2. **Check conversation history:**
```bash
curl http://localhost:5000/api/conversation/history/session_xxx?limit=10
```

3. **Verify Neo4j relationships:**
```cypher
MATCH (s:Session {session_id: "session_xxx"})-[:HAS_MESSAGE]->(m:Message)
RETUR9+ |
| **Database** | Conversation persistence | Neo4j 5.x |
| **Intent Classifier** | User intent detection (5 intents) | Keyword matching with confidence scores |
| **Entity Extractor** | Extract structured data | Regex patterns (orders, products, etc.) |
| **Response Generator** | Context-aware AI responses | Template-based with followup detection |
| **Rate Limiter** | API protection | Flask-Limiter |

---

## 📦 Prerequisites

### System Requirements

- **Python 3.9+**
- **pip** (Python package manager)
- **Neo4j 5.x** (local or cloud)

### External Services

- **Neo4j Database** (choose one option)
  - Neo4j Sandbox: https://sandbox.neo4j.com/ (Free, recommended)
  - Neo4j Aura: https://neo4j.com/cloud/aura/ (Production)
  - Local Docker: `docker run neo4j:latest`

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
cd chatbot-project

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
NEO4J_PASSWORD=your_password_here
```

**For Neo4j Sandbox (Recommended):**
1. Visit https://sandbox.neo4j.com/
2. Create a free instance (no credit card required)
3. Copy connection details into `.env`
4. Instance auto-pauses after 3 days of inactivity

### 3. Start Backend

```bash
python app.py
```

Expected output:
```
2025-12-07 15:30:00 - __main__ - INFO - Connected to Neo4j at bolt://...
2025-12-07 15:30:00 - __main__ - INFO - Database constraints created successfully
2025-12-07 15:30:00 - __main__ - INFO - EnhancedIntentClassifier initialized
2025-12-07 15:30:00 - __main__ - INFO - DialogueEngine initialized
2025-12-07 15:30:00 - __main__ - INFO - ✓ All components initialized successfully!
 * Running on http://0.0.0.0:5000
```

### 4. Start Frontend

**Option A: Open HTML directly (Simplest)**
```bash
# Just open the file in your browser
open index.html  # macOS
start index.html  # Windows
xdg-open index.html  # Linux
```

**Option B: Use Python HTTP server**
```bash
python -m http.server 3000
# Visit http://localhost:3000
```

### 5. Test the Chatbot

Try these sample queries:
- "What's my order #12345 status?"
- "I want to return order 67890"
- "Tell me about your laptop"
- "My phone is broken, help!"
- "What are your shipping options?"

---

## 💻 Installation

### Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd chatbot-project
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
```
Flask==2.3.3
flask-cors==4.0.0
flask-limiter==3.5.0
neo4j==5.13.0
python-dotenv==1.0.0
flasgger==0.9.7.1
```

### Step 4: Configure Neo4j

**Option A: Neo4j Sandbox (Recommended for testing)**

1. Visit https://sandbox.neo4j.com/
2. Click "New Project" → "Create Sandbox"
3. Choose "Blank Sandbox"
4. Get connection details from "Connection details" tab
5. Update `.env`:
   ```env
   NEO4J_URI=bolt://[instance-id].databases.neo4j.io
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=[your-generated-password]
   ```

**Option B: Local Neo4j Docker**

```bash
docker run --name neo4j \
  -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  -v $HOME/neo4j/data:/data \
  neo4j:5.13.0
```

Then update `.env`:
```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

**Option C: Neo4j Aura (Production)**

1. Visit https://neo4j.com/cloud/aura/
2. Create free tier account
3. Create database instance
4. Copy connection string to `.env`

---

## 📝 Usage

### Running Locally

**Terminal 1 - Backend:**
```bash
python app.py
```

**Terminal 2 - Frontend:**
```bash
# Simple: Just open index.html in your browser
# OR use a local server:
python -m http.server 3000
```

### Testing the Application

#### 1. Health Check
```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "2.0",
  "components": {
    "neo4j": "connected",
    "classifier": "loaded",
    "generator": "loaded"
  },
  "timestamp": "2025-12-07T15:30:00"
}
```

#### 2. Create Session
```bash
curl -X POST http://localhost:5000/api/session/create \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "session_id": "session_46b4ee403f00",
  "status": "created",
  "timestamp": "2025-12-07T15:30:00"
}
```

#### 3. Send Message
```bash
curl -X POST http://localhost:5000/api/message/send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_46b4ee403f00",
    "message": "What is my order #12345 status?"
  }'
```

Response:
```json
{
  "status": "success",
  "session_id": "session_46b4ee403f00",
  "bot_response": "Thank you! I found order #12345. It's currently in transit...",
  "bot_message_id": "msg_a1b2c3d4e5f6",
  "intent": "order_status",
  "confidence": 0.9,
  "entities": {
    "order_number": "12345"
  },
  "is_followup": false,
  "context_messages": 0
}
```

#### 4. Submit Feedback
```bash
curl -X POST http://localhost:5000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "msg_a1b2c3d4e5f6",
    "feedback": "positive"
  }'
```

#### 5. Get Analytics
```bash
curl http://localhost:5000/api/analytics/summary
```

Response:
```json
{
  "total_sessions": 5,
  "total_messages": 24,
  "avg_messages_per_session": 4.8,
  "intent_distribution": {
    "order_status": 8,
    "product_info": 6,
    "return_refund": 4,
    "general_inquiry": 6
  },
  "positive_feedback_count": 15,
  "negative_feedback_count": 2
}
```

### Example Conversations

#### Order Status Query
```
User: "What's my order status?"
Bot: "I'd be happy to help you track your order! Could you please provide your order number?"

User: "Order #12345"
Bot: "Thank you! I found order #12345. It's currently in transit and should arrive within 3-5 business days."
[User gives 👍 feedback]
```

#### Return Request
```
User: "I need to return an item"
Bot: "I'm sorry you'd like to return something. I can definitely help with that. What's your order number?"

User: "Order 67890"
Bot: "Thank you for order #67890. You're within our 30-day return window. I'll send you a return label via email."
```

#### Product Inquiry
```
User: "Tell me about your laptop"
Bot: "The laptop is a popular choice! It's priced at $299 and currently in stock. Would you like to know more about its features?"
```

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
# Flask Configuration (Optional)
# ============================================
FLASK_ENV=development
FLASK_DEBUG=True
PYTHONUNBUFFERED=1
```

### Configuration Reference

The application uses these configuration values (defined in `Config` class):

| Setting | Value | Description |
|---------|-------|-------------|
| `MAX_MESSAGE_LENGTH` | 1000 | Maximum characters per message |
| `MIN_MESSAGE_LENGTH` | 1 | Minimum characters per message |
| `CONFIDENCE_THRESHOLD` | 0.5 | Minimum confidence for intent classification |
| `CONTEXT_WINDOW_SIZE` | 6 | Number of past messages to retrieve |
| `TOPIC_OVERLAP_THRESHOLD` | 0.5 | Threshold for detecting followup questions |

### Rate Limiting

- **Per minute:** 30 requests for `/api/message/send`
- **Per hour:** 50 requests (default)
- **Per day:** 200 requests (default)

---

## 🐳 Docker Deployment

### Prerequisites
- Docker 20.10+
- Docker Compose 2.0+

### Quick Deploy

1. **Create `docker-compose.yml`:**

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.13.0
    ports:
      - "7687:7687"
      - "7474:7474"
    environment:
      NEO4J_AUTH: neo4j/password
    volumes:
      - neo4j_data:/data

  backend:
    build: .
    ports:
      - "5000:5000"
    environment:
      NEO4J_URI: bolt://neo4j:7687
      NEO4J_USER: neo4j
      NEO4J_PASSWORD: password
    depends_on:
      - neo4j

  frontend:
    image: nginx:alpine
    ports:
      - "3000:80"
    volumes:
      - ./frontend:/usr/share/nginx/html:ro

volumes:
  neo4j_data:
```

2. **Create `Dockerfile`:**

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY .env .

EXPOSE 5000

CMD ["python", "app.py"]
```

3. **Build and Start:**
```bash
docker-compose up --build -d
```

4. **Access Services:**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:5000
   - Neo4j Browser: http://localhost:7474

5. **View Logs:**
```bash
docker-compose logs -f backend
```

6. **Stop Services:**
```bash
docker-compose down
```

### Single Container (Backend Only)

```bash
# Build
docker build -t chatbot-backend .

# Run
docker run -p 5000:5000 \
  -e NEO4J_URI=bolt://your-neo4j-host:7687 \
  -e NEO4J_USER=neo4j \
  -e NEO4J_PASSWORD=password \
  chatbot-backend
```

---

## 📡 API Documentation

### Base URL
```
http://localhost:5000/api
```

### Authentication
No authentication required (add JWT/OAuth for production)

### Endpoints

#### 1. Create Session
Create a new conversation session.

```http
POST /api/session/create
Content-Type: application/json

Request Body (optional):
{
  "user_id": "user_123"
}

Response (201 Created):
{
  "session_id": "session_a1b2c3d4e5f6",
  "status": "created",
  "timestamp": "2025-12-07T15:30:00"
}
```

#### 2. Send Message
Send a user message and get bot response.

```http
POST /api/message/send
Content-Type: application/json

Request Body:
{
  "session_id": "session_a1b2c3d4e5f6",
  "message": "What is my order #12345 status?"
}

Response (200 OK):
{
  "status": "success",
  "session_id": "session_a1b2c3d4e5f6",
  "bot_response": "Thank you! I found order #12345...",
  "bot_message_id": "msg_xyz123",
  "intent": "order_status",
  "confidence": 0.9,
  "entities": {
    "order_number": "12345"
  },
  "is_followup": false,
  "context_messages": 2
}
```

**Intent Types:**
- `order_status` - Order tracking queries
- `product_info` - Product information requests
- `return_refund` - Return/refund inquiries
- `troubleshooting` - Technical support
- `shipping` - Shipping/delivery questions
- `general_inquiry` - General questions

**Entity Types:**
- `order_number` - Order IDs (e.g., #12345)
- `product_name` - Product names (laptop, phone, etc.)
- `amount` - Monetary values ($99.99)
- `email` - Email addresses
- `date` - Dates (MM/DD/YYYY)

#### 3. Submit Feedback
Rate a bot response as helpful or not helpful.

```http
POST /api/feedback
Content-Type: application/json

Request Body:
{
  "message_id": "msg_xyz123",
  "feedback": "positive"  // or "negative"
}

Response (200 OK):
{
  "status": "success",
  "message_id": "msg_xyz123",
  "feedback": "positive",
  "message": "Feedback saved to Neo4j database"
}
```

#### 4. Get Conversation History
Retrieve message history for a session.

```http
GET /api/conversation/history/{session_id}?limit=50

Response (200 OK):
{
  "session_id": "session_a1b2c3d4e5f6",
  "messages": [
    {
      "message_id": "msg_user1",
      "sender": "user",
      "text": "What is my order status?",
      "intent": "order_status",
      "entities": {},
      "confidence": 0.85,
      "timestamp": "2025-12-07T15:30:00"
    },
    {
      "message_id": "msg_bot1",
      "sender": "bot",
      "text": "I'd be happy to help...",
      "intent": "response_to_order_status",
      "entities": null,
      "confidence": 0.95,
      "timestamp": "2025-12-07T15:30:01"
    }
  ],
  "count": 2
}
```

#### 5. Get Session Context
Retrieve session metadata.

```http
GET /api/session/context/{session_id}

Response (200 OK):
{
  "session_id": "session_a1b2c3d4e5f6",
  "metadata": {
    "session_id": "session_a1b2c3d4e5f6",
    "created_at": "2025-12-07T15:30:00",
    "last_interaction": "2025-12-07T15:35:00",
    "interaction_count": 5,
    "user_intent": "order_status",
    "topic": "order_status",
    "status": "active",
    "topics_discussed": ["order_status", "product_info"]
  },
  "timestamp": "2025-12-07T15:40:00"
}
```

#### 6. Get Analytics
Retrieve system-wide conversation analytics.

```http
GET /api/analytics/summary

Response (200 OK):
{
  "total_sessions": 15,
  "total_messages": 73,
  "avg_messages_per_session": 4.87,
  "intent_distribution": {
    "order_status": 25,
    "product_info": 18,
    "return_refund": 12,
    "troubleshooting": 8,
    "shipping": 10
  },
  "positive_feedback_count": 45,
  "negative_feedback_count": 8
}
```

#### 7. Export Conversation
Download conversation history as JSON.

```http
GET /api/conversation/export/{session_id}

Response (200 OK):
Content-Disposition: attachment; filename=conversation_session_xxx.json

{
  "session_id": "session_a1b2c3d4e5f6",
  "exported_at": "2025-12-07T15:45:00",
  "messages": [...]
}
```

#### 8. Health Check
Check if the API is running and all components are healthy.

```http
GET /api/health

Response (200 OK):
{
  "status": "healthy",
  "version": "2.0",
  "components": {
    "neo4j": "connected",
    "classifier": "loaded",
    "generator": "loaded"
  },
  "timestamp": "2025-12-07T15:50:00"
}
```

### Error Responses

All endpoints return standard error formats:

```json
{
  "status": "error",
  "error": "Message cannot be empty"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `201` - Created (new session)
- `400` - Bad Request (validation error)
- `404` - Not Found (session/message not found)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

---

## 📁 Project Structure

```
chatbot-project/
├── app.py                          # Main Flask application (800+ lines)
│   ├── Config                      # Application configuration
│   ├── MessageValidator            # Input validation & sanitization
│   ├── Neo4jSessionManager         # Database operations
│   ├── EnhancedIntentClassifier    # Intent detection (5 intents)
│   ├── EnhancedResponseGenerator   # Context-aware responses
│   └── DialogueEngine              # Orchestrates all components
│
├── requirements.txt                # Python dependencies
├── .env                           # Environment variables (gitignored)
├── .gitignore                     # Git ignore rules
├── README.md                      # This file
│
├── index.html                     # Frontend application
│   ├── React UI components
│   ├── Feedback system
│   ├── Analytics display
│   └── Export functionality
│
├── docker-compose.yml             # Multi-container orchestration
├── Dockerfile                     # Backend Docker image
│
└── logs/                          # Application logs (auto-created)
```

### Key Files Explained

| File | Lines of Code | Purpose |
|------|---------------|---------|
| `app.py` | 800+ | Complete backend logic, API endpoints, NLP pipeline |
| `index.html` | 400+ | Full frontend React application |
| `requirements.txt` | 10 | Python package dependencies |
| `.env` | 3-5 | Sensitive configuration |
| `docker-compose.yml` | 30-40 | Container orchestration |

---

## 🔧 Troubleshooting

### Issue: "Failed to connect to Neo4j"

**Symptoms:**
```
ERROR - Failed to connect to Neo4j: Unable to retrieve routing information
```

**Solutions:**

1. **Check Neo4j is running:**
```bash
# For Docker
docker ps | grep neo4j

# For Sandbox
# Visit https://sandbox.neo4j.com/ and ensure instance is active
```

2. **Verify credentials in `.env`:**
```bash
cat .env
# Ensure NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD are correct
```

3. **Test connection manually:**
```python
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://your-host:7687",
    auth=("neo4j", "your-password")
)

with driver.session() as session:
    result = session.run("RETURN 1")
    print(result.single()[0])  # Should print: 1
```

4. **For Sandbox instances:**
   - Check if instance is paused (auto-pauses after 3 days)
   - Click "Resume" in Neo4j Sandbox dashboard
   - Wait 30-60 seconds for instance to start

### Issue: "Backend not running" Error in Frontend

**Symptoms:**
- Red banner: "Backend not running. Start with: python app.py"
- No responses from chatbot

**Solutions:**

1. **Verify backend is running:**
```bash
# Check if process is running
ps aux | grep python | grep app.py

# Test health endpoint
curl http://localhost:5000/api/health
```

2. **Check for port conflicts:**
```bash
# See what's using port 5000
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows
```

3. **Review backend logs:**
```bash
# Look for error messages in terminal where app.py is running
# Common issues: Missing .env, wrong Neo4j credentials
```

4. **CORS issues:**
   - Already configured with `flask-cors`
   - If still issues, check browser console (F12) for CORS errors

### Issue: "Module not found" Errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'neo4j'
```

**Solutions:**

1. **Ensure virtual environment is activated:**
```bash
# Look for (venv) in terminal prompt
# If not present:
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows
```

2. **Reinstall dependencies:**
```bash
pip install --upgrade -r requirements.txt
```

3. **For specific packages:**
```bash
pip install neo4j==5.13.0
pip install flask==2.3.3
pip install flask-cors==4.0.0
```

4. **Clear pip cache if issues persist:**
```bash
pip cache purge
pip install -r requirements.txt
```

### Issue: Feedback Buttons Not Working

**Symptoms:**
- Clicking 👍 or 👎 does nothing
- No visual feedback when clicking buttons

**Solutions:**

1. **Check browser console (F12 → Console):**
```javascript
// Should see:
"Submitting positive feedback for message: msg_xyz123"
"Feedback saved successfully: {status: 'success', ...}"
```

2. **Verify message has valid ID:**
   - Frontend must receive `bot_message_id` from backend
   - Check network tab (F12 → Network) for `/api/message/send` response

3. **Test feedback endpoint directly:**
```bash
curl -X POST http://localhost:5000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{"message_id": "msg_test123", "feedback": "positive"}'
```

4. **Verify in Neo4j:**
```cypher
// Run in Neo4j Browser (http://localhost:7474)
MATCH (m:Message)
WHERE m.feedback IS NOT NULL
RETURN m.message_id, m.feedback, m.feedback_timestamp
ORDER BY m.feedback_timestamp DESC
LIMIT 10
```

### Issue: Analytics Not Showing

**Symptoms:**
- Analytics panel shows zeros or doesn't appear
- Stats don't update after conversations

**Solutions:**

1. **Check if data exists in Neo4j:**
```cypher
MATCH (s:Session)-[:HAS_MESSAGE]->(m:Message)
RETURN count(s) as sessions, count(m) as messages
```

2. **Test analytics endpoint:**
```bash
curl http://localhost:5000/api/analytics/summary
```

3. **Review backend logs:**
```bash
# Look for analytics errors
grep "Analytics error" logs/*.log
```

4. **Clear browser cache:**
   - Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

### Issue: Port Already in Use

**Symptoms:**
```
OSError: [Errno 48] Address already in use
```

**Solutions:**

1. **Find and kill process using port 5000:**

**macOS/Linux:**
```bash
lsof -i :5000
kill -9 <PID>
```

**Windows:**
```bash
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

2. **Use different port:**
```python
# In app.py, change last line:
app.run(debug=True, host='0.0.0.0', port=5001)  # Changed from 5000
```

3. **Update frontend to use new port:**
```javascript
// In index.html, change:
const API_BASE = "http://localhost:5001/api";  // Changed from 5000
```

### Issue: Rate Limit Exceeded

**Symptoms:**
```json
{
  "error": "429 Too Many Requests: 30 per 1 minute"
}
```

**Solutions:**

1. **Wait for rate limit window to reset** (1 minute for message sending)

2. **Adjust rate limits in `app.py`:**
```python
# Find this line and modify:
@limiter.limit("30 per minute")  # Change to "60 per minute"
```

3. **Disable rate limiting for testing:**
```python
# Comment out the limiter decorator:
# @limiter.limit("30 per minute")
def send_message():
    ...
```

### Issue: Neo4j Sandbox Instance Paused

**Symptoms:**
- Connection works initially, then fails after a few days
- Error: "Unable to retrieve routing information"

**Solutions:**

1. **Resume instance:**
   - Go to https://sandbox.neo4j.com/
   - Find your instance
   - Click "Resume" button
   - Wait 30-60 seconds

2. **Keep instance active:**
   - Sandbox instances auto-pause after 3 days of inactivity
   - Make sure to use chatbot regularly
   - Or upgrade to Neo4j Aura for always-on database

3.