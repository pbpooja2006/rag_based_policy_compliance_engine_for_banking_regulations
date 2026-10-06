import React, { useState } from 'react';
import ComplianceBadge from './ComplianceBadge';
import SourceCard from './SourceCard';

export default function ChatMessage({ message }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  if (message.role === 'user') {
    return <div className="message-row user-row"><div className="user-bubble"><div className="message-content">{message.content}</div></div></div>;
  }
  const { content = '', compliance_status, recommended_action, sources = [], is_error, is_scenario } = message;
  const primary = sources[0];
  return (
    <div className={`message-row assistant-row ${is_error ? 'error-row' : ''}`}>
      <article className="assistant-card">
        <div className="assistant-header">
          <div className="bot-avatar" aria-hidden="true">R</div>
          <div className="assistant-title-meta"><span className="assistant-name">RBI Regulatory Assistant</span><span className="rag-label">Grounded in indexed RBI documents</span></div>
        </div>
        {is_scenario && compliance_status && <div className="compliance-section"><ComplianceBadge status={compliance_status} /></div>}
        <section className="answer-section">
          <h3 className="answer-label">Answer</h3>
          <div className="message-body">{content.split('\n\n').filter(Boolean).map((para, i) => <p key={i} className="answer-paragraph">{para}</p>)}</div>
        </section>
        <section className="justification-card">
          <h3 className="justification-title">Why this answer</h3>
          {primary ? <>
            <p className="justification-intro">The most relevant supporting passage from the RBI documents:</p>
            <blockquote className="justification-evidence">{primary.evidence}</blockquote>
            <p className="justification-citation">{primary.document} · page {primary.page}{primary.section ? ` · ${primary.section}` : ''}</p>
          </> : <p className="justification-intro">The available RBI documents did not provide enough relevant evidence to answer confidently.</p>}
        </section>
        {is_scenario && recommended_action && <div className="recommendation-card"><div className="recommendation-title">Suggested next step</div><p className="recommendation-text">{recommended_action}</p></div>}
        {sources.length > 0 && <details className="all-sources"><summary>See all sources ({sources.length})</summary><div className="sources-grid">{sources.map((source, i) => <SourceCard key={i} source={source} index={i} />)}</div></details>}
        <p className="card-disclaimer">AI-assisted information for educational use only. Not a legal determination.</p>
      </article>
    </div>
  );
}