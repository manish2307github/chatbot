import React, { useState, useEffect, useRef } from "react";

const API_BASE = "http://localhost:5000/api";

export default function ChatApp() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState("");
  const chatEndRef = useRef(null);
  const inputRef = useRef(null);

  // Initialize session on mount
  useEffect(() => {
    createNewSession();
  }, []);

  // Auto-scroll to latest message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const createNewSession = async () => {
    try {
        const response = await fetch(`${API_BASE}/session/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}) // Always send empty object instead of nothing
      });
      
      if (!response.ok) throw new Error("Failed to create session");
      
      const data = await response.json();
      setSessionId(data.session_id);
      setMessages([]);
      setError("");
      inputRef.current?.focus();
    } catch (err) {
      setError("Backend not running. Start with: python app.py");
      console.error(err);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    
    if (!input.trim() || !sessionId) return;
    
    const messageText = input;
    const userMsg = {
      id: Date.now(),
      sender: "user",
      text: messageText,
      timestamp: new Date(),
    };
    
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/message/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: messageText,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to get response");
      }

      const botMsg = {
        id: Date.now() + 1,
        sender: "bot",
        text: data.bot_response,
        timestamp: new Date(),
        intent: data.intent,
        confidence: data.confidence,
      };

      setMessages((prev) => [...prev, botMsg]);
    } catch (err) {
      setError(err.message);
      const errorMsg = {
        id: Date.now() + 1,
        sender: "bot",
        text: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date(),
        isError: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto; }
        
        .chat-container {
          display: flex;
          flex-direction: column;
          height: 100vh;
          max-width: 900px;
          margin: 0 auto;
          background: #f5f5f5;
          box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        
        .chat-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 20px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .chat-header h1 {
          margin: 0;
          font-size: 24px;
          font-weight: 600;
        }
        
        .session-info {
          display: flex;
          gap: 15px;
          align-items: center;
          font-size: 12px;
        }
        
        .btn-new-session {
          padding: 8px 16px;
          background: rgba(255,255,255,0.2);
          color: white;
          border: 1px solid rgba(255,255,255,0.3);
          border-radius: 4px;
          cursor: pointer;
          font-size: 12px;
          transition: background 0.3s;
        }
        
        .btn-new-session:hover {
          background: rgba(255,255,255,0.3);
        }
        
        .error-banner {
          background: #ffebee;
          color: #c62828;
          padding: 12px;
          border-bottom: 2px solid #c62828;
          font-size: 13px;
          text-align: center;
        }
        
        .chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          background: white;
        }
        
        .welcome-message {
          text-align: center;
          color: #999;
          margin: auto;
          padding: 40px 20px;
        }
        
        .welcome-message p:first-child {
          font-size: 18px;
          font-weight: 500;
          margin-bottom: 10px;
        }
        
        .message {
          display: flex;
          animation: slideIn 0.3s ease-out;
        }
        
        .message-user {
          justify-content: flex-end;
        }
        
        .message-bot {
          justify-content: flex-start;
        }
        
        .message-content {
          max-width: 70%;
          padding: 12px 16px;
          border-radius: 12px;
          word-wrap: break-word;
        }
        
        .message-user .message-content {
          background: #667eea;
          color: white;
          border-bottom-right-radius: 4px;
        }
        
        .message-bot .message-content {
          background: #f0f0f0;
          color: #333;
          border-bottom-left-radius: 4px;
        }
        
        .message-error .message-content {
          background: #ffebee;
          color: #c62828;
        }
        
        .message-text {
          margin: 0 0 8px 0;
        }
        
        .message-time {
          display: block;
          font-size: 11px;
          opacity: 0.7;
          margin-top: 6px;
        }
        
        .message-intent {
          display: block;
          font-size: 10px;
          opacity: 0.6;
          margin-top: 4px;
        }
        
        .typing-indicator {
          display: flex;
          gap: 4px;
          padding: 12px 16px;
          background: #f0f0f0;
          border-radius: 12px;
        }
        
        .typing-indicator span {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #999;
          animation: bounce 1.4s infinite;
        }
        
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes bounce {
          0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
          30% { opacity: 1; transform: translateY(-10px); }
        }
        
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        .chat-input-area {
          display: flex;
          gap: 10px;
          padding: 15px;
          background: white;
          border-top: 1px solid #e0e0e0;
        }
        
        .chat-input {
          flex: 1;
          padding: 12px 16px;
          border: 1px solid #e0e0e0;
          border-radius: 24px;
          font-size: 14px;
          outline: none;
          transition: border-color 0.3s;
        }
        
        .chat-input:focus {
          border-color: #667eea;
        }
        
        .chat-input:disabled {
          background: #f5f5f5;
          opacity: 0.6;
          cursor: not-allowed;
        }
        
        .btn-send {
          padding: 12px 24px;
          background: #667eea;
          color: white;
          border: none;
          border-radius: 24px;
          cursor: pointer;
          font-weight: 600;
          transition: background 0.3s, transform 0.1s;
          white-space: nowrap;
        }
        
        .btn-send:hover:not(:disabled) {
          background: #764ba2;
          transform: translateY(-2px);
        }
        
        .btn-send:disabled {
          background: #ccc;
          cursor: not-allowed;
        }
        
        .chat-footer {
          padding: 10px;
          background: #f9f9f9;
          border-top: 1px solid #e0e0e0;
          text-align: center;
          color: #999;
          font-size: 11px;
        }
      `}</style>

      <div className="chat-container">
        {/* Header */}
        <div className="chat-header">
          <h1>🤖 Customer Support Chatbot</h1>
          <div className="session-info">
            <small>Session: {sessionId?.substring(0, 12)}...</small>
            <button onClick={createNewSession} className="btn-new-session">
              New Chat
            </button>
          </div>
        </div>

        {/* Error */}
        {error && <div className="error-banner">{error}</div>}

        {/* Messages */}
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="welcome-message">
              <p>Welcome! 👋</p>
              <p>How can I assist you today?</p>
              <small>Try: "What's my order status?" or "I need help with a return"</small>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`message message-${msg.sender} ${msg.isError ? "message-error" : ""}`}
            >
              <div className="message-content">
                <p className="message-text">{msg.text}</p>
                <small className="message-time">
                  {msg.timestamp.toLocaleTimeString()}
                </small>
                {msg.intent && (
                  <small className="message-intent">
                    Intent: {msg.intent} ({(msg.confidence * 100).toFixed(0)}%)
                  </small>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="message message-bot">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}

          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div className="chat-input-area">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage(e)}
            placeholder="Type your message..."
            disabled={loading || !sessionId}
            maxLength={1000}
            className="chat-input"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !sessionId || !input.trim()}
            className="btn-send"
          >
            {loading ? "⏳ Sending..." : "📤 Send"}
          </button>
        </div>

        {/* Footer */}
        <div className="chat-footer">
          <small>
            Chat ID: {sessionId?.substring(0, 12)}... | Messages: {messages.length}
          </small>
        </div>
      </div>
    </>
  );
}