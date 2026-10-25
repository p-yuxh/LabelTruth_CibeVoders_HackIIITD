import React from 'react';

/**
 * Reusable design-system components for the LabelTruth Audit Page.
 * Conforms to the consolidated design tokens (radius, borders, shadows, type-scale).
 */

export function Card({ children, className = '', style, ...props }) {
  return (
    <article className={`lt-card ${className}`} style={style} {...props}>
      {children}
    </article>
  );
}

export function SectionHeading({ children, className = '', style, icon, ...props }) {
  return (
    <h3 className={`lt-eyebrow ${className}`} style={style} {...props}>
      {icon && <span className="lt-eyebrow-icon">{icon}</span>}
      <span>{children}</span>
    </h3>
  );
}

export function Accordion({
  title,
  isOpen,
  onToggle,
  children,
  badge,
  infoComponent,
  id,
  className = '',
  style,
}) {
  return (
    <section className={`lt-accordion ${isOpen ? 'is-open' : 'is-closed'} ${className}`} id={id} style={style}>
      <button
        type="button"
        className="lt-accordion-header"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <span className="lt-accordion-title">
          <span>{title}</span>
          {infoComponent}
          {badge}
        </span>
        <span className="lt-accordion-icon" aria-hidden="true">
          {isOpen ? '−' : '+'}
        </span>
      </button>
      {isOpen && <div className="lt-accordion-body">{children}</div>}
    </section>
  );
}

export function Badge({ children, variant = '', className = '', style, ...props }) {
  return (
    <span className={`lt-badge ${variant} ${className}`} style={style} {...props}>
      {children}
    </span>
  );
}

export function TextLink({ children, href = '#', target, isDark = false, className = '', style, ...props }) {
  return (
    <a
      href={href}
      target={target}
      rel={target === '_blank' ? 'noopener noreferrer' : undefined}
      className={`lt-textlink ${isDark ? 'is-dark' : 'is-light'} ${className}`}
      style={style}
      {...props}
    >
      <span>{children}</span>
      <span className="lt-textlink-arrow" aria-hidden="true">→</span>
    </a>
  );
}

export function Callout({ variant = 'summary', title, children, className = '', style, ...props }) {
  return (
    <div className={`lt-callout callout-${variant} ${className}`} style={style} {...props}>
      {title && <b className="lt-callout-title">{title}</b>}
      <div className="lt-callout-content">{children}</div>
    </div>
  );
}

export function DataTable({ headers = [], rows = [], className = '', alignRightIndexes = [], nowrapIndexes = [] }) {
  return (
    <div className="lt-data-table-wrap">
      <table className={`lt-data-table ${className}`}>
        <thead>
          <tr>
            {headers.map((h, i) => {
              const isRight = alignRightIndexes.includes(i);
              return (
                <th
                  key={i}
                  style={{
                    textAlign: isRight ? 'right' : 'left',
                    whiteSpace: nowrapIndexes.includes(i) ? 'nowrap' : 'normal',
                  }}
                >
                  {h}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rIdx) => (
            <tr key={rIdx}>
              {row.map((cell, cIdx) => {
                const isRight = alignRightIndexes.includes(cIdx);
                const isNowrap = nowrapIndexes.includes(cIdx);
                return (
                  <td
                    key={cIdx}
                    style={{
                      textAlign: isRight ? 'right' : 'left',
                      whiteSpace: isNowrap ? 'nowrap' : 'normal',
                    }}
                  >
                    {cell}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

