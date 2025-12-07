// Create unique constraints
CREATE CONSTRAINT session_id_unique IF NOT EXISTS 
FOR (s:Session) REQUIRE s.session_id IS UNIQUE;

CREATE CONSTRAINT message_id_unique IF NOT EXISTS 
FOR (m:Message) REQUIRE m.message_id IS UNIQUE;

// Create indexes for faster queries
CREATE INDEX session_created IF NOT EXISTS 
FOR (s:Session) ON (s.created_at);

CREATE INDEX message_timestamp IF NOT EXISTS 
FOR (m:Message) ON (m.timestamp);

CREATE INDEX message_sender IF NOT EXISTS 
FOR (m:Message) ON (m.sender);

CREATE INDEX message_intent IF NOT EXISTS 
FOR (m:Message) ON (m.intent);

// Create initial indexes for performance
CREATE INDEX session_status IF NOT EXISTS 
FOR (s:Session) ON (s.status);

// Create sample session for testing
CREATE (s:Session {
    session_id: 'test_session_001',
    created_at: datetime(),
    last_interaction: datetime(),
    interaction_count: 0,
    status: 'active'
});

// Verify setup
MATCH (n) RETURN COUNT(n) as total_nodes;