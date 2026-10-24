import React, { useState } from 'react';
import { Search, RotateCw } from 'lucide-react';

const SUGGESTIONS = [
  'Cadbury Bournvita',
  'Nestle Maggi 2-Minute Noodles',
  'Too Yumm Multigrain Chips',
  'Yoga Bar Dark Chocolate Oats',
  'Amul Butter',
];

export default function SearchSection({ onSearch, loading }) {
  const [query, setQuery] = useState('');
  const [forceRefresh, setForceRefresh] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !loading) {
      onSearch(query.trim(), forceRefresh);
    }
  };

  const handleChipClick = (suggestion) => {
    setQuery(suggestion);
    onSearch(suggestion, forceRefresh);
  };

  return (
    <div className="search-card">
      <form onSubmit={handleSubmit} className="search-input-wrapper">
        <input
          type="text"
          className="search-input"
          placeholder="Search Indian packaged food or brand (e.g. Cadbury Bournvita, Maggi, Too Yumm)..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={loading}
        />
        <button
          type="submit"
          className="btn-search"
          disabled={loading || !query.trim()}
        >
          {loading ? (
            <div className="spinner" />
          ) : (
            <>
              <Search size={18} />
              <span>Audit Product</span>
            </>
          )}
        </button>
      </form>

      <div className="search-footer">
        <div className="suggestion-chips">
          <span className="chip-label">Quick Suggestions:</span>
          {SUGGESTIONS.map((item) => (
            <button
              key={item}
              type="button"
              className="chip-btn"
              onClick={() => handleChipClick(item)}
              disabled={loading}
            >
              {item}
            </button>
          ))}
        </div>

        <div className="search-options">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={forceRefresh}
              onChange={(e) => setForceRefresh(e.target.checked)}
            />
            <span>Bypass PostgreSQL cache & force fresh TinyFish crawl</span>
          </label>
          {forceRefresh && (
            <span style={{ color: '#f59e0b', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 600 }}>
              <RotateCw size={12} /> Force Crawl Active
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
