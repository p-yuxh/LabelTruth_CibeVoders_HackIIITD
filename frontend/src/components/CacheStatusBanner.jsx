import React, { useState } from 'react';
import { Database, Globe, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

export default function CacheStatusBanner({ result }) {
  const [showSources, setShowSources] = useState(false);
  const isCached = result.is_cached;
  const sources = result.source_urls || [];

  return (
    <div className={`cache-banner ${isCached ? 'hit' : 'miss'}`}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {isCached ? <Database size={16} /> : <Globe size={16} />}
        <span>
          {isCached ? (
            <>
              <strong>PostgreSQL Cache Hit</strong> (Log #{result.evidence_log_id})
            </>
          ) : (
            <>
              <strong>TinyFish + Claude Live Pipeline</strong> (Saved as Log #{result.evidence_log_id})
            </>
          )}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span className={`badge-pill ${isCached ? 'hit' : 'miss'}`}>
          {isCached ? 'CACHED' : 'FRESH EXTRACT'}
        </span>
        
        {sources.length > 0 && (
          <button
            onClick={() => setShowSources(!showSources)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'inherit',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              fontSize: '0.75rem',
              gap: '2px',
              fontWeight: 600
            }}
          >
            {sources.length} sources
            {showSources ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        )}
      </div>

      {showSources && (
        <div style={{ width: '100%', marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
          <div style={{ fontSize: '0.72rem', color: '#9ca3af', marginBottom: '4px' }}>CRAWLED SOURCES:</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {sources.map((url, idx) => (
              <a
                key={idx}
                href={url}
                target="_blank"
                rel="noreferrer"
                style={{
                  color: 'inherit',
                  textDecoration: 'underline',
                  fontSize: '0.74rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
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

