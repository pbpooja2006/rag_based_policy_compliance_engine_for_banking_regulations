import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ChatPage from './pages/ChatPage';
import AdminPage from './pages/AdminPage';
import AboutPage from './pages/AboutPage';
import { checkHealth } from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [healthInfo, setHealthInfo] = useState(null);

  const refreshHealth = async () => {
    try {
      const data = await checkHealth();
      setHealthInfo(data);
    } catch {
      // Backend may be starting or offline
    }
  };

  useEffect(() => {
    refreshHealth();
    const interval = setInterval(refreshHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app-layout">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        healthInfo={healthInfo}
      />

      <main className="app-main-content">
        {activeTab === 'chat' && <ChatPage />}
        {activeTab === 'admin' && <AdminPage onDocsChanged={refreshHealth} />}
        {activeTab === 'about' && <AboutPage />}
      </main>

      <footer className="app-footer">
        <div className="footer-content">
          <span>
            Adaptive RAG Banking Compliance MVP &bull; Academic Demonstration &bull; Powered by RBI Regulations, BAAI/bge-small-en-v1.5, ChromaDB &amp; Gemini
          </span>
          <span className="footer-links">
            <button type="button" onClick={() => setActiveTab('about')} className="footer-link-btn">
              Architecture &amp; Team
            </button>
          </span>
        </div>
      </footer>
    </div>
  );
}
