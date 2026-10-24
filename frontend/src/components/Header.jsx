import React from 'react';
import { Database, ShieldCheck, Cpu, Globe } from 'lucide-react';

export default function Header({ onOpenEvidenceLogs }) {
  return (
    <header className="desktop-header">
      <div className="brand-wrapper">
        <div className="logo-badge">
          LT
        </div>
        <div className="brand-text">
          <h1>LabelTruth</h1>
          <p>Indian Packaged Foods Claims Auditor & Nutrition Comparator</p>
        </div>
      </div>

      <div className="header-badges">
        <div className="tech-tag">
          <Globe size={13} color="#06b6d4" />
          <span>TinyFish Live Agent</span>
        </div>
        <div className="tech-tag">
          <Database size={13} color="#10b981" />
          <span>PostgreSQL Cache</span>
        </div>
        <div className="tech-tag">
          <ShieldCheck size={13} color="#a855f7" />
          <span>FSSAI Standards</span>
        </div>

        <button 
          className="btn-icon"
          onClick={onOpenEvidenceLogs}
          title="Inspect PostgreSQL Evidence Log Cache"
        >
          <Database size={16} />
          <span>Evidence Logs</span>
        </button>
      </div>
    </header>
  );
}
