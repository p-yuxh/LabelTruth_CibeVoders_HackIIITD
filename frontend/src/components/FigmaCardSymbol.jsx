import React from 'react';

export default function FigmaCardSymbol({ type }) {
  const paths = [
    (
      <React.Fragment key="eye">
        <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />
        <circle cx="12" cy="12" r="2.5" />
      </React.Fragment>
    ),
    (
      <React.Fragment key="flask">
        <path d="M9 3h6M10 3v5l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3M8 14h8" />
      </React.Fragment>
    ),
    (
      <React.Fragment key="layers">
        <path d="m12 3 8 4-8 4-8-4 8-4Z" />
        <path d="m4 12 8 4 8-4M4 17l8 4 8-4" />
      </React.Fragment>
    ),
  ];

  return (
    <span className="card-symbol" aria-hidden="true">
      <svg viewBox="0 0 24 24">
        {paths[type] || paths[0]}
      </svg>
    </span>
  );
}

