import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from '../components/ChatMessage';
import { sendChatMessage } from '../services/api';

const EXAMPLE_PROMPTS = [
  {
    category: 'KYC & Due Diligence',
    title: 'Customer Onboarding without ID',
    scenario: true,
    prompt: 'Scenario: A branch manager onboarded a savings account customer without verifying official identity documents because the customer was introduced by a senior local politician. Is this compliant with RBI KYC guidelines?',
  },
  {
    category: 'KYC Requirements',
    title: 'Periodic KYC Updation',
    scenario: false,
    prompt: 'What are the RBI periodic updation frequencies for low-risk, medium-risk, and high-risk customers?',
  },
  {
    category: 'Customer Protection',
    title: 'Unauthorised Electronic Transaction',
    scenario: true,
    prompt: 'Scenario: A customer notified their bank 4 days after a third-party fraud debit occurred due to an account takeover. What is the customer liability under RBI rules?',
  },
  {
    category: 'Digital Lending',
    title: 'Digital Lending KFS & Recovery',
    scenario: false,
    prompt: 'What are the RBI requirements regarding Key Fact Statement (KFS) and recovery practices in digital lending?',
  },
  {
    category: 'Out of Scope',
    title: 'Corporate Income Tax Slab',
    scenario: false,
    prompt: 'What are the corporate income tax brackets and capital gains exemption rules for financial institutions under the Finance Act?',
  },
];

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [categoryFilter, setCategoryFilter] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (questionText = null) => {
    const q = (questionText || input).trim();
    if (!q || loading) return;

    setError(null);
    setInput('');

    const userMsgId = Date.now().toString();
    const newUserMsg = {
      id: userMsgId,
      role: 'user',
      content: q,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, newUserMsg]);
    setLoading(true);

    try {
      const response = await sendChatMessage(q, categoryFilter || null);
      const assistantMsg = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.answer,
        compliance_status: response.compliance_status,
        recommended_action: response.recommended_action,
        sources: response.sources || [],
        is_scenario: response.is_scenario,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err.message || 'An error occurred while querying the compliance system.');
      const errorMsg = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `Error: ${err.message || 'Failed to process request.'}`,
        is_error: true,
        sources: [],
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClearHistory = () => {
    if (window.confirm('Clear all conversation messages in this session?')) {
      setMessages([]);
      setError(null);
    }
  };

  return (
    <div className="chat-page">
      {/* Disclaimer Banner */}
      <div className="legal-notice-banner">
        <div className="notice-content">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>
            <strong>Educational Mini-Project Notice:</strong> This system uses semantic search and retrieval-augmented generation over official RBI documents. Outputs are AI-assisted analytical aids and not legally binding or formal regulatory opinions.
          </span>
        </div>
        {messages.length > 0 && (
          <button type="button" className="clear-chat-btn" onClick={handleClearHistory} title="Clear session history">
            Clear Chat
          </button>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="error-alert">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{error}</span>
          <button type="button" className="close-alert-btn" onClick={() => setError(null)}>
            &times;
          </button>
        </div>
      )}

      {/* Chat Messages Stream */}
      <div className="chat-history-container">
        {messages.length === 0 ? (
          <div className="chat-empty-state">
            <div className="empty-state-badge">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
                <line x1="12" y1="22.08" x2="12" y2="12" />
              </svg>
            </div>
            <h2>Real-Time RBI Policy Compliance & Intelligence</h2>
            <p>
              Ask any question on RBI Master Directions or describe a banking scenario to assess regulatory compliance. Answers cite exact source documents, page numbers, and clauses.
            </p>

            <div className="example-prompts-grid">
              {EXAMPLE_PROMPTS.map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="example-prompt-card"
                  onClick={() => handleSend(item.prompt)}
                >
                  <div className="example-card-meta">
                    <span className="example-category">{item.category}</span>
                    {item.scenario && <span className="scenario-chip">Scenario Check</span>}
                  </div>
                  <h4 className="example-title">{item.title}</h4>
                  <p className="example-text">{item.prompt}</p>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}
            {loading && (
              <div className="message-row assistant-row">
                <div className="assistant-card loading-card">
                  <div className="loading-spinner-row">
                    <div className="spinner"></div>
                    <span>Searching RBI regulations, evaluating semantic similarity, and verifying compliance requirements...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="chat-input-wrapper">
        <div className="input-container">
          <textarea
            className="chat-textarea"
            placeholder="Ask a question about RBI regulations or describe a banking scenario..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={loading}
          />
          <button
            type="button"
            className="send-button"
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
          >
            {loading ? (
              <span className="btn-spinner"></span>
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            )}
            <span>Analyze</span>
          </button>
        </div>
      </div>
    </div>
  );
}
