# 🧪 Testing Guide for Enhanced Chatbot

## Quick Test Commands

# Test order number extraction
curl -X POST http://localhost:5000/api/message/send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_123",
    "message": "What is the status of my order #12345?"
  }'

# Expected Response:
{
  "status": "success",
  "bot_response": "Thank you! I found order #12345. It's currently in transit...",
  "intent": "order_status",
  "confidence": 0.9,
  "entities": {
    "order_number": "12345"
  }
}

### 2. Test Context Awareness (Follow-up)
# First message
curl -X POST http://localhost:5000/api/message/send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_456",
    "message": "I want to buy a laptop"
  }'

# Follow-up (should recognize continuation)
curl -X POST http://localhost:5000/api/message/send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_456",
    "message": "What is the price?"
  }'

# Expected: Bot should understand "price" refers to "laptop"

### 3. Test Topic Shift Detection

# Session 1: Start with order status
curl -X POST http://localhost:5000/api/message/send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_789",
    "message": "Where is my order?"
  }'

# Session 1: Shift to product info
curl -X POST http://localhost:5000/api/message/send \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_789",
    "message": "Actually, I want to ask about laptop features"
  }'

# Expected Response should contain: "Now let me help you with product information."


### 4. Test Feedback System

```bash
# Send feedback
curl -X POST http://localhost:5000/api/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "msg_abc123",
    "feedback": "positive"
  }'

# Expected:
{
  "status": "success",
  "message_id": "msg_abc123",
  "feedback": "positive"
}
```

### 5. Test Analytics Endpoint

```bash
curl http://localhost:5000/api/analytics/summary

# Expected:
{
  "total_sessions": 15,
  "total_messages": 87,
  "avg_messages_per_session": 5.8,
  "intent_distribution": {
    "order_status": 25,
    "product_info": 18,
    "return_refund": 12,
    "troubleshooting": 8,
    "shipping": 15,
    "general_inquiry": 9
  },
  "positive_feedback_count": 42,
  "negative_feedback_count": 8
}
```

### 6. Test Conversation Export

curl http://localhost:5000/api/conversation/export/test_session_123 > conversation.json

# Check the downloaded file
cat conversation.json

### 7. Test Rate Limiting

# Send 35 requests rapidly (limit is 30/min)
for i in {1..35}; do
  curl -X POST http://localhost:5000/api/message/send \
    -H "Content-Type: application/json" \
    -d "{\"session_id\": \"test_rate_limit\", \"message\": \"Test $i\"}" &
done
wait

# Expected: Last 5 requests should return 429 (Too Many Requests)
## 🎯 Feature Testing Checklist

### ✅ Enhanced Entity Extraction
- [ ] Order numbers: `#12345`, `order 67890`
- [ ] Products: `laptop`, `phone`, `keyboard`
- [ ] Amounts: `$299`, `$49.99`
- [ ] Emails: `user@example.com`
- [ ] Dates: `12/15/2024`, `01-20-2025`

### ✅ Context-Aware Responses
- [ ] First-time questions get introductory responses
- [ ] Follow-up questions show continuity
- [ ] Responses include entity values (e.g., "Order #12345")
- [ ] Related intents maintain context

### ✅ Topic Shift Detection
- [ ] Changing from order_status → product_info shows transition message
- [ ] Related intents (order_status ↔ shipping) don't trigger shift
- [ ] Session metadata tracks all discussed topics

### ✅ Feedback System
- [ ] 👍 Positive feedback recorded
- [ ] 👎 Negative feedback recorded
- [ ] Analytics show feedback counts
- [ ] Frontend updates feedback state immediately

### ✅ Analytics Dashboard
- [ ] Total sessions count accurate
- [ ] Average messages per session calculated
- [ ] Intent distribution shows all intents
- [ ] Feedback counts displayed

### ✅ Conversation Export
- [ ] JSON file downloads correctly
- [ ] Contains all messages with metadata
- [ ] Timestamp of export included
- [ ] File naming uses session_id

### ✅ Rate Limiting
- [ ] 30 messages/minute limit enforced
- [ ] 429 error returned when exceeded
- [ ] Error message explains rate limit

## 🧪 End-to-End Test Scenarios

### Scenario 1: Order Tracking with Entity
```
User: "What's the status of order #12345?"
Bot: "Thank you! I found order #12345. It's currently in transit..."
  ✓ Entity extracted: order_number = 12345
  ✓ Intent: order_status (confidence: 0.9)
  ✓ Response includes order number

User: "When will it arrive?"
Bot: "Your order is being processed and will ship within 24 hours..."
  ✓ Recognized as follow-up (is_followup: true)
  ✓ Context: Previous message about order #12345
  ✓ No topic shift detected


### Scenario 2: Product Inquiry → Return
```
User: "Tell me about your laptops"
Bot: "I'd be happy to help! Which product would you like to learn more about?"
  ✓ Intent: product_info (confidence: 0.85)
  ✓ First-time question response

User: "Actually, I need to return my laptop"
Bot: "I understand you want to process a return. I'm sorry you'd like..."
  ✓ Topic shift detected (product_info → return_refund)
  ✓ Prefix added: "I understand you want to process a return."
  ✓ Session topics_discussed: [product_info, return_refund]
```

### Scenario 3: Feedback Loop
```
User: "My product is broken"
Bot: "I'm sorry you're experiencing an issue. What exactly is happening?"
  ✓ Intent: troubleshooting
  
User: [Clicks 👍]
  ✓ Feedback: positive
  ✓ Neo4j updated with feedback timestamp
  ✓ Analytics increments positive_feedback_count
  
Admin: Checks analytics
  ✓ Dashboard shows 1 positive feedback
  ✓ Intent distribution shows troubleshooting: 1
```

## 🔍 Neo4j Database Verification

### Check Session with Context
```cypher
MATCH (s:Session {session_id: "test_session_123"})-[:HAS_MESSAGE]->(m:Message)
RETURN s.user_intent, s.topics_discussed, collect(m.text) as messages
```

### Verify Entity Storage
```cypher
MATCH (m:Message)
WHERE m.entities IS NOT NULL
RETURN m.text, m.entities, m.intent
LIMIT 10
```

### Check Feedback Data
```cypher
MATCH (m:Message)
WHERE m.feedback IS NOT NULL
RETURN m.text, m.feedback, m.feedback_timestamp
ORDER BY m.feedback_timestamp DESC
LIMIT 20
```

### Analyze Intent Distribution
```cypher
MATCH (m:Message)
WHERE m.intent IS NOT NULL AND m.sender = 'user'
RETURN m.intent, count(*) as count
ORDER BY count DESC
