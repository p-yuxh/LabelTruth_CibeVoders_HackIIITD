import React, { useState } from 'react';
import { Copy, Check, Code, Bot, CheckCircle2 } from 'lucide-react';

export default function RawJsonViewer({ auditResponse }) {
  const [copiedNormalized, setCopiedNormalized] = useState(false);
  const [copiedAgent, setCopiedAgent] = useState(false);

  if (!auditResponse) return null;

  const handleCopy = (text, type) => {
    navigator.clipboard.writeText(text);
    if (type === 'normalized') {
      setCopiedNormalized(true);
      setTimeout(() => setCopiedNormalized(false), 2000);
    } else {
      setCopiedAgent(true);
      setTimeout(() => setCopiedAgent(false), 2000);
    }
  };

  const normalizedJsonStr = JSON.stringify(auditResponse.data, null, 2);
  const tinyfishJsonStr = JSON.stringify(auditResponse.tinyfish_agent_raw || {}, null, 2);

  return (
    <div className="content-card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 800, color: '#f8fafc' }}>
            Structured Pipeline Data & Agent Inspector
          </h3>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', marginTop: '2px' }}>
            Dual-pane desktop view: TinyFish Agent raw extraction side-by-side with the normalized LabelTruth schema.
          </p>
        </div>
      </div>

      <div className="dual-pane-json">
        {/* PANE 1: TinyFish Agent Raw Output */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Bot size={16} /> TinyFish Agent DOM Extraction (Raw)
            </span>
            <button
              className="btn-icon"
              style={{ padding: '4px 10px', fontSize: '0.75rem' }}
              onClick={() => handleCopy(tinyfishJsonStr, 'agent')}
            >
              {copiedAgent ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
              <span>{copiedAgent ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
          <pre className="code-viewer">
            {tinyfishJsonStr}
          </pre>
        </div>

        {/* PANE 2: Normalized Schema with Source URLs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#34d399', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Code size={16} /> Audited Schema (with Source URLs)
            </span>
            <button
              className="btn-icon"
              style={{ padding: '4px 10px', fontSize: '0.75rem' }}
              onClick={() => handleCopy(normalizedJsonStr, 'normalized')}
            >
              {copiedNormalized ? <Check size={13} color="#10b981" /> : <Copy size={13} />}
              <span>{copiedNormalized ? 'Copied' : 'Copy'}</span>
            </button>
          </div>
          <pre className="code-viewer">
            {normalizedJsonStr}
          </pre>
        </div>
      </div>
    </div>
  );
}
