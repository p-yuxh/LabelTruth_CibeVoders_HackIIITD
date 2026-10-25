import React from 'react';

export default function FigmaComparisonCard({ item, onSelectProduct }) {
  if (!item) return null;

  return (
    <article className="comparison-card">
      <div className="comparison-top">
        <span>{item.category}</span>
        <b>{item.verdict}</b>
      </div>
      <div className="comparison-products">
        {[item.left, item.right].map((product, index) => {
          const imgName = product.image.split('/').pop()?.replace('.png', '') || '';
          let packClass = 'tall-pack';
          if (['nutri-choice', 'unibic', 'potata'].some((name) => product.image.includes(name))) {
            packClass = 'wide-pack';
          } else if (['maaza', 'pepsi', 'seven-up'].some((name) => product.image.includes(name))) {
            packClass = 'bottle-pack';
          }

          return (
            <div
              className="compare-product"
              key={`${product.name}-${index}`}
              style={{ cursor: onSelectProduct ? 'pointer' : 'default' }}
              onClick={() => onSelectProduct && onSelectProduct(product.name)}
            >
              <div className={`compare-image ${imgName} ${packClass}`}>
                <img src={product.image} alt={product.name} />
              </div>
              <h3>{product.name}</h3>
              <p>{product.note}</p>
              <div className="score">
                <strong>{product.score}</strong>
                <span>/ 100<br />match</span>
              </div>
            </div>
          );
        })}
        <span className="versus">VS</span>
      </div>
    </article>
  );
}

