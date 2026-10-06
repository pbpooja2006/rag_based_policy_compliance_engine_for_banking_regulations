import React, { useState } from 'react';

export default function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false);

  if (!source) return null;

  const { document, page, section, evidence } = source;
  const isLongEvidence = evidence && evidence.length > 220;

  return (
    <div className="source-card">
      <div className="source-header">
        <div className="source-title-group">
          <span className="source-index-chip">[{index + 1}]</span>
          <span className="source-doc-name" title={document}>
            {document}
          </span>
        </div>
        <div className="source-pills">
          <span className="pill-badge pill-page">Page {page}</span>
          {section && <span className="pill-badge pill-section">{section}</span>}
        </div>
      </div>

      <div className="source-body">
        <p className="evidence-text">
          {expanded || !isLongEvidence
            ? evidence
            : `${evidence.slice(0, 220)}...`}
        </p>

        {isLongEvidence && (
          <button
            type="button"
            className="expand-btn"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? '▲ Collapse excerpt' : '▼ Read full evidence passage'}
          </button>
        )}
      </div>
    </div>
  );
}
