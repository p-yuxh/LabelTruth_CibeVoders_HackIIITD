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
  ShieldAlert,
} from 'lucide-react';

export default function IndependentEvidenceSection({ evidence, category }) {
  const [unverifiedOpen, setUnverifiedOpen] = useState(false);

  if (!evidence) {
    return null;
  }

  const section1 = evidence.section_1 || evidence;
  const acceptedReports = section1.accepted || [];
  const unverifiedReports = section1.reported_not_verified || [];

  const coverageBadge = section1.coverage_badge || {
    status: acceptedReports.length > 0 ? 'FOUND' : 'SEARCHED_NONE_FOUND',
    badge_text: acceptedReports.length > 0 ? `FOUND (${acceptedReports.length} ${acceptedReports.length === 1 ? 'report' : 'reports'})` : 'SEARCHED_NONE_FOUND',
    message: section1.empty_state_text || 'No lab report found for this product on Trustified or Unbox Health.',
  };

  const summaryView = section1.summary_view || `Lab evidence available for ${acceptedReports.length} of ${Math.max(1, acceptedReports.length + unverifiedReports.length)} products`;

  const categoryName = category?.value || category || '';
  const browseText =
    section1.category_browse_text ||
    `Browse Consumer Voice ${categoryName ? categoryName + ' ' : ''}reviews (not evidence for this product)`;
  const browseUrl = section1.category_browse_url;

  return (
    <div className="evidence-container">
      {/* =================================================================
          INDEPENDENT LAB EVIDENCE (TRUSTIFIED, UNBOX HEALTH)
          ================================================================= */}
      <section className="evidence-section-card" aria-label="Independent lab evidence">
        <div className="evidence-section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
          <div>
            <h3 className="evidence-heading" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={18} />
              Independent lab evidence (Trustified, Unbox Health)
              {/* Independent lab & regulatory evidence */}
            </h3>
            <div style={{ fontSize: '0.74rem', color: '#888888', marginTop: '2px' }}>
              {summaryView}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: '4px',
                backgroundColor: coverageBadge.status === 'FOUND' ? 'rgba(74, 222, 128, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: coverageBadge.status === 'FOUND' ? '#4ade80' : '#f87171',
                border: `1px solid ${coverageBadge.status === 'FOUND' ? 'rgba(74, 222, 128, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
              }}
            >
              {coverageBadge.badge_text || coverageBadge.status}
            </span>
          </div>
        </div>

        {/* Accepted Reports */}
        {acceptedReports.length === 0 ? (
          <div className="empty-evidence-box">
            <Info size={18} style={{ marginBottom: '8px', color: '#737373' }} />
            <div style={{ fontSize: '0.9rem', color: '#e5e5e5', fontWeight: 700, lineHeight: 1.4 }}>
              {section1.empty_state_text ||
                'No lab report found for this product on Trustified or Unbox Health. This does not mean the product is safe or unsafe.'}
              {/* Fallback note: No matching lab report found for this product */}
            </div>
            <div style={{ fontSize: '0.78rem', color: '#888888', marginTop: '6px' }}>
              Statutory label cross-referencing remains active for standard claims auditing.
            </div>
            {browseUrl && (
              <div style={{ marginTop: '12px' }}>
                <a
                  href={browseUrl}
                  target="_blank"
                  rel="noopener noreferrer"
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

            const reportHref = report.final_url || report.original_report_url;
            const isTrustified = (report.source_name || '').toLowerCase().includes('trustified');
            const isUnbox = (report.source_name || '').toLowerCase().includes('unbox');
            const pdfReportUrl = report.pdf_report_url;

            const isRestricted = report.link_status === 'restricted' || report.is_restricted;
            const lastVerifiedDate = report.last_verified || report.checked_at?.slice(0, 10) || report.verified_at;

            return (
              <article key={report.record_id} className="evidence-item-card">
                {/* Meta Row: Source, Age Badge, Notes */}
                <div className="evidence-meta-row">
                  <div className="evidence-badges-cluster">
                    <span className="tier-badge" style={{ fontWeight: 700 }}>
                      {report.source_name}
                    </span>
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
                          <HelpCircle size={11} color="#888888" /> non-accredited test
                        </>
                      )}
                    </span>

                    {/* Specific Flag Pills */}
                    {report.labs_disagree && (
                      <span style={{ fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px', backgroundColor: 'rgba(239, 68, 68, 0.2)', color: '#f87171', border: '1px solid rgba(239, 68, 68, 0.3)', fontWeight: 600 }}>
                        labs disagree
                      </span>
                    )}
                    {report.page_vs_pdf_mismatch && (
                      <span style={{ fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px', backgroundColor: 'rgba(234, 179, 8, 0.2)', color: '#facc15', border: '1px solid rgba(234, 179, 8, 0.3)', fontWeight: 600 }}>
                        page vs PDF mismatch
                      </span>
                    )}
                    {report.batch_mapping_not_confirmed && (
                      <span style={{ fontSize: '0.7rem', padding: '2px 6px', borderRadius: '4px', backgroundColor: 'rgba(163, 163, 163, 0.2)', color: '#a3a3a3', border: '1px solid rgba(163, 163, 163, 0.3)', fontWeight: 600 }}>
                        batch mapping not confirmed
                      </span>
                    )}
                  </div>

                  {/* Links Row */}
                  <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    {reportHref && (
                      <a
                        href={reportHref}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="citation-link"
                        style={{ fontSize: '0.78rem' }}
                      >
                        <ExternalLink size={12} />
                        {isTrustified ? 'Open Trustified report page' : isUnbox ? 'Open Unbox Health report page' : 'Open report page'}
                      </a>
                    )}
                    {pdfReportUrl ? (
                      <a
                        href={pdfReportUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="citation-link"
                        style={{ fontSize: '0.78rem', color: '#60a5fa' }}
                      >
                        <ExternalLink size={12} /> Open lab report PDF
                      </a>
                    ) : isUnbox ? (
                      <span style={{ fontSize: '0.72rem', color: '#888888', fontStyle: 'italic' }}>
                        Report PDF may require an Unbox Health login
                      </span>
                    ) : null}

                    {lastVerifiedDate && (
                      <span style={{ fontSize: '0.7rem', color: '#737373' }}>
                        Last verified {lastVerifiedDate}
                      </span>
                    )}
                  </div>
                </div>

                {/* Source, Lab & Testing Facility */}
                <div>
                  <div style={{ fontSize: '0.92rem', fontWeight: 800, color: '#ffffff' }}>
                    {report.product}
                  </div>
                  <div style={{ fontSize: '0.78rem', color: '#a3a3a3', marginTop: '2px' }}>
                    Testing Facility: <strong>{report.lab_name}</strong>
                    {report.accreditation_no && report.accreditation_no !== 'not stated' && (
                      <span> • Scope / Cert: {report.accreditation_no}</span>
                    )}
                  </div>
                </div>

                {/* Informational Findings: Trustified Status / NMR / Unbox Rating */}
                {(report.testing_status_display || report.interpretation || report.unbox_rating) && (
                  <div style={{ margin: '6px 0', padding: '6px 10px', borderRadius: '4px', backgroundColor: 'rgba(255, 255, 255, 0.04)', fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    {report.testing_status_display && (
                      <div style={{ color: '#e5e5e5' }}>
                        <strong>Overall Status: </strong>
                        <span style={{ color: report.testing_status === 'Failed' ? '#f87171' : '#4ade80', fontWeight: 700 }}>
                          {report.testing_status_display}
                        </span>
                      </div>
                    )}
                    {report.interpretation && (
                      <div style={{ color: '#e5e5e5' }}>
                        <strong>Interpretation: </strong>
                        <span>{report.interpretation} (reported by Trustified)</span>
                      </div>
                    )}
                    {report.unbox_rating && (
                      <div style={{ color: '#e5e5e5' }}>
                        <strong>Rating: </strong>
                        <span>Unbox Health's own rating: <strong>{report.unbox_rating}</strong>{report.unbox_score ? ` (Score: ${report.unbox_score})` : ''}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Multi-Lab Separate Results (No Averaging) */}
                {report.lab_reports && report.lab_reports.length > 0 && (
                  <div style={{ margin: '8px 0', padding: '8px', borderRadius: '4px', border: '1px solid #333333', backgroundColor: '#141414' }}>
                    <div style={{ fontSize: '0.76rem', color: '#a3a3a3', fontWeight: 700, marginBottom: '6px', textTransform: 'uppercase' }}>
                      Separate Per-Lab Measurements (No Averaging):
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '8px' }}>
                      {report.lab_reports.map((lr, idx) => (
                        <div key={idx} style={{ padding: '6px', borderRadius: '4px', backgroundColor: '#1c1c1c', fontSize: '0.78rem' }}>
                          <div style={{ color: '#ffffff', fontWeight: 700 }}>{lr.lab_name}</div>
                          <div style={{ color: '#888888', fontSize: '0.72rem' }}>
                            {lr.accredited ? 'NABL Accredited' : 'non-accredited test'} • Tested: {lr.test_date || 'not stated'}
                          </div>
                          <div style={{ marginTop: '4px', color: '#4ade80', fontWeight: 600 }}>
                            {lr.parameter}: {lr.measured_value} {lr.unit}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

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

                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '4px', flexWrap: 'wrap' }}>
                      {item.discovery_url && (
                        <a
                          href={item.discovery_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="citation-link"
                          style={{ fontSize: '0.74rem' }}
                        >
                          <ExternalLink size={11} /> View Discovery Link
                        </a>
                      )}
                      {item.archived_url && (
                        <a
                          href={item.archived_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="citation-link"
                          style={{ fontSize: '0.74rem' }}
                        >
                          <ExternalLink size={11} /> Archived copy
                        </a>
                      )}
                    </div>
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
