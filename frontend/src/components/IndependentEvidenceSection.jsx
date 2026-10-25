import React, { useState } from 'react';
import {
  FileText,
  ExternalLink,
  AlertCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  Info,
  CheckCircle2,
  HelpCircle,
} from 'lucide-react';

export default function IndependentEvidenceSection({ evidence, category }) {
  const [unverifiedOpen, setUnverifiedOpen] = useState(false);

  if (!evidence) {
    return null;
  }

  const section1 = evidence.section_1 || evidence;
  const acceptedReports = section1.accepted || [];
  const unverifiedReports = section1.reported_not_verified || [];

  const categoryName = category?.value || category || '';
  const browseText =
    section1.category_browse_text ||
    `Browse Consumer Voice ${categoryName ? categoryName + ' ' : ''}reviews (not evidence for this product)`;
  const browseUrl = section1.category_browse_url || 'https://consumer-voice.org/category/food/';

  return (
    <div className="evidence-container">
      {/* =================================================================
          INDEPENDENT LAB & REGULATORY EVIDENCE
          ================================================================= */}
      <section className="evidence-section-card" aria-label="Independent lab and regulatory evidence">
        <div className="evidence-section-header">
          <h3 className="evidence-heading">
            <FileText size={18} />
            Independent lab &amp; regulatory evidence
          </h3>
          <span style={{ fontSize: '0.74rem', color: '#888888', fontWeight: 600 }}>
            {acceptedReports.length} Verified Lab {acceptedReports.length === 1 ? 'Record' : 'Records'}
          </span>
        </div>

        {/* Accepted Reports */}
        {acceptedReports.length === 0 ? (
          <div className="empty-evidence-box">
            <Info size={18} style={{ marginBottom: '8px', color: '#737373' }} />
            <div style={{ fontSize: '0.9rem', color: '#e5e5e5', fontWeight: 700 }}>
              No matching lab report found for this product.
            </div>
            <div style={{ fontSize: '0.78rem', color: '#888888', marginTop: '6px' }}>
              Claims without independent analytical testing default to statutory label cross-referencing.
            </div>
            {browseUrl && (
              <div style={{ marginTop: '12px' }}>
                <a
                  href={browseUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="citation-link"
                  style={{ fontSize: '0.8rem', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
                >
                  <ExternalLink size={12} />
                  <span>{browseText}</span>
                </a>
              </div>
            )}
          </div>
        ) : (
          acceptedReports.map((report) => {
            const ageStatus = report.age_status || 'unknown';
            const ageBadgeClass = `badge-age-${ageStatus}`;
            const ageBadgeLabel =
              ageStatus === 'recent'
                ? 'Recent'
                : ageStatus === 'ageing'
                ? 'Ageing'
                : ageStatus === 'old'
                ? 'Old / historical'
                : 'Date unknown';

            const gapPct = report.lab_gap_pct;
            const hasGap = gapPct !== null && gapPct !== undefined;
            const gapExceeded = hasGap && Math.abs(gapPct) > 15.0;

            const tierName =
              report.tier === 'A'
                ? 'Tier A: Regulators & Govt'
                : report.tier === 'B'
                ? 'Tier B: Notified NABL Lab'
                : report.tier === 'C'
                ? 'Tier C: Comparative Test Org'
                : 'Tier D: Reference Data';

            return (
              <article key={report.record_id} className="evidence-item-card">
                {/* Meta Row: Tier, Source, Age Badge */}
                <div className="evidence-meta-row">
                  <div className="evidence-badges-cluster">
                    <span className="tier-badge">{tierName}</span>
                    <span className={ageBadgeClass}>
                      <Clock size={11} /> {ageBadgeLabel}
                    </span>
                    <span
                      className={`accreditation-pill ${
                        report.accreditation_checked ? 'checked' : ''
                      }`}
                    >
                      {report.accreditation_checked ? (
                        <>
                          <CheckCircle2 size={11} color="#4ade80" /> Checked against NABL / FSSAI
                        </>
                      ) : (
                        <>
                          <HelpCircle size={11} color="#888888" /> Accreditation not checked
                        </>
                      )}
                    </span>
                  </div>

                  {report.original_report_url && (
                    <a
                      href={report.original_report_url}
                      target="_blank"
                      rel="noreferrer"
                      className="citation-link"
                      style={{ fontSize: '0.78rem' }}
                    >
                      <ExternalLink size={12} /> View Primary Report PDF
                    </a>
                  )}
                </div>

                {/* Source and Lab Specification */}
                <div>
                  <div style={{ fontSize: '0.92rem', fontWeight: 800, color: '#ffffff' }}>
                    {report.source_name}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#a3a3a3', marginTop: '2px' }}>
                    Testing Facility: <strong>{report.lab_name}</strong>
                    {report.accreditation_no && report.accreditation_no !== 'not stated' && (
                      <span> • Scope / Cert: {report.accreditation_no}</span>
                    )}
                  </div>
                </div>

                {/* Analytical Parameter & Lab vs Label Comparison */}
                <div className="evidence-values-grid">
                  <div className="evidence-val-col">
                    <span className="evidence-val-label">Parameter Tested</span>
                    <span className="evidence-val-data">{report.parameter}</span>
                  </div>

                  <div className="evidence-val-col">
                    <span className="evidence-val-label">Declared Label Value</span>
                    <span className="evidence-val-data">
                      {report.label_value !== null ? `${report.label_value} ${report.unit || ''}` : 'Not declared'}
                    </span>
                  </div>

                  <div className="evidence-val-col">
                    <span className="evidence-val-label">Independent Lab Value</span>
                    <span className="evidence-val-data">
                      {report.lab_value !== null ? `${report.lab_value} ${report.unit || ''}` : 'Qualitative Review'}
                    </span>
                  </div>

                  {hasGap && (
                    <div className="evidence-val-col">
                      <span className="evidence-val-label">Lab vs Label Gap</span>
                      <span className={`evidence-gap-pill ${gapExceeded ? 'gap-exceeded' : 'gap-acceptable'}`}>
                        {gapPct > 0 ? `+${gapPct}%` : `${gapPct}%`}
                      </span>
                    </div>
                  )}

                  <div className="evidence-val-col">
                    <span className="evidence-val-label">Measurement Basis</span>
                    <span style={{ fontSize: '0.8rem', color: '#cccccc', fontWeight: 600 }}>
                      {report.basis || 'per 100 g'}
                    </span>
                  </div>
                </div>

                {/* Testing Context: Method, Batch & Age Note */}
                <div style={{ fontSize: '0.78rem', color: '#888888', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                  <div>
                    Method: <span style={{ color: '#cccccc' }}>{report.method || 'not stated'}</span> • Sample Count: <span style={{ color: '#cccccc' }}>{report.sample_count || 'not stated'}</span> • Batch: <span style={{ color: '#cccccc' }}>{report.batch || 'not stated'}</span>
                  </div>
                  <div>
                    <strong>{report.age_display || 'Date not recorded'}</strong>. {report.batch_note || 'Results apply to the batch tested; the product may have changed since.'}
                  </div>
                </div>

                {/* Brand Response & Regulator Action */}
                {(report.brand_response && report.brand_response !== 'None on record.') ||
                (report.regulator_action && report.regulator_action !== 'None on record.') ? (
                  <div className="evidence-context-box">
                    {report.brand_response && report.brand_response !== 'None on record.' && (
                      <div>
                        <strong style={{ color: '#ffffff' }}>Brand Response: </strong>
                        {report.brand_response}
                      </div>
                    )}
                    {report.regulator_action && report.regulator_action !== 'None on record.' && (
                      <div style={{ marginTop: '4px' }}>
                        <strong style={{ color: '#ffffff' }}>Regulator Action: </strong>
                        {report.regulator_action}
                      </div>
                    )}
                  </div>
                ) : null}

                {/* Standard Statutory Batch Disclaimer */}
                <div className="evidence-disclaimer">
                  <Info size={12} />
                  <span>{report.disclaimer || 'Reported evidence for the tested batch, not proof of wrongdoing.'}</span>
                </div>
              </article>
            );
          })
        )}

        {/* Collapsible 'Reported, not verified' Group */}
        {unverifiedReports.length > 0 && (
          <div style={{ marginTop: '16px' }}>
            <button
              type="button"
              className="unverified-group-toggle"
              onClick={() => setUnverifiedOpen(!unverifiedOpen)}
              aria-expanded={unverifiedOpen}
            >
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <AlertCircle size={14} />
                Reported, not verified ({unverifiedReports.length})
              </span>
              {unverifiedOpen ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
            </button>

            {unverifiedOpen && (
              <div className="unverified-list-wrapper">
                {unverifiedReports.map((item) => (
                  <div key={item.record_id} className="unverified-item-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong style={{ fontSize: '0.86rem', color: '#ffffff' }}>
                        {item.source_name}
                      </strong>
                      <span className="badge-age-unknown">Not Verified for Verdicts</span>
                    </div>

                    <div className="unverified-reason-callout">
                      <strong>Reason Excluded: </strong>
                      {item.not_verified_reason || 'Failed strict acceptance rules.'}
                    </div>

                    <p style={{ fontSize: '0.8rem', color: '#888888', margin: 0 }}>
                      {item.raw_text_snippet || 'No text snippet attached.'}
                    </p>

                    {item.discovery_url && (
                      <div>
                        <a
                          href={item.discovery_url}
                          target="_blank"
                          rel="noreferrer"
                          className="citation-link"
                          style={{ fontSize: '0.74rem' }}
                        >
                          <ExternalLink size={11} /> View Discovery Link
                        </a>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}


