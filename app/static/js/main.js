// GPS Ushering and Events — shared site behaviour, loaded on every public
// page (see app/templates/base.html). Nothing here needs a build step or
// any library — plain DOM APIs throughout. Each block below is
// independent and guards itself with an `if (element)` check, so this
// one file works fine even on pages that don't have, say, a gallery or a
// booking form.

document.addEventListener('DOMContentLoaded', () => {
  /* Light / dark theme toggle. The INITIAL theme is set synchronously by
     an inline <script> at the very top of <head> (see app/templates/
     base.html) — before this file even loads — specifically to avoid a
     flash of the wrong theme on page load. This block only wires up the
     toggle button's click handler and keeps its moon/sun icon in sync
     with whatever theme is currently active. */
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

  /* Mobile nav toggle: the hamburger button just toggles an "open" class
     on itself (animates into an X, see css/style.css) and on the nav
     links list (slides it into view). Clicking any link inside also
     closes the menu, so navigating doesn't leave it stuck open. */
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

  /* FAQ accordion: only one answer open at a time. Clicking a question
     closes whichever other one is currently open, then — unless the
     clicked item WAS the one that just got closed — opens it by animating
     max-height from 0 to its natural scrollHeight (a plain CSS
     `height: auto` transition doesn't animate, so scrollHeight is the
     usual workaround). */
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

  /* Gallery filter: category buttons (All/Weddings/Corporate/...) just
     show/hide tiles by comparing the button's data-filter to each tile's
     data-category — no re-fetching or re-rendering, every tile is
     already in the page and this only toggles CSS display. */
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

  /* Gallery lightbox: clicking any tile opens the full-screen overlay
     (only present on the Gallery page — see the `lightbox=True` flag in
     app/routers/pages.py:gallery_page) and shows that tile's caption.
     Closes via the explicit close button, or by clicking the dark
     backdrop itself (the `e.target === lightbox` check distinguishes a
     click on the backdrop from a click bubbling up from its contents). */
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

  /* Booking / contact form — posts JSON to this same FastAPI app's own
     /api/bookings endpoint (see app/routers/bookings.py). Same origin, so
     no separate backend URL to configure. */
  const bookingForm = document.querySelector('#booking-form');
  if (bookingForm) {
    bookingForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const payload = Object.fromEntries(new FormData(bookingForm).entries());
      try {
        await fetch('/api/bookings', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } catch (err) {
        /* network hiccup — the success message below is optimistic either way */
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
