import React from 'react';

export default function ComplianceBadge({ status }) {
  if (!status) return null;

  const config = {
    COMPLIANT: {
      label: 'COMPLIANT',
      className: 'badge-compliant',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      ),
      description: 'Activity appears consistent with referenced RBI regulations',
    },
    POTENTIALLY_NON_COMPLIANT: {
      label: 'POTENTIALLY NON-COMPLIANT',
      className: 'badge-noncompliant',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      ),
      description: 'Activity appears to conflict with mandatory RBI regulatory requirements',
    },
    REQUIRES_FURTHER_REVIEW: {
      label: 'REQUIRES FURTHER REVIEW',
      className: 'badge-review',
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      ),
      description: 'Insufficient facts or ambiguous context; regulatory expert review required',
    },
  };

  const item = config[status] || {
    label: status,
    className: 'badge-review',
    icon: null,
    description: '',
  };

  return (
    <div className={`compliance-badge-container ${item.className}`}>
      <span className="badge-tag">
        {item.icon}
        <strong>{item.label}</strong>
      </span>
      <span className="badge-disclaimer-chip">AI-assisted assessment &bull; Non-binding</span>
    </div>
  );
}
