from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import datetime
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
import os
import logging
import re
from flasgger import Swagger
from dotenv import load_dotenv
from functools import lru_cache
import hashlib

# Neo4j imports
from neo4j import GraphDatabase

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
class Config:
    MAX_MESSAGE_LENGTH = 1000
    MIN_MESSAGE_LENGTH = 1
    CONFIDENCE_THRESHOLD = 0.5
    CONTEXT_WINDOW_SIZE = 6
    MAX_RESPONSE_LENGTH = 200
    SESSION_TIMEOUT_HOURS = 24
    TOPIC_OVERLAP_THRESHOLD = 0.5

# ==================== INPUT VALIDATION ====================
class MessageValidator:
    @staticmethod
    def validate_message(text: str) -> Tuple[bool, str]:
        if not text or not text.strip():
            return False, "Message cannot be empty"
        if len(text) > Config.MAX_MESSAGE_LENGTH:
            return False, f"Message exceeds {Config.MAX_MESSAGE_LENGTH} characters"
        if len(text) < Config.MIN_MESSAGE_LENGTH:
            return False, "Message too short"
        if re.search(r'<script|javascript:|onerror=', text, re.IGNORECASE):
            return False, "Invalid message format"
        return True, ""
    
    @staticmethod
    def sanitize_message(text: str) -> str:
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        return text

# ==================== NEO4J SESSION MANAGER ====================
class Neo4jSessionManager:
    def __init__(self, uri: str, user: str, password: str, max_connections: int = 50):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password), max_connection_pool_size=max_connections, connection_acquisition_timeout=30.0)
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j at {uri}")
            self._create_constraints()
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def _create_constraints(self):
        try:
            with self.driver.session() as session:
                session.execute_write(lambda tx: tx.run("CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.session_id IS UNIQUE"))
                session.execute_write(lambda tx: tx.run("CREATE CONSTRAINT message_id_unique IF NOT EXISTS FOR (m:Message) REQUIRE m.message_id IS UNIQUE"))
            logger.info("Database constraints created successfully")
        except Exception as e:
            logger.warning(f"Constraint creation warning: {e}")
    
    def create_session(self, user_id: str = None) -> str:
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        try:
            with self.driver.session() as session:
                session.execute_write(self._create_session_node, session_id, user_id)
            logger.info(f"Created session: {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    @staticmethod
    def _create_session_node(tx, session_id: str, user_id: str = None):
        query = """CREATE (s:Session {session_id: $session_id, user_id: $user_id, created_at: datetime(), last_interaction: datetime(), interaction_count: 0, user_intent: null, topic: null, status: 'active', topics_discussed: []}) RETURN s"""
        tx.run(query, session_id=session_id, user_id=user_id)
    
    def add_message(self, session_id: str, sender: str, text: str, intent: str = None, entities: Dict = None, confidence: float = None) -> Dict:
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        try:
            with self.driver.session() as session:
                result = session.execute_write(self._add_message_node, session_id, message_id, sender, text, intent, entities, confidence)
            return result
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise
    
    @staticmethod
    def _add_message_node(tx, session_id: str, message_id: str, sender: str, text: str, intent: str = None, entities: Dict = None, confidence: float = None) -> Dict:
        query = """MATCH (s:Session {session_id: $session_id}) CREATE (m:Message {message_id: $message_id, sender: $sender, text: $text, intent: $intent, entities: $entities, confidence: $confidence, timestamp: datetime(), token_count: $token_count, feedback: null}) CREATE (s)-[:HAS_MESSAGE]->(m) SET s.last_interaction = datetime(), s.interaction_count = s.interaction_count + 1 RETURN m"""
        token_count = len(text.split())
        tx.run(query, session_id=session_id, message_id=message_id, sender=sender, text=text, intent=intent, entities=json.dumps(entities) if entities else None, confidence=confidence, token_count=token_count)
        return {"message_id": message_id, "status": "added"}
    
    def get_conversation_context(self, session_id: str, num_messages: int = 5) -> List[Dict]:
        try:
            with self.driver.session() as session:
                result = session.execute_read(self._fetch_recent_messages, session_id, num_messages)
            return result
        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return []
    
    @staticmethod
    def _fetch_recent_messages(tx, session_id: str, num_messages: int) -> List[Dict]:
        query = """MATCH (s:Session {session_id: $session_id})-[:HAS_MESSAGE]->(m:Message) RETURN m ORDER BY m.timestamp DESC LIMIT $limit"""
        result = tx.run(query, session_id=session_id, limit=num_messages)
        messages = []
        for record in result:
            msg = record["m"]
            try:
                entities = json.loads(msg.get('entities', '{}') or '{}')
            except (json.JSONDecodeError, TypeError):
                entities = {}
            message_data = {'message_id': msg['message_id'], 'sender': msg['sender'], 'text': msg['text'], 'intent': msg.get('intent'), 'entities': entities, 'confidence': msg.get('confidence'), 'timestamp': str(msg['timestamp'])}
            messages.append(message_data)
        return list(reversed(messages))
    
    def get_session_metadata(self, session_id: str) -> Optional[Dict]:
        try:
            with self.driver.session() as session:
                result = session.execute_read(self._fetch_session_metadata, session_id)
            return result
        except Exception as e:
            logger.error(f"Failed to get session metadata: {e}")
            return None
    
    @staticmethod
    def _fetch_session_metadata(tx, session_id: str) -> Optional[Dict]:
        query = """MATCH (s:Session {session_id: $session_id}) RETURN s"""
        result = tx.run(query, session_id=session_id)
        record = result.single()
        if not record:
            return None
        session_node = record["s"]
        return {'session_id': session_node['session_id'], 'created_at': str(session_node['created_at']), 'last_interaction': str(session_node['last_interaction']), 'interaction_count': session_node['interaction_count'], 'user_intent': session_node.get('user_intent'), 'topic': session_node.get('topic'), 'status': session_node.get('status', 'active'), 'topics_discussed': session_node.get('topics_discussed', [])}
    
    def update_session_intent(self, session_id: str, intent: str, topic: str = None):
        try:
            with self.driver.session() as session:
                session.execute_write(self._update_intent, session_id, intent, topic)
        except Exception as e:
            logger.error(f"Failed to update session intent: {e}")
    
    @staticmethod
    def _update_intent(tx, session_id: str, intent: str, topic: str = None):
        query = """MATCH (s:Session {session_id: $session_id}) SET s.user_intent = $intent, s.topic = coalesce($topic, s.topic), s.topics_discussed = CASE WHEN $topic IS NOT NULL AND NOT $topic IN s.topics_discussed THEN s.topics_discussed + [$topic] ELSE s.topics_discussed END RETURN s"""
        tx.run(query, session_id=session_id, intent=intent, topic=topic)
    
    def add_feedback(self, message_id: str, feedback: str):
        try:
            with self.driver.session() as session:
                session.execute_write(lambda tx: tx.run("""MATCH (m:Message {message_id: $message_id}) SET m.feedback = $feedback, m.feedback_timestamp = datetime() RETURN m""", message_id=message_id, feedback=feedback))
            logger.info(f"Feedback added for message {message_id}: {feedback}")
        except Exception as e:
            logger.error(f"Failed to add feedback: {e}")


    def get_analytics(self) -> Dict:
        try:
            with self.driver.session() as session:
                result = session.execute_read(self._fetch_analytics)
            return result
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {}
    
    @staticmethod
    def _fetch_analytics(tx) -> Dict:
        query = """
        MATCH (s:Session)-[:HAS_MESSAGE]->(m:Message)
        WITH s, collect(m) as messages
        RETURN 
            count(DISTINCT s) as total_sessions,
            sum(size(messages)) as total_messages,
            avg(toFloat(size(messages))) as avg_messages_per_session,
            [msg IN messages WHERE msg.intent IS NOT NULL | msg.intent] as all_intents,
            size([msg IN messages WHERE msg.feedback = 'positive']) as positive_feedback_count,
            size([msg IN messages WHERE msg.feedback = 'negative']) as negative_feedback_count
        """
        result = tx.run(query)
        data = result.single()
        
        if not data:
            return {
                'total_sessions': 0,
                'total_messages': 0,
                'avg_messages_per_session': 0,
                'intent_distribution': {},
                'positive_feedback_count': 0,
                'negative_feedback_count': 0
            }
        
        # Process intent counts
        intent_counts = {}
        for intent in data['all_intents']:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
        
        return {
            'total_sessions': data['total_sessions'],
            'total_messages': data['total_messages'],
            'avg_messages_per_session': round(data['avg_messages_per_session'], 2) if data['avg_messages_per_session'] else 0,
            'intent_distribution': intent_counts,
            'positive_feedback_count': data['positive_feedback_count'],
            'negative_feedback_count': data['negative_feedback_count']
        }

    def close(self):
        try:
            self.driver.close()
            logger.info("Neo4j connection closed")
        except Exception as e:
            logger.error(f"Error closing Neo4j connection: {e}")

# ==================== ENHANCED INTENT CLASSIFIER ====================
class EnhancedIntentClassifier:
    def __init__(self):
        self.confidence_threshold = Config.CONFIDENCE_THRESHOLD
        self.entity_patterns = {'order_number': r'(?:order\s+|#|number\s+)(\d{4,})', 'product_name': r'\b(laptop|phone|tablet|headphones|keyboard|mouse|monitor|charger|camera|printer)\b', 'amount': r'\$(\d+(?:\.\d{2})?)', 'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'date': r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b'}
        logger.info("EnhancedIntentClassifier initialized")
    
    def classify_intent(self, text: str) -> Dict[str, Any]:
        text_lower = text.lower()
        entities = self._extract_entities(text)
        intent_keywords = {'order_status': ['order', 'status', 'track', 'where', 'deliver', 'shipped', 'tracking'], 'product_info': ['product', 'price', 'specs', 'available', 'feature', 'cost', 'sell', 'buy'], 'return_refund': ['return', 'refund', 'exchange', 'back', 'money', 'cancel'], 'troubleshooting': ['broken', 'not work', 'issue', 'problem', 'error', 'help', 'fix', 'repair'], 'shipping': ['shipping', 'delivery', 'address', 'destination', 'transport', 'ship']}
        intent_scores = {}
        for intent, keywords in intent_keywords.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                intent_scores[intent] = score
        if intent_scores:
            best_intent = max(intent_scores, key=intent_scores.get)
            confidence = min(0.85 + (intent_scores[best_intent] * 0.05), 0.95)
            return {'intent': best_intent, 'confidence': confidence, 'entities': entities, 'text': text, 'source': 'keyword_match'}
        return {'intent': 'general_inquiry', 'confidence': 0.6, 'entities': entities, 'text': text, 'source': 'fallback'}
    
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        entities = []
        text_lower = text.lower()
        for entity_type, pattern in self.entity_patterns.items():
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                entities.append({'entity': entity_type, 'value': match.group(1) if match.groups() else match.group(0), 'start': match.start(), 'end': match.end(), 'confidence': 0.9})
        return entities

# See next artifact for ResponseGenerator and remaining code...

# CONTINUATION OF app.py - Add this after the EnhancedIntentClassifier

import random

# ==================== ENHANCED RESPONSE GENERATOR ====================
class EnhancedResponseGenerator:
    def __init__(self):
        self.intent_responses = {
            'order_status': {
                'first_ask': ["I'd be happy to help you track your order! Could you please provide your order number?", "Let me help you check the status of your order. What's your order number?"],
                'with_order': ["Thank you! I found order #{order}. It's currently in transit and should arrive within 3-5 business days.", "Great! Order #{order} has been shipped and is on its way to you. Expected delivery: 3-5 business days.", "Order #{order} is out for delivery! You should receive it today or tomorrow."],
                'followup': ["Your order is being processed and will ship within 24 hours. You'll receive tracking information via email.", "The tracking shows your order is currently at the local distribution center. It should be delivered soon!"],
                'topic_shift': "I see you're asking about order status now. "
            },
            'product_info': {
                'first_ask': ["I'd be happy to help! Which product would you like to learn more about?", "What product interests you? I can give you all the details."],
                'with_product': ["The {product} is a popular choice! It's priced at $299 and currently in stock. Would you like to know more about its features?", "We have the {product} available for $299. It comes with a 1-year warranty and free shipping. Interested?"],
                'followup': ["That product is in stock and ready to ship! Is there anything specific you'd like to know about it?", "We have several options available. Would you like pricing information or details about features?"],
                'topic_shift': "Now let me help you with product information. "
            },
            'return_refund': {
                'first_ask': ["I'm sorry you'd like to return something. I can definitely help with that. What's your order number?", "I can help process a return for you. Could you provide your order number?"],
                'with_order': ["Thank you for order #{order}. You're within our 30-day return window. I'll send you a return label via email.", "I can process the return for order #{order}. You'll receive a prepaid return label within 24 hours."],
                'followup': ["Your return request is approved. Once we receive the item back, your refund will be processed within 5-7 business days.", "After you ship the item back using the return label, you'll see the refund in your account within a week."],
                'topic_shift': "I understand you want to process a return. "
            },
            'troubleshooting': {
                'first_ask': ["I'm sorry you're experiencing an issue. What exactly is happening?", "I'd like to help fix this. Can you describe what's going wrong?"],
                'with_product': ["Let's troubleshoot your {product}. First, have you tried restarting the device?", "For {product} issues, let's try a few things: 1) Check the power connection, 2) Restart the device, 3) Update firmware if needed."],
                'followup': ["I understand. Let's try clearing your browser cache and restarting your device. That often resolves the issue.", "This might be a technical issue on our end. Let me escalate this to our support team. You'll hear back within 24 hours."],
                'topic_shift': "Now let's troubleshoot your issue. "
            },
            'shipping': {
                'first_ask': ["I can help with shipping questions! What would you like to know?", "Do you have a question about shipping? I'm here to help."],
                'followup': ["We offer standard shipping (5-7 days, free on orders over $50) and express shipping (2-3 days, $15). Which works best for you?", "We typically ship within 1-2 business days. Standard delivery is 5-7 days, or you can choose express for 2-3 days.", "We offer free shipping on orders over $50! Standard shipping is 5-7 business days. Would you like express shipping instead?"],
                'topic_shift': "Let me help with your shipping question. "
            },
            'general_inquiry': {
                'first_ask': ["Hello! How can I assist you today?", "Welcome! What can I help you with?"],
                'followup': ["I understand. Let me help you with that.", "That's a great question. Here's what I can tell you...", "Thanks for asking! Is there anything else I can help you with?"]
            }
        }
        self.stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'my', 'i', 'you', 'me', 'it', 'of', 'to', 'in', 'on', 'for', 'with', 'at', 'by', 'from'}
    
    def generate_response(self, user_input: str, context_history: List[Dict] = None, intent: str = None, session_metadata: Dict = None, entities: List[Dict] = None) -> str:
        if not intent:
            intent = 'general_inquiry'
        response_pool = self.intent_responses.get(intent, self.intent_responses['general_inquiry'])
        entity_dict = {}
        if entities:
            for entity in entities:
                entity_dict[entity['entity']] = entity['value']
        topic_shift = self._detect_topic_shift(intent, session_metadata)
        topic_shift_prefix = response_pool.get('topic_shift', '') if topic_shift else ''
        is_followup = self._is_followup_question(user_input, context_history, intent, session_metadata)
        if entity_dict.get('order_number') and 'with_order' in response_pool:
            response = random.choice(response_pool['with_order'])
        elif entity_dict.get('product_name') and 'with_product' in response_pool:
            response = random.choice(response_pool['with_product'])
        elif is_followup:
            response = random.choice(response_pool.get('followup', response_pool['first_ask']))
        else:
            response = random.choice(response_pool['first_ask'])
        response = self._substitute_entities(response, entity_dict)
        if topic_shift_prefix:
            response = topic_shift_prefix + response
        return response
    
    def _substitute_entities(self, response: str, entities: Dict[str, str]) -> str:
        for entity_type, value in entities.items():
            placeholder = f"{{{entity_type.split('_')[-1]}}}"
            response = response.replace(placeholder, str(value))
        return response
    
    def _extract_keywords(self, text: str) -> set:
        if isinstance(text, dict):
            text = text.get('text', '')
        words = text.lower().split()
        return {w for w in words if w not in self.stopwords and len(w) > 3}
    
    def _is_followup_question(self, user_input: str, context_history: List[Dict], current_intent: str, session_metadata: Dict) -> bool:
        if not context_history or len(context_history) == 0:
            return False
        current_keywords = self._extract_keywords(user_input)
        recent_messages = context_history[-3:] if len(context_history) >= 3 else context_history
        historical_keywords = set()
        for msg in recent_messages:
            historical_keywords.update(self._extract_keywords(msg.get('text', '')))
        if current_keywords and historical_keywords:
            overlap = len(current_keywords & historical_keywords)
            overlap_ratio = overlap / max(len(current_keywords), 1)
            if overlap_ratio > Config.TOPIC_OVERLAP_THRESHOLD:
                return True
        if session_metadata and session_metadata.get('user_intent'):
            previous_intent = session_metadata.get('user_intent')
            if previous_intent == current_intent:
                return True
            related_intents = {'order_status': ['shipping', 'return_refund'], 'product_info': ['return_refund'], 'return_refund': ['order_status', 'shipping']}
            if previous_intent in related_intents:
                if current_intent in related_intents[previous_intent]:
                    return True
        if len(context_history) >= 2:
            return True
        return False
    
    def _detect_topic_shift(self, current_intent: str, session_metadata: Dict) -> bool:
        if not session_metadata:
            return False
        previous_intent = session_metadata.get('user_intent')
        if not previous_intent or previous_intent == current_intent:
            return False
        related_groups = [{'order_status', 'shipping', 'return_refund'}, {'product_info', 'return_refund'}]
        current_group = None
        previous_group = None
        for group in related_groups:
            if current_intent in group:
                current_group = group
            if previous_intent in group:
                previous_group = group
        return current_group != previous_group

# ==================== UNIFIED DIALOGUE ENGINE ====================
class DialogueEngine:
    def __init__(self, neo4j_manager, intent_classifier, response_generator):
        self.neo4j = neo4j_manager
        self.classifier = intent_classifier
        self.response_generator = response_generator
        self.validator = MessageValidator()
        logger.info("DialogueEngine initialized")
    
    def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        is_valid, error_msg = self.validator.validate_message(user_message)
        if not is_valid:
            return {'status': 'error', 'error': error_msg}
        sanitized_message = self.validator.sanitize_message(user_message)
        try:
            intent_result = self.classifier.classify_intent(sanitized_message)
            intent = intent_result['intent']
            confidence = intent_result['confidence']
            entities = intent_result['entities']
            context_history = self.neo4j.get_conversation_context(session_id, num_messages=Config.CONTEXT_WINDOW_SIZE)
            session_metadata = self.neo4j.get_session_metadata(session_id)
            entity_dict = {e['entity']: e['value'] for e in entities}
            self.neo4j.add_message(session_id=session_id, sender='user', text=sanitized_message, intent=intent, entities=entity_dict, confidence=confidence)
            self.neo4j.update_session_intent(session_id, intent, topic=intent)
            bot_response = self.response_generator.generate_response(user_input=sanitized_message, context_history=context_history, intent=intent, session_metadata=session_metadata, entities=entities)
            self.neo4j.add_message(session_id=session_id, sender='bot', text=bot_response, intent=f"response_to_{intent}", confidence=0.95)
            return {'status': 'success', 'session_id': session_id, 'bot_response': bot_response, 'intent': intent, 'confidence': float(confidence), 'entities': entity_dict, 'is_followup': len(context_history) > 0, 'context_messages': len(context_history)}
        except Exception as e:
            logger.error(f"Message processing error: {e}", exc_info=True)
            return {'status': 'error', 'error': 'Failed to process message', 'session_id': session_id}

# ==================== INITIALIZE FLASK APP ====================
app = Flask(__name__)
CORS(app)

# Rate limiting
limiter = Limiter(app=app, key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])

swagger = Swagger(app, template={"swagger": "2.0", "info": {"title": "🤖 Conversational AI Chatbot", "version": "2.0.0"}})

logger.info("Initializing application components...")

try:
    neo4j_uri = os.getenv('NEO4J_URI')
    neo4j_user = os.getenv('NEO4J_USER')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    if not neo4j_uri or not neo4j_user or not neo4j_password:
        logger.critical("Missing Neo4j environment variables!")
        exit(1)
    neo4j_manager = Neo4jSessionManager(neo4j_uri, neo4j_user, neo4j_password)
    intent_classifier = EnhancedIntentClassifier()
    response_generator = EnhancedResponseGenerator()
    dialogue_engine = DialogueEngine(neo4j_manager, intent_classifier, response_generator)
    logger.info("✓ All components initialized successfully!")
except Exception as e:
    logger.critical(f"Failed to initialize: {e}")
    exit(1)

# ==================== API ENDPOINTS ====================

@app.route('/')
def index():
    return jsonify({'message': 'Conversational Chatbot API v2.0', 'docs': '/apidocs/'})


@app.route('/api/session/create', methods=['POST'])
def create_session():
    try:
        # Use get_json with silent=True to handle empty/malformed JSON gracefully
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id')
        session_id = neo4j_manager.create_session(user_id)
        return jsonify({'session_id': session_id, 'status': 'created', 'timestamp': datetime.now().isoformat()}), 201
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/message/send', methods=['POST'])
@limiter.limit("30 per minute")
def send_message():
    try:
        data = request.json
        session_id = data.get('session_id')
        user_message = data.get('message', '').strip()
        if not user_message:
            return jsonify({'error': 'Empty message'}), 400
        if not session_id:
            session_id = neo4j_manager.create_session()
        result = dialogue_engine.process_message(session_id, user_message)
        if result.get('status') == 'error':
            return jsonify(result), 400
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Message processing error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/history/<session_id>', methods=['GET'])
def get_history(session_id):
    try:
        limit = request.args.get('limit', 50, type=int)
        history = neo4j_manager.get_conversation_context(session_id, limit)
        return jsonify({'session_id': session_id, 'messages': history, 'count': len(history)}), 200
    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/session/context/<session_id>', methods=['GET'])
def get_context(session_id):
    try:
        metadata = neo4j_manager.get_session_metadata(session_id)
        if not metadata:
            return jsonify({'error': 'Session not found'}), 404
        return jsonify({'session_id': session_id, 'metadata': metadata, 'timestamp': datetime.now().isoformat()}), 200
    except Exception as e:
        logger.error(f"Context retrieval error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/feedback', methods=['POST'])
def submit_feedback():
    try:
        data = request.json
        message_id = data.get('message_id')
        feedback = data.get('feedback')
        if feedback not in ['positive', 'negative']:
            return jsonify({'error': 'Invalid feedback'}), 400
        neo4j_manager.add_feedback(message_id, feedback)
        return jsonify({'status': 'success', 'message_id': message_id, 'feedback': feedback}), 200
    except Exception as e:
        logger.error(f"Feedback error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/summary', methods=['GET'])
def get_analytics():
    try:
        analytics = neo4j_manager.get_analytics()
        return jsonify(analytics), 200
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/conversation/export/<session_id>', methods=['GET'])
def export_conversation(session_id):
    try:
        history = neo4j_manager.get_conversation_context(session_id, limit=1000)
        export_data = {'session_id': session_id, 'exported_at': datetime.now().isoformat(), 'messages': history}
        return jsonify(export_data), 200, {'Content-Disposition': f'attachment; filename=conversation_{session_id}.json'}
    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        return jsonify({'status': 'healthy', 'version': '2.0', 'components': {'neo4j': 'connected', 'classifier': 'loaded', 'generator': 'loaded'}, 'timestamp': datetime.now().isoformat()}), 200
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    try:
        logger.info("Starting Enhanced Flask application...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("Shutting down application...")
        neo4j_manager.close()
    except Exception as e:
        logger.critical(f"Application error: {e}")
        neo4j_manager.close()
        exit(1)
        