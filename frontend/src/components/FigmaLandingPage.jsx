import React, { useState, useEffect, useRef } from 'react';
import { Search } from 'lucide-react';
import FigmaCardSymbol from './FigmaCardSymbol';
import FigmaComparisonCard from './FigmaComparisonCard';

const values = [
  ['Strictly Independent', 'No sponsorships or hidden funding—only objective verdicts.'],
  ['Made Personal', 'Filter products by your allergies, diet, and preferences.'],
  ['Backed by Proof', 'Claims are checked against lab data and regulatory standards.'],
];

const steps = [
  ['01', 'Set Your Priorities', 'Choose products, dietary needs, and ingredients to avoid.'],
  ['02', 'We Check the Evidence', 'We compare labels with official sources and independent lab reports.'],
  ['03', 'Get a Clear Verdict', 'See what is verified, contradicted, or still unproven.'],
];

const faqs = [
  ['What is LabelTruth?', 'An independent tool that checks package claims against nutrition data, regulations, and lab evidence.'],
  ['Where does the data come from?', 'Product labels, official sources, regulatory guidance, and independent tests.'],
  ['Can brands pay to change their verdicts?', 'No. LabelTruth is independent, and brands cannot buy or alter a verdict.'],
  ['What if a product has no public lab test available?', 'We clearly show what is verified, what is unverified, and which evidence is still missing.'],
];

const testimonials = [
  ['“Finally, clarity beyond the marketing.”', 'I can quickly see what is actually in my kids’ snacks.', 'Ananya S., Parent'],
  ['“Peace of mind when it matters.”', 'Real cross-checks make managing dietary needs much easier.', 'Rahul M., Shopper'],
  ['“No more guessing at the shelf.”', 'Independent evidence has changed how I fill my cart.', 'Vikram K., Fitness Enthusiast'],
];

const comparisons = [
  {
    category: 'Instant Noodles',
    filter: 'Noodles',
    left: { name: 'Maggi 2-Minute Noodles', image: '/products/comparison/maggi.png', score: '58', note: 'Check sodium and serving size' },
    right: { name: 'Top Ramen Masala', image: '/products/comparison/top-ramen.png', score: '55', note: 'Compare fat and sodium' },
    verdict: 'Classic noodle matchup',
  },
  {
    category: 'Alternative Noodles',
    filter: 'Noodles',
    left: { name: 'Gluten Free 5 Grain', image: '/products/comparison/gluten-free-noodles.png', score: '78', note: 'Multi-grain, gluten-free claim' },
    right: { name: 'Moi Soi Konjac Noodles', image: '/products/comparison/moi-soi.png', score: '82', note: 'Low-calorie konjac noodles' },
    verdict: 'Check your dietary fit',
  },
  {
    category: 'Biscuits',
    filter: 'Biscuits',
    left: { name: 'NutriChoice Oats', image: '/products/comparison/nutri-choice.png', score: '69', note: 'Oats claim, verify sugar' },
    right: { name: 'Unibic Butter Cookies', image: '/products/comparison/unibic.png', score: '52', note: 'Indulgent butter cookie' },
    verdict: 'Health claim vs treat',
  },
  {
    category: 'Tea-Time Snacks',
    filter: 'Snacks',
    left: { name: 'Potata Biscuits', image: '/products/comparison/potata.png', score: '51', note: 'Review refined flour and salt' },
    right: { name: 'NutriChoice Oats', image: '/products/comparison/nutri-choice.png', score: '69', note: 'Compare fibre per serving' },
    verdict: 'Compare the full label',
  },
  {
    category: 'Sweet Drinks',
    filter: 'Fruit drinks',
    left: { name: 'Maaza Mango', image: '/products/comparison/maaza.png', score: '46', note: 'Fruit drink; inspect added sugar' },
    right: { name: 'Pepsi', image: '/products/comparison/pepsi.png', score: '34', note: 'Carbonated sugary drink' },
    verdict: 'Sugar is the key check',
  },
  {
    category: 'Soft Drinks',
    filter: 'Soft drinks',
    left: { name: 'Pepsi', image: '/products/comparison/pepsi.png', score: '34', note: 'Compare sugar and caffeine' },
    right: { name: '7UP', image: '/products/comparison/seven-up.png', score: '36', note: 'Compare sugar per 100 ml' },
    verdict: 'Similar product category',
  },
];

function ProductPill({ name, src, onClick }) {
  return (
    <div className="product" onClick={onClick} style={{ cursor: 'pointer' }}>
      <img src={src} alt={name} />
      <span>{name}</span>
    </div>
  );
}

export default function FigmaLandingPage({
  onSearch,
  onOpenAuth,
  onOpenAccount,
  onOpenPersonalize,
  onOpenEvidenceLogs,
  onOpenLegal,
  isLoggedIn,
  user,
  profile,
  loading = false,
}) {
  const [openFaq, setOpenFaq] = useState(0);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [productQuery, setProductQuery] = useState('');
  const [compareFilter, setCompareFilter] = useState('All products');
  const searchRef = useRef(null);

  const activeCount =
    (profile?.dietary_conditions?.filter((c) => c !== 'general_health')?.length || 0) +
    (profile?.allergies?.length || 0) +
    (profile?.avoid_ingredients?.length || 0);

  useEffect(() => {
    const updateProgress = () => {
      const available = document.documentElement.scrollHeight - window.innerHeight;
      setScrollProgress(available > 0 ? window.scrollY / available : 0);
      const searchScroll = Math.min(window.scrollY / 180, 1);
      searchRef.current?.style.setProperty('--search-scroll', String(searchScroll));
      searchRef.current?.style.setProperty('--search-scale', String(1 - searchScroll * 0.035));
      searchRef.current?.style.setProperty('--search-opacity', String(1 - searchScroll * 0.12));
    };

    const observer = new IntersectionObserver(
      (entries) => entries.forEach((entry) => entry.isIntersecting && entry.target.classList.add('is-visible')),
      { threshold: 0.12 }
    );

    document.querySelectorAll('.section, footer').forEach((section) => observer.observe(section));
    window.addEventListener('scroll', updateProgress, { passive: true });
    updateProgress();

    return () => {
      observer.disconnect();
      window.removeEventListener('scroll', updateProgress);
    };
  }, []);

  const handleHeroSubmit = (e) => {
    e.preventDefault();
    if (productQuery.trim()) {
      onSearch(productQuery.trim(), false);
    }
  };

  return (
    <main>
      {/* Scroll Progress Bar */}
      <div
        className="scroll-progress"
        style={{ transform: `scaleX(${scrollProgress})` }}
      />

      {/* Navigation Header */}
      <header>
        <a className="brand" href="#home">
          Label<span>Truth</span>
        </a>
        <nav aria-label="Main navigation">
          <a href="#home">Home</a>
          <a href="#about">About</a>
          <a href="#features">Features</a>
          <a href="#compare">Compare</a>
          <a href="#faq">FAQ</a>
        </nav>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            className="personalize-nav-btn"
            onClick={() => onOpenPersonalize && onOpenPersonalize('complete')}
            title="Personalise your health conditions and dietary preferences"
          >
            Personalise
            {activeCount > 0 && <span className="header-badge">{activeCount}</span>}
          </button>
          <button
            type="button"
            className="audit-history"
            onClick={onOpenEvidenceLogs}
            style={{ padding: '8px 14px', fontSize: '10px' }}
          >
            History
          </button>
          {isLoggedIn ? (
            <button
              className="login"
              type="button"
              onClick={onOpenAccount}
              style={{ background: 'var(--green)' }}
            >
              {user?.full_name ? user.full_name.split(' ')[0] : 'Account'}
            </button>
          ) : (
            <button
              className="login"
              type="button"
              onClick={() => onOpenAuth('login')}
            >
              Log in
            </button>
          )}
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero" id="home">
        <div className="search-shell" ref={searchRef}>
          <form className="search" onSubmit={handleHeroSubmit}>
            <input
              value={productQuery}
              onChange={(e) => setProductQuery(e.target.value)}
              placeholder="Search an Indian packaged food item (e.g. Maggi, Bournvita, Lays)..."
              aria-label="Search a product or ingredient"
            />
            <button
              className="search-submit"
              type="submit"
              aria-label="Search product"
              disabled={loading}
            >
              {loading ? (
                <span style={{ fontSize: '13px', lineHeight: 1 }}>…</span>
              ) : (
                <Search size={14} strokeWidth={2.5} />
              )}
            </button>
          </form>
        </div>

        <p className="eyebrow">Clear claims. Credible evidence.</p>
        <h1>
          Question the claim.<br />
          Verify the <em>proof.</em>
        </h1>
        <p className="subhead">Look past the label. Compare the facts.</p>

        {/* Verified Products Showcase */}
        <div className="products" aria-label="Example verified products">
          <ProductPill
            name="Kellogg's Corn Flakes"
            src="/products/corn-flakes.png"
            onClick={() => onSearch("Kellogg's Corn Flakes", false)}
          />
          <ProductPill
            name="Farmley Peri-Peri Makhana"
            src="/products/makhana.png"
            onClick={() => onSearch('Farmley Peri-Peri Makhana', false)}
          />
          <ProductPill
            name="Amul Dark Chocolate"
            src="/products/dark-chocolate.png"
            onClick={() => onSearch('Amul Dark Chocolate', false)}
          />
          <ProductPill
            name="Real Mixed Fruit Juice"
            src="/products/fruit-juice.png"
            onClick={() => onSearch('Real Mixed Fruit Juice', false)}
          />
          <ProductPill
            name="Makino Corn Munch"
            src="/products/corn-munch.png"
            onClick={() => onSearch('Makino Corn Munch', false)}
          />
        </div>
      </section>

      {/* From The Aisle Photo Gallery */}
      <section className="food-gallery" aria-label="Packaged foods in stores">
        <div className="gallery-copy">
          <span>FROM THE AISLE</span>
          <h2>Real products.<br />Clearer choices.</h2>
        </div>
        <figure>
          <img
            src="https://images.unsplash.com/photo-1688217170693-e821c6e18d72?auto=format&fit=crop&w=900&q=82"
            alt="Colourful packaged snacks displayed in a store"
          />
          <figcaption>Snacks</figcaption>
        </figure>
        <figure>
          <img
            src="https://images.unsplash.com/photo-1641652682537-e1a9334f206d?auto=format&fit=crop&w=900&q=82"
            alt="Packaged food products on grocery shelves"
          />
          <figcaption>Everyday foods</figcaption>
        </figure>
        <figure>
          <img
            src="https://images.unsplash.com/photo-1604719312245-6d2c47114758?auto=format&fit=crop&w=900&q=82"
            alt="Rows of packaged grocery products"
          />
          <figcaption>Pantry staples</figcaption>
        </figure>
      </section>

      {/* The Reality */}
      <section className="section reality">
        <div className="section-heading">
          <span>THE REALITY</span>
          <h2>Why We Need This Now</h2>
          <p>The truth shouldn’t be hidden behind the label.</p>
        </div>
        <div className="grid three reality-cards">
          {[
            ['The Health Halo', 'Words like “clean” and “zero sugar” can distract from what is actually inside.'],
            ['The Evidence Gap', 'Independent tests can reveal what bold package claims leave out.'],
            ['The Ingredient Maze', 'Complex names make everyday labels difficult to understand.'],
          ].map(([title, copy], index) => (
            <article className="card" key={title}>
              <FigmaCardSymbol type={index} />
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      {/* The Difference (Values) */}
      <section className="section values" id="features">
        <div className="section-heading">
          <span>THE DIFFERENCE</span>
          <h2>Why LabelTruth?</h2>
          <p>Independent evidence, made personal.</p>
        </div>
        <div className="grid three">
          {values.map(([title, copy]) => (
            <article className="value" key={title}>
              <i>✓</i>
              <h3>{title}</h3>
              <p>{copy}</p>
            </article>
          ))}
        </div>
      </section>

      {/* Simple by Design - How It Works */}
      <section className="section how">
        <div className="section-heading">
          <span>SIMPLE BY DESIGN</span>
          <h2>How It Works</h2>
        </div>
        <div className="how-layout">
          <figure className="how-visual">
            <img
              src="https://images.unsplash.com/photo-1667665908399-6d858dd26231?auto=format&fit=crop&w=1100&q=84"
              alt="Indian shopper comparing products in a grocery aisle"
            />
            <figcaption>
              <b>Shop smarter</b>
              <span>Evidence at every step.</span>
            </figcaption>
          </figure>
          <div className="steps">
            {steps.map(([number, title, copy]) => (
              <article className="step" key={number}>
                <b>{number}</b>
                <div>
                  <h3>{title}</h3>
                  <p>{copy}</p>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="section testimonials">
        <div className="section-heading left">
          <span>REAL STORIES</span>
          <h2>What consumers say about LabelTruth</h2>
        </div>
        <div className="grid three">
          {testimonials.map(([quote, copy, by]) => (
            <article className="quote" key={quote}>
              <h3>{quote}</h3>
              <p>{copy}</p>
              <small>— {by}</small>
            </article>
          ))}
        </div>
      </section>

      {/* Comparisons with Category Filtering */}
      <section className="section compare" id="compare">
        <div className="section-heading">
          <span>PRODUCT MATCHUPS</span>
          <h2>Compare Beyond the Label</h2>
          <p>Quick evidence-led snapshots across popular food types.</p>
        </div>
        <div className="category-pills" aria-label="Product categories">
          {['All products', 'Noodles', 'Biscuits', 'Snacks', 'Fruit drinks', 'Soft drinks'].map((type) => (
            <button
              type="button"
              className={compareFilter === type ? 'active' : ''}
              onClick={() => setCompareFilter(type)}
              aria-pressed={compareFilter === type}
              key={type}
            >
              {type}
            </button>
          ))}
        </div>
        <div className="comparison-grid">
          {comparisons
            .filter((item) => compareFilter === 'All products' || item.filter === compareFilter)
            .map((item) => (
              <FigmaComparisonCard
                item={item}
                key={item.category}
                onSelectProduct={(name) => onSearch(name, false)}
              />
            ))}
        </div>
        <p className="comparison-note">
          Scores are illustrative match summaries. Always review the full evidence for your dietary needs.
        </p>
      </section>

      {/* FAQs */}
      <section className="section faq" id="faq">
        <div className="section-heading left">
          <span>QUESTIONS, ANSWERED</span>
          <h2>FAQ</h2>
        </div>
        <div className="faq-list">
          {faqs.map(([question, answer], index) => (
            <article
              className={openFaq === index ? 'faq-item open' : 'faq-item'}
              key={question}
            >
              <button
                onClick={() => setOpenFaq(openFaq === index ? -1 : index)}
                aria-expanded={openFaq === index}
                type="button"
              >
                <span>{question}</span>
                <b>+</b>
              </button>
              <div>
                <p>{answer}</p>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* About Us */}
      <section className="section about" id="about">
        <div className="section-heading left">
          <span>ABOUT US</span>
          <h2>Built for clarity, not clicks.</h2>
        </div>
        <div className="about-grid">
          <article className="mission">
            <h3>Our Mission</h3>
            <p>Make packaged-food claims clear, credible, and easy to compare.</p>
          </article>
          <div>
            <article>
              <h3>Why We Built This</h3>
              <p>Food labels are full of appealing claims but short on clear context.</p>
            </article>
            <article>
              <h3>How We Stand Apart</h3>
              <p>We compare claims with nutrition data, regulations, and independent evidence.</p>
            </article>
          </div>
          <figure className="about-photo">
            <img
              src="https://images.unsplash.com/photo-1628102491629-778571d893a3?auto=format&fit=crop&w=900&q=84"
              alt="Shopper choosing groceries in a supermarket"
            />
          </figure>
        </div>
      </section>

      {/* Footer */}
      <footer>
        <div className="footer-brand">
          <a className="brand" href="#home">
            Label<span>Truth</span>
          </a>
          <p>Truth belongs on every label.</p>
          <small>Independent food-claim clarity for everyday choices.</small>
        </div>
        <div>
          <b>Explore</b>
          <a href="#about">About us</a>
          <a href="#features">Why LabelTruth</a>
          <a href="#compare">Compare products</a>
          <a href="#faq">FAQ</a>
          <a href="#home">How it works</a>
        </div>
        <div>
          <b>Contact</b>
          <a href="mailto:hello@labeltruth.com">hello@labeltruth.com</a>
          <a href="tel:+91987XXXXXXX">+91 987XX XXXXX</a>
          <span>
            Arise Complex, Near RQS Building<br />
            ALT State, India
          </span>
        </div>
        <div className="footer-support">
          <b>Need help?</b>
          <p>Questions about a claim or product?</p>
          <a className="support-button" href="tel:+91987XXXXXXX">
            <span aria-hidden="true">24/7</span> Support helpline
          </a>
        </div>
        <div className="footer-bottom">
          <small>© 2025 LabelTruth. All rights reserved.</small>
          <div>
            <a
              href="#terms"
              onClick={(e) => {
                e.preventDefault();
                onOpenLegal('terms');
              }}
            >
              Terms
            </a>
            <a
              href="#privacy"
              onClick={(e) => {
                e.preventDefault();
                onOpenLegal('privacy');
              }}
            >
              Privacy
            </a>
          </div>
        </div>
      </footer>
    </main>
  );
}

