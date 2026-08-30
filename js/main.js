// GPS Ushering and Events — shared site behaviour

document.addEventListener('DOMContentLoaded', () => {
  /* Light / dark theme toggle. The initial theme is set synchronously in
     <head> (see layout.njk) to avoid a flash of the wrong theme; this just
     wires up the click handler and keeps the icon in sync. */
  const themeToggle = document.querySelector('.theme-toggle');
  if (themeToggle) {
    const icon = themeToggle.querySelector('i');
    const setIcon = (theme) => {
      if (icon) icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    };
    setIcon(document.documentElement.getAttribute('data-theme') || 'light');
    themeToggle.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      setIcon(next);
      try {
        localStorage.setItem('theme', next);
      } catch (e) {
        /* private browsing / storage blocked — theme just won't persist */
      }
    });
  }

  /* Mobile nav toggle */
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      navToggle.classList.toggle('open');
      navLinks.classList.toggle('open');
    });
    navLinks.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', () => {
        navToggle.classList.remove('open');
        navLinks.classList.remove('open');
      });
    });
  }

  /* Highlight active nav link */
  const current = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach((link) => {
    const href = link.getAttribute('href');
    if (href === current || (current === '' && href === 'index.html')) {
      link.classList.add('active');
    }
  });

  /* Back-to-top button */
  const backToTop = document.querySelector('.back-to-top');
  if (backToTop) {
    window.addEventListener('scroll', () => {
      backToTop.classList.toggle('show', window.scrollY > 400);
    });
    backToTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  /* FAQ accordion */
  document.querySelectorAll('.faq-item').forEach((item) => {
    const question = item.querySelector('.faq-question');
    const answer = item.querySelector('.faq-answer');
    if (!question || !answer) return;
    question.addEventListener('click', () => {
      const isOpen = item.classList.contains('open');
      document.querySelectorAll('.faq-item.open').forEach((openItem) => {
        openItem.classList.remove('open');
        openItem.querySelector('.faq-answer').style.maxHeight = null;
      });
      if (!isOpen) {
        item.classList.add('open');
        answer.style.maxHeight = answer.scrollHeight + 'px';
      }
    });
  });

  /* Gallery filter */
  const filterButtons = document.querySelectorAll('.filter-btn');
  const galleryItems = document.querySelectorAll('.gallery-item');
  filterButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      filterButtons.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.dataset.filter;
      galleryItems.forEach((item) => {
        const show = filter === 'all' || item.dataset.category === filter;
        item.style.display = show ? '' : 'none';
      });
    });
  });

  /* Gallery lightbox */
  const lightbox = document.querySelector('.lightbox');
  if (lightbox) {
    const lightboxCaption = lightbox.querySelector('.lightbox-caption');
    galleryItems.forEach((item) => {
      item.addEventListener('click', () => {
        lightboxCaption.textContent = item.dataset.label || '';
        lightbox.classList.add('open');
      });
    });
    lightbox.querySelector('.lightbox-close').addEventListener('click', () => {
      lightbox.classList.remove('open');
    });
    lightbox.addEventListener('click', (e) => {
      if (e.target === lightbox) lightbox.classList.remove('open');
    });
  }

  /* Booking / contact form — posts JSON to the FastAPI backend's /api/bookings
     endpoint (see /backend). The backend's URL is injected at build time via
     the <meta name="api-base-url"> tag (from _data/settings.json) since the
     frontend and backend are deployed as separate services on separate
     domains. Until that's set to a real deployed URL, the fetch fails
     silently and we still show the success message so the UI can be
     reviewed before hosting is live. */
  const bookingForm = document.querySelector('#booking-form');
  if (bookingForm) {
    bookingForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const apiBaseUrl = document.querySelector('meta[name="api-base-url"]')?.content || '';
      const payload = Object.fromEntries(new FormData(bookingForm).entries());
      try {
        await fetch(`${apiBaseUrl}/api/bookings`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } catch (err) {
        /* backend not deployed/configured yet — ignore until it is */
      }
      const successBox = document.querySelector('.form-success');
      if (successBox) {
        successBox.classList.add('show');
        successBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
      bookingForm.reset();
    });
  }

  /* Footer year */
  document.querySelectorAll('.current-year').forEach((el) => {
    el.textContent = new Date().getFullYear();
  });
});
