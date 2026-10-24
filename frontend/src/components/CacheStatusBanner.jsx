import React, { useState } from 'react';
import { CheckCircle2, Globe2, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

export default function CacheStatusBanner({ result }) {
  const [showSources, setShowSources] = useState(false);
  const isCached = result.is_cached;
  const sources = result.source_urls || [];

  return (
    <div className="cache-banner">
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {isCached ? <CheckCircle2 size={16} color="#ffffff" /> : <Globe2 size={16} color="#ffffff" />}
        <span style={{ fontSize: '0.86rem', color: '#ffffff' }}>
          {isCached ? (
            <>
              <strong>Verified Product Record</strong> (Instant verification from audit history)
            </>
          ) : (
            <>
              <strong>Live Verified Audit</strong> (Freshly analyzed from brand and retailer sources)
            </>
          )}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <span className="badge-pill">
          {isCached ? 'VERIFIED RECORD' : 'LIVE AUDIT'}
        </span>
        
        {sources.length > 0 && (
          <button
            onClick={() => setShowSources(!showSources)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#a3a3a3',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              fontSize: '0.8rem',
              gap: '4px',
              fontWeight: 600,
              textDecoration: 'underline'
            }}
          >
            {sources.length} Verified Sources
            {showSources ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        )}
      </div>

      {showSources && (
        <div style={{ width: '100%', marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #2a2a2a' }}>
          <div style={{ fontSize: '0.74rem', color: '#737373', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>
            Primary Evidence Sources:
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
            {sources.map((url, idx) => (
              <a
                key={idx}
                href={url}
                target="_blank"
                rel="noreferrer"
                style={{
                  color: '#ffffff',
                  textDecoration: 'underline',
                  fontSize: '0.78rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  wordBreak: 'break-all'
                }}
              >
                <ExternalLink size={12} />
                {url}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
