import React from 'react';
import { History } from 'lucide-react';

export default function Header({ onOpenEvidenceLogs }) {
  return (
    <header className="desktop-header">
      <div className="brand-wrapper">
        <div className="logo-badge">
          LT
        </div>
        <div className="brand-text">
          <h1>LabelTruth</h1>
          <p>Packaged Food Claims & Ingredients Auditor</p>
        </div>
      </div>

      <div>
        <button 
          className="btn-icon"
          onClick={onOpenEvidenceLogs}
          title="Browse previously audited products"
        >
          <History size={15} />
          <span>Audit History</span>
        </button>
      </div>
    </header>
  );
}
