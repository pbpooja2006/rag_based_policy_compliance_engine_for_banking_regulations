import React from 'react';

export default function Header({ activeTab, setActiveTab, healthInfo }) {
  return (
    <header className="app-header">
      <div className="header-container">
        <div className="brand-section">
          <div className="logo-badge">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M3 21h18M3 10h18M5 10v11M19 10v11M9 10v11M15 10v11M12 2L2 7h20L12 2z"/>
            </svg>
          </div>
          <div>
            <h1 className="app-title">Banking Regulatory Compliance Assistant</h1>
            <p className="app-subtitle">RBI-powered AI-assisted regulatory search and compliance support</p>
          </div>
        </div>

        <div className="header-actions">
          {healthInfo && (
            <div className="health-badge">
              <span className={`status-dot ${healthInfo.status === 'healthy' ? 'online' : 'degraded'}`}></span>
              <span className="kb-info">
                {healthInfo.document_count || 0} Docs &bull; {healthInfo.chunk_count || 0} Chunks
              </span>
            </div>
          )}

          <nav className="tab-nav">
            <button
              className={`nav-btn ${activeTab === 'chat' ? 'active' : ''}`}
              onClick={() => setActiveTab('chat')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
              Compliance Chat
            </button>
            <button
              className={`nav-btn ${activeTab === 'admin' ? 'active' : ''}`}
              onClick={() => setActiveTab('admin')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
                <polyline points="10 9 9 9 8 9"/>
              </svg>
              Regulations Admin
            </button>
            <button
              className={`nav-btn ${activeTab === 'about' ? 'active' : ''}`}
              onClick={() => setActiveTab('about')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="16" x2="12" y2="12"/>
                <line x1="12" y1="8" x2="12.01" y2="8"/>
              </svg>
              Architecture
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
}
