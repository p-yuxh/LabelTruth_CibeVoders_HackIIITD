import React, { useState } from 'react';
import { ExternalLink, BookOpen, ChevronDown, ChevronUp, Scale, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function ReferenceStandardsSection({ citations = [], shareOfDaily = 0.15 }) {
  const [expanded, setExpanded] = useState(false);

  // Group citations by category
  const fssaiClaims = citations.filter((c) => c.benchmark_type === 'claim_rule');
  const dailyGuidelines = citations.filter((c) => c.benchmark_type === 'daily_limit');
  const clinicalGuidance = citations.filter((c) => c.benchmark_type === 'clinical_guidance');

  const sharePct = Math.round(shareOfDaily * 100);

  return (
    <div style={{ background: '#0a0a0a', border: '1px solid #2a2a2a', padding: '20px', marginTop: '24px' }}>
      {/* Header with expand/collapse */}
      <div
        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
        onClick={() => setExpanded(!expanded)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <Scale size={18} style={{ color: '#ffffff' }} />
          <div>
            <h4 style={{ fontSize: '0.88rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#ffffff' }}>
              Statutory Standards & Reference Citations
            </h4>
            <span style={{ fontSize: '0.72rem', color: '#888888' }}>
              Verified benchmarks from FSSAI, ICMR-NIN 2024, ADA 2026, and WHO with source provenance.
            </span>
          </div>
        </div>

        <button
          type="button"
          style={{ background: 'transparent', border: 'none', color: '#ffffff', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}
        >
          <span>{expanded ? 'Hide Details' : 'View Standards'}</span>
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      </div>

      {/* Disclosures Note */}
      <div style={{ background: '#121212', border: '1px solid #222222', padding: '12px', marginTop: '14px', fontSize: '0.76rem', color: '#cccccc', lineHeight: 1.5 }}>
        <div>
          <strong style={{ color: '#ffffff' }}>• Per-Serving Calculation Disclosure: </strong>
          Most statutory guidelines state per-day limits. Per-serving benchmarks are calculated as a{' '}
          <strong style={{ color: '#ffffff' }}>{sharePct}% configurable share</strong> of daily dietary allowances (e.g., ICMR-NIN 2024 salt 5 g/day, sugar 25 g/day).
        </div>
        <div style={{ marginTop: '4px' }}>
          <strong style={{ color: '#ffffff' }}>• Diabetes Assumptions: </strong>
          Diabetes/hypertension per-product thresholds are app-defined assumptions based on ADA 2026 & RSSDI guidance; they are not statutory statutory limits.
        </div>
        <div style={{ marginTop: '4px' }}>
          <strong style={{ color: '#ffffff' }}>• Lab Evidence: </strong>
          Third-party consumer lab reports (Trustified / Consumer Voice) are shown as reported third-party evidence, never legal proof of wrongdoing.
        </div>
      </div>

      {/* Expandable Citations Grid */}
      {expanded && (
        <div style={{ marginTop: '18px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* 1. FSSAI Claim Rules */}
          {fssaiClaims.length > 0 && (
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', color: '#a3a3a3', letterSpacing: '0.05em', marginBottom: '8px' }}>
                FSSAI Statutory Claim Standards (Advertising & Claims 2018 / Display 2020)
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
                {fssaiClaims.map((c, idx) => (
                  <div key={idx} style={{ background: '#141414', border: '1px solid #2a2a2a', padding: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <strong style={{ fontSize: '0.82rem', color: '#ffffff' }}>{c.parameter}</strong>
                      <span style={{ fontSize: '0.68rem', background: '#222222', color: '#a3a3a3', padding: '2px 6px' }}>
                        {c.statutory_status}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#ffffff', fontWeight: 600 }}>
                      Threshold: {c.value} {c.unit}
                    </div>
                    <p style={{ fontSize: '0.72rem', color: '#888888', marginTop: '4px' }}>{c.notes}</p>
                    <a
                      href={c.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="citation-link"
                      style={{ marginTop: '6px', display: 'inline-flex', fontSize: '0.72rem' }}
                    >
                      <ExternalLink size={10} />
                      <span>{c.source_name} (Accessed: {c.access_date})</span>
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 2. ICMR-NIN & WHO Daily Guidelines */}
          {dailyGuidelines.length > 0 && (
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', color: '#a3a3a3', letterSpacing: '0.05em', marginBottom: '8px' }}>
                ICMR-NIN 2024 & WHO Dietary Guidelines for Indians
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
                {dailyGuidelines.map((c, idx) => (
                  <div key={idx} style={{ background: '#141414', border: '1px solid #2a2a2a', padding: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <strong style={{ fontSize: '0.82rem', color: '#ffffff' }}>{c.parameter}</strong>
                      <span style={{ fontSize: '0.68rem', background: '#222222', color: '#a3a3a3', padding: '2px 6px' }}>
                        {c.statutory_status}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#ffffff', fontWeight: 600 }}>
                      Daily Benchmark: {c.value} {c.unit}
                    </div>
                    <p style={{ fontSize: '0.72rem', color: '#888888', marginTop: '4px' }}>{c.notes}</p>
                    <a
                      href={c.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="citation-link"
                      style={{ marginTop: '6px', display: 'inline-flex', fontSize: '0.72rem' }}
                    >
                      <ExternalLink size={10} />
                      <span>{c.source_name} (Accessed: {c.access_date})</span>
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 3. Diabetes Clinical Guidance */}
          {clinicalGuidance.length > 0 && (
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 800, textTransform: 'uppercase', color: '#a3a3a3', letterSpacing: '0.05em', marginBottom: '8px' }}>
                ADA 2026 & RSSDI Diabetes Clinical Nutrition Guidance
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
                {clinicalGuidance.map((c, idx) => (
                  <div key={idx} style={{ background: '#141414', border: '1px solid #2a2a2a', padding: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <strong style={{ fontSize: '0.82rem', color: '#ffffff' }}>{c.parameter}</strong>
                      <span style={{ fontSize: '0.68rem', background: '#222222', color: '#a3a3a3', padding: '2px 6px' }}>
                        {c.statutory_status}
                      </span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#ffffff', fontWeight: 600 }}>
                      Guideline: {c.value} {c.unit}
                    </div>
                    <p style={{ fontSize: '0.72rem', color: '#888888', marginTop: '4px' }}>{c.notes}</p>
                    <a
                      href={c.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="citation-link"
                      style={{ marginTop: '6px', display: 'inline-flex', fontSize: '0.72rem' }}
                    >
                      <ExternalLink size={10} />
                      <span>{c.source_name} (Accessed: {c.access_date})</span>
                    </a>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

