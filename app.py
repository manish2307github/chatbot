from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json
import uuid
from typing import List, Dict, Any, Optional, Tuple
import os
import logging
import re
from flask_swagger_ui import get_swaggerui_blueprint
from flasgger import Swagger
from dotenv import load_dotenv

# NLP and ML imports
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Neo4j imports
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
class Config:
    """Application configuration"""
    MAX_MESSAGE_LENGTH = 1000
    MIN_MESSAGE_LENGTH = 1
    CONFIDENCE_THRESHOLD = 0.5
    CONTEXT_WINDOW_SIZE = 6
    MAX_RESPONSE_LENGTH = 200
    SESSION_TIMEOUT_HOURS = 24


# ==================== INPUT VALIDATION ====================
class MessageValidator:
    """Validate and sanitize user input"""
    
    @staticmethod
    def validate_message(text: str) -> Tuple[bool, str]:
        """Validate user input with security checks"""
        if not text or not text.strip():
            return False, "Message cannot be empty"
        
        if len(text) > Config.MAX_MESSAGE_LENGTH:
            return False, f"Message exceeds {Config.MAX_MESSAGE_LENGTH} characters"
        
        if len(text) < Config.MIN_MESSAGE_LENGTH:
            return False, "Message too short"
        
        # Check for injection patterns
        if re.search(r'<script|javascript:|onerror=', text, re.IGNORECASE):
            return False, "Invalid message format"
        
        return True, ""
    
    @staticmethod
    def sanitize_message(text: str) -> str:
        """Remove potentially harmful characters"""
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        return text


# ==================== NEO4J SESSION MANAGER ====================
class Neo4jSessionManager:
    """Manages conversation sessions using Neo4j graph database"""
    
    def __init__(self, uri: str, user: str, password: str, max_connections: int = 50):
        try:
            self.driver = GraphDatabase.driver(
                uri,
                auth=(user, password),
                max_connection_pool_size=max_connections,
                connection_acquisition_timeout=30.0
            )
            
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j at {uri}")
            self._create_constraints()
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def _create_constraints(self):
        """Create unique constraints for data integrity"""
        try:
            with self.driver.session() as session:
                session.execute_write(
                    lambda tx: tx.run(
                        "CREATE CONSTRAINT session_id_unique IF NOT EXISTS FOR (s:Session) REQUIRE s.session_id IS UNIQUE"
                    )
                )
                session.execute_write(
                    lambda tx: tx.run(
                        "CREATE CONSTRAINT message_id_unique IF NOT EXISTS FOR (m:Message) REQUIRE m.message_id IS UNIQUE"
                    )
                )
            logger.info("Database constraints created successfully")
        except Exception as e:
            logger.warning(f"Constraint creation warning: {e}")
    
    def create_session(self) -> str:
        """Create new conversation session node in Neo4j"""
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        try:
            with self.driver.session() as session:
                session.execute_write(self._create_session_node, session_id)
            logger.info(f"Created session: {session_id}")
            return session_id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    @staticmethod
    def _create_session_node(tx, session_id: str):
        """Create session node with metadata"""
        query = """
        CREATE (s:Session {
            session_id: $session_id,
            created_at: datetime(),
            last_interaction: datetime(),
            interaction_count: 0,
            user_intent: null,
            topic: null,
            status: 'active'
        })
        RETURN s
        """
        tx.run(query, session_id=session_id)
    
    def add_message(self, session_id: str, sender: str, text: str,
                   intent: str = None, entities: Dict = None) -> Dict:
        """Add message node and link to session"""
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        try:
            with self.driver.session() as session:
                result = session.execute_write(
                    self._add_message_node,
                    session_id,
                    message_id,
                    sender,
                    text,
                    intent,
                    entities
                )
            return result
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise
    
    @staticmethod
    def _add_message_node(tx, session_id: str, message_id: str,
                         sender: str, text: str, intent: str = None,
                         entities: Dict = None) -> Dict:
        """Create message node and establish relationships"""
        query = """
        MATCH (s:Session {session_id: $session_id})
        CREATE (m:Message {
            message_id: $message_id,
            sender: $sender,
            text: $text,
            intent: $intent,
            entities: $entities,
            timestamp: datetime(),
            token_count: $token_count
        })
        CREATE (s)-[:HAS_MESSAGE]->(m)
        SET s.last_interaction = datetime(),
            s.interaction_count = s.interaction_count + 1
        RETURN m
        """
        
        token_count = len(text.split())
        tx.run(
            query,
            session_id=session_id,
            message_id=message_id,
            sender=sender,
            text=text,
            intent=intent,
            entities=json.dumps(entities) if entities else None,
            token_count=token_count
        )
        return {"message_id": message_id, "status": "added"}
    
    def get_conversation_context(self, session_id: str, num_messages: int = 5) -> List[Dict]:
        """Retrieve recent messages for context window"""
        try:
            with self.driver.session() as session:
                result = session.execute_read(
                    self._fetch_recent_messages,
                    session_id,
                    num_messages
                )
            return result
        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return []
    
    @staticmethod
    def _fetch_recent_messages(tx, session_id: str, num_messages: int) -> List[Dict]:
        """Fetch recent messages ordered by timestamp"""
        query = """
        MATCH (s:Session {session_id: $session_id})-[:HAS_MESSAGE]->(m:Message)
        RETURN m
        ORDER BY m.timestamp DESC
        LIMIT $limit
        """
        
        result = tx.run(query, session_id=session_id, limit=num_messages)
        messages = []
        
        for record in result:
            msg = record["m"]
            try:
                entities = json.loads(msg.get('entities', '{}') or '{}')
            except (json.JSONDecodeError, TypeError):
                entities = {}
            
            message_data = {
                'message_id': msg['message_id'],
                'sender': msg['sender'],
                'text': msg['text'],
                'intent': msg.get('intent'),
                'entities': entities,
                'timestamp': str(msg['timestamp'])
            }
            messages.append(message_data)
        
        return list(reversed(messages))
    
    def get_session_metadata(self, session_id: str) -> Optional[Dict]:
        """Retrieve session metadata and context"""
        try:
            with self.driver.session() as session:
                result = session.execute_read(
                    self._fetch_session_metadata,
                    session_id
                )
            return result
        except Exception as e:
            logger.error(f"Failed to get session metadata: {e}")
            return None
    
    @staticmethod
    def _fetch_session_metadata(tx, session_id: str) -> Optional[Dict]:
        """Fetch session metadata"""
        query = """
        MATCH (s:Session {session_id: $session_id})
        RETURN s
        """
        
        result = tx.run(query, session_id=session_id)
        record = result.single()
        
        if not record:
            return None
        
        session_node = record["s"]
        return {
            'session_id': session_node['session_id'],
            'created_at': str(session_node['created_at']),
            'last_interaction': str(session_node['last_interaction']),
            'interaction_count': session_node['interaction_count'],
            'user_intent': session_node.get('user_intent'),
            'topic': session_node.get('topic'),
            'status': session_node.get('status', 'active')
        }
    
    def update_session_intent(self, session_id: str, intent: str, topic: str = None):
        """Update session with detected intent and topic"""
        try:
            with self.driver.session() as session:
                session.execute_write(
                    self._update_intent,
                    session_id,
                    intent,
                    topic
                )
        except Exception as e:
            logger.error(f"Failed to update session intent: {e}")
    
    @staticmethod
    def _update_intent(tx, session_id: str, intent: str, topic: str = None):
        """Update session intent and topic"""
        query = """
        MATCH (s:Session {session_id: $session_id})
        SET s.user_intent = $intent,
            s.topic = coalesce($topic, s.topic)
        RETURN s
        """
        tx.run(query, session_id=session_id, intent=intent, topic=topic)
    
    def close(self):
        """Close database connection"""
        try:
            self.driver.close()
            logger.info("Neo4j connection closed")
        except Exception as e:
            logger.error(f"Error closing Neo4j connection: {e}")


# ==================== RASA INTENT CLASSIFIER ====================
class RasaIntentClassifier:
    """Intent classification using keyword-based fallback"""
    
    def __init__(self):
        self.confidence_threshold = Config.CONFIDENCE_THRESHOLD
        logger.info("RasaIntentClassifier initialized")
    
    def classify_intent(self, text: str) -> Dict[str, Any]:
        """Classify user intent using keyword matching"""
        return self._fallback_classify(text)
    
    def _fallback_classify(self, text: str) -> Dict[str, Any]:
        """Keyword-based classification"""
        intent_keywords = {
            'order_status': ['order', 'status', 'track', 'where', 'deliver', 'shipped'],
            'product_info': ['product', 'price', 'specs', 'available', 'feature', 'cost'],
            'return_refund': ['return', 'refund', 'exchange', 'back', 'money'],
            'troubleshooting': ['broken', 'not work', 'issue', 'problem', 'error', 'help'],
            'shipping': ['shipping', 'delivery', 'address', 'destination', 'transport']
        }
        
        text_lower = text.lower()
        
        for intent, keywords in intent_keywords.items():
            if any(kw in text_lower for kw in keywords):
                return {
                    'intent': intent,
                    'confidence': 0.85,
                    'entities': [],
                    'text': text,
                    'source': 'keyword_match'
                }
        
        return {
            'intent': 'general_inquiry',
            'confidence': 0.6,
            'entities': [],
            'text': text,
            'source': 'fallback'
        }


# ==================== RESPONSE GENERATOR ====================
class FallbackResponseGenerator:
    """Simple fallback response generator"""
    
    def generate_response(self, user_input: str, context_history: List[str] = None,
                        max_length: int = 100, temperature: float = 0.7) -> str:
        """Generate response based on intent"""
        intent_responses = {
            'order_status': "Thank you for asking about your order. Please provide your order number and I'll help you track it.",
            'product_info': "I'd be happy to help with product information. What product are you interested in?",
            'return_refund': "We're here to assist with returns and refunds. Please share your order number.",
            'troubleshooting': "I'm sorry you're experiencing issues. Can you describe the problem in more detail?",
            'shipping': "Thank you for your shipping inquiry. How can I assist you today?",
            'general_inquiry': "Thank you for reaching out! How can I help you today?"
        }
        
        if context_history and len(context_history) > 0:
            last_msg = context_history[-1].lower()
            for intent, response in intent_responses.items():
                if any(keyword in last_msg for keyword in intent.split('_')):
                    return response
        
        return intent_responses.get('general_inquiry', "Thank you for your message!")
    
class ContextAwareResponseGenerator:
    """Response generator that uses conversation context for contextual responses"""
    
    def __init__(self):
        # Intent-specific response templates
        self.intent_responses = {
            'order_status': {
                'first_ask': [
                    "I'd be happy to help you track your order! Could you please provide your order number?",
                    "Let me help you check the status of your order. What's your order number?"
                ],
                'followup': [
                    "Thank you! I found your order. It's currently in transit and should arrive within 3-5 business days.",
                    "Got it! Your order has been shipped and is on its way to you. You should receive it soon.",
                    "Your order is being prepared for shipment. We'll send you a tracking number as soon as it ships!"
                ],
                'with_order_number': [
                    "Order {order} is currently in transit. Expected delivery is within 3-5 business days.",
                    "I found order {order}. It's been shipped and you should see it arrive soon.",
                ]
            },
            'product_info': {
                'first_ask': [
                    "I'd be happy to help! Which product would you like to learn more about?",
                    "What product interests you? I can give you all the details."
                ],
                'followup': [
                    "That's a popular choice! We have great reviews on that product. Would you like to know more about pricing or availability?",
                    "That product is in stock and ready to ship! Is there anything specific you'd like to know about it?",
                    "We have several options available. Would you like pricing information or details about features?"
                ]
            },
            'return_refund': {
                'first_ask': [
                    "I'm sorry you'd like to return something. I can definitely help with that. What's your order number?",
                    "I can help process a return for you. Could you provide your order number?"
                ],
                'followup': [
                    "Thank you for that information. You're within our 30-day return window, so I can help process this for you.",
                    "I can process that return for you. Here's what happens next: we'll send you a return label, you pack the item and drop it off at any shipping location.",
                    "Your return request is approved. You'll receive a return label via email. Once we receive the item back, your refund will be processed within 5-7 business days."
                ]
            },
            'troubleshooting': {
                'first_ask': [
                    "I'm sorry you're experiencing an issue. What exactly is happening?",
                    "I'd like to help fix this. Can you describe what's going wrong?"
                ],
                'followup': [
                    "I understand. Let's troubleshoot this together. First, have you tried refreshing the page or restarting your device?",
                    "That sounds frustrating. A few things to try: clear your browser cache, try a different browser, or contact our support team for personalized help.",
                    "This might be a technical issue on our end. Let me escalate this to our support team. You'll hear back within 24 hours with a solution."
                ]
            },
            'shipping': {
                'first_ask': [
                    "I can help with shipping questions! What would you like to know?",
                    "Do you have a question about shipping? I'm here to help."
                ],
                'followup': [
                    "We offer standard shipping (5-7 days) and express shipping (2-3 days). Which option works best for you?",
                    "We typically ship within 1-2 business days. Standard delivery is 5-7 days, or you can choose express for 2-3 days.",
                    "We offer free shipping on orders over $50! Standard shipping is 5-7 business days. Would you like express shipping instead?"
                ]
            },
            'general_inquiry': {
                'first_ask': [
                    "Hello! How can I assist you today?",
                    "Welcome! What can I help you with?"
                ],
                'followup': [
                    "I understand. Let me help you with that.",
                    "That's a great question. Here's what I can tell you...",
                    "Thanks for asking! Is there anything else I can help you with?"
                ]
            }
        }
    def generate_response(self, user_input: str, context_history: List[str] = None,
                        intent: str = None, session_metadata: Dict = None) -> str:
        """
        Generate realistic, context-aware response
        """
        import random
        
        if not intent:
            intent = 'general_inquiry'
        
        response_pool = self.intent_responses.get(intent, self.intent_responses['general_inquiry'])
        
        # Check if this is a follow-up
        is_followup = self._is_followup_question(context_history, intent, session_metadata)
        
        # Check if user provided order number
        order_number = self._extract_order_number(user_input, context_history)
        
        if is_followup and order_number and 'with_order_number' in response_pool:
            # Use order-specific response
            response = random.choice(response_pool['with_order_number'])
            response = response.replace('{order}', order_number)
        elif is_followup:
            response = random.choice(response_pool.get('followup', response_pool['first_ask']))
        else:
            response = random.choice(response_pool['first_ask'])
        
        return response
    def _is_followup_question(self, context_history: List[str], 
                             current_intent: str, 
                             session_metadata: Dict) -> bool:
        """Check if this is a follow-up question"""
        
        if not context_history or len(context_history) == 0:
            return False
        
        if session_metadata and session_metadata.get('user_intent'):
            previous_intent = session_metadata.get('user_intent')
            
            if previous_intent == current_intent:
                return True
            
            related_intents = {
                'order_status': ['shipping', 'return_refund'],
                'product_info': ['return_refund'],
                'return_refund': ['order_status', 'shipping']
            }
            
            if previous_intent in related_intents:
                if current_intent in related_intents[previous_intent]:
                    return True
        
        if len(context_history) >= 2:
            return True
        
        return False
    def _select_initial_response(self, response_pool: Dict) -> str:
        """Select response for initial question"""
        import random
        
        responses = response_pool.get('first_ask', 
                                     ['Thank you for your question. How can I help?'])
        return random.choice(responses)
    
    def _select_followup_response(self, response_pool: Dict, 
                                 user_input: str, 
                                 context_history: List[str]) -> str:
        """Select context-aware response for follow-up question"""
        import random
        
        responses = response_pool.get('followup', 
                                     ['I understand. Let me help you with that.'])
        
        selected = random.choice(responses)
        
        # Try to extract order number from user input or context
        order_number = self._extract_order_number(user_input, context_history)
        if order_number and '{order}' in selected:
            selected = selected.replace('{order}', order_number)
        
        return selected
    
    def _extract_order_number(self, user_input: str, context_history: List[str]) -> str:
        """Extract order number from messages"""
        import re
        
        match = re.search(r'#?(\d{4,})', user_input)
        if match:
            return match.group(1)
        
        if context_history:
            for msg in context_history:
                match = re.search(r'#?(\d{4,})', msg)
                if match:
                    return match.group(1)
        
        return None
# ==================== UNIFIED DIALOGUE ENGINE ====================
class DialogueEngine:
    """Unified dialogue engine with improved context awareness"""
    
    def __init__(self, neo4j_manager: Neo4jSessionManager,
                 rasa_classifier: RasaIntentClassifier,
                 response_generator: ContextAwareResponseGenerator):
        self.neo4j = neo4j_manager
        self.rasa = rasa_classifier
        self.response_generator = response_generator
        self.validator = MessageValidator()
        logger.info("DialogueEngine initialized")
    
    def process_message(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """Process user message through complete dialogue pipeline"""
        
        # Validate message
        is_valid, error_msg = self.validator.validate_message(user_message)
        if not is_valid:
            return {'status': 'error', 'error': error_msg}
        
        sanitized_message = self.validator.sanitize_message(user_message)
        
        try:
            # Step 1: Classify intent
            intent_result = self.rasa.classify_intent(sanitized_message)
            intent = intent_result['intent']
            confidence = intent_result['confidence']
            entities = intent_result['entities']
            
            # Step 2: Retrieve conversation context (IMPORTANT!)
            context_history = self.neo4j.get_conversation_context(
                session_id,
                num_messages=Config.CONTEXT_WINDOW_SIZE
            )
            
            # Step 3: Get session metadata for context awareness
            session_metadata = self.neo4j.get_session_metadata(session_id)
            
            # Step 4: Add user message to Neo4j
            self.neo4j.add_message(
                session_id=session_id,
                sender='user',
                text=sanitized_message,
                intent=intent,
                entities={e.get('entity', 'unknown'): e.get('value', '') for e in entities} if entities else {}
            )
            
            # Step 5: Update session metadata
            self.neo4j.update_session_intent(session_id, intent)
            
            # Step 6: Generate CONTEXT-AWARE response
            # Pass context history, intent, and session metadata
            bot_response = self.response_generator.generate_response(
                user_input=sanitized_message,
                context_history=[msg['text'] for msg in context_history],
                intent=intent,
                session_metadata=session_metadata
            )
            
            # Step 7: Add bot response to Neo4j
            self.neo4j.add_message(
                session_id=session_id,
                sender='bot',
                text=bot_response,
                intent=f"response_to_{intent}"
            )
            
            return {
                'status': 'success',
                'session_id': session_id,
                'bot_response': bot_response,
                'intent': intent,
                'confidence': float(confidence),
                'entities': {e.get('entity', 'unknown'): e.get('value', '') for e in entities} if entities else {},
                'is_followup': len(context_history) > 0,
                'context_messages': len(context_history)
            }
        
        except Exception as e:
            logger.error(f"Message processing error: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': 'Failed to process message',
                'session_id': session_id
            }
    
# ==================== INITIALIZE FLASK APP ====================
app = Flask(__name__)
@app.route('/')
def index():
    return jsonify({'message': 'Chatbot API Running', 'docs': '/api/docs'})

CORS(app)

# Initialize Swagger
swagger = Swagger(app, template={
    "swagger": "2.0",
    "info": {
        "title": "🤖 Conversational AI Chatbot API",
        "description": "Multi-turn dialogue system with Neo4j storage",
        "version": "1.0.0",
        "contact": {
            "name": "Support",
            "email": "support@chatbot.com"
        }
    },
    "basePath": "/api",
    "schemes": ["http", "https"]
})

# Initialize components
logger.info("Initializing application components...")

# Neo4j Connection
try:
    neo4j_uri = os.getenv('NEO4J_URI')
    neo4j_user = os.getenv('NEO4J_USER')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    if not neo4j_uri or not neo4j_user or not neo4j_password:
        logger.critical("Missing Neo4j environment variables!")
        logger.critical("Please create a .env file with NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        exit(1)
    
    logger.info(f"Connecting to Neo4j at {neo4j_uri}")
    neo4j_manager = Neo4jSessionManager(neo4j_uri, neo4j_user, neo4j_password)
    logger.info("✓ Neo4j manager initialized")
except Exception as e:
    logger.critical(f"Failed to initialize Neo4j: {e}")
    exit(1)

# Rasa Intent Classifier
try:
    rasa_classifier = RasaIntentClassifier()
    logger.info("✓ Rasa classifier initialized")
except Exception as e:
    logger.critical(f"Failed to initialize Rasa classifier: {e}")
    exit(1)

# Response Generator
try:
    response_generator = ContextAwareResponseGenerator()
    logger.info("✓ Context-aware response generator initialized")
except Exception as e:
    logger.critical(f"Failed to initialize response generator: {e}")
    exit(1)

# Unified Dialogue Engine
try:
    dialogue_engine = DialogueEngine(neo4j_manager, rasa_classifier, response_generator)
    logger.info("✓ Dialogue engine initialized")
except Exception as e:
    logger.critical(f"Failed to initialize dialogue engine: {e}")
    exit(1)

logger.info("All components initialized successfully!")


# ==================== API ENDPOINTS ====================
@app.route('/api/session/create', methods=['POST'])
def create_session():
    """
    Create a new conversation session
    ---
    tags:
      - Session
    responses:
      201:
        description: Session created successfully
        schema:
          properties:
            session_id:
              type: string
              example: "session_a1b2c3d4e5f6g7h8"
            status:
              type: string
              example: "created"
            timestamp:
              type: string
              example: "2025-01-15T10:30:00"
    """
    try:
        session_id = neo4j_manager.create_session()
        return jsonify({
            'session_id': session_id,
            'status': 'created',
            'timestamp': datetime.now().isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Session creation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/message/send', methods=['POST'])
def send_message():
    """
    Send a message and get AI response
    ---
    tags:
      - Messages
    parameters:
      - name: body
        in: body
        required: true
        schema:
          properties:
            session_id:
              type: string
              example: "session_a1b2c3d4e5f6g7h8"
            message:
              type: string
              example: "What is my order status?"
    responses:
      200:
        description: Response generated successfully
        schema:
          properties:
            status:
              type: string
              example: "success"
            bot_response:
              type: string
            intent:
              type: string
              example: "order_status"
            confidence:
              type: number
              example: 0.85
    """
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
    """
    Get conversation history for a session
    ---
    tags:
      - History
    parameters:
      - name: session_id
        in: path
        required: true
        type: string
      - name: limit
        in: query
        type: integer
        default: 50
    responses:
      200:
        description: Conversation history retrieved
        schema:
          properties:
            session_id:
              type: string
            messages:
              type: array
            count:
              type: integer
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        history = neo4j_manager.get_conversation_context(session_id, limit)
        
        return jsonify({
            'session_id': session_id,
            'messages': history,
            'count': len(history)
        }), 200
    
    except Exception as e:
        logger.error(f"History retrieval error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/context/<session_id>', methods=['GET'])
def get_context(session_id):
    """
    Get session context and metadata
    ---
    tags:
      - Session
    parameters:
      - name: session_id
        in: path
        required: true
        type: string
    responses:
      200:
        description: Session metadata retrieved
        schema:
          properties:
            session_id:
              type: string
            metadata:
              type: object
    """
    try:
        metadata = neo4j_manager.get_session_metadata(session_id)
        
        if not metadata:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({
            'session_id': session_id,
            'metadata': metadata,
            'timestamp': datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        logger.error(f"Context retrieval error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    ---
    tags:
      - Health
    responses:
      200:
        description: Service is healthy
        schema:
          properties:
            status:
              type: string
              example: "healthy"
            components:
              type: object
    """
    try:
        return jsonify({
            'status': 'healthy',
            'components': {
                'neo4j': 'connected',
                'classifier': 'loaded',
                'generator': 'loaded'
            },
            'timestamp': datetime.now().isoformat()
        }), 200
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
        logger.info("Starting Flask application...")
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("Shutting down application...")
        neo4j_manager.close()
    except Exception as e:
        logger.critical(f"Application error: {e}")
        neo4j_manager.close()
        exit(1)