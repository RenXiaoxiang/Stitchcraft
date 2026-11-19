/* Hollow Roast — launch page interactions.
   Progressive enhancement: the page is complete without JavaScript. */
(function () {
  'use strict';

  var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var menuButton = document.getElementById('menu-toggle');
  var nav = document.getElementById('site-nav');

  function setMenu(open) {
    if (!menuButton || !nav) return;
    menuButton.setAttribute('aria-expanded', open ? 'true' : 'false');
    nav.classList.toggle('is-open', open);
  }

  if (menuButton && nav) {
    menuButton.addEventListener('click', function () {
      setMenu(menuButton.getAttribute('aria-expanded') !== 'true');
    });
    nav.addEventListener('click', function (event) {
      if (event.target.closest('a')) setMenu(false);
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') setMenu(false);
    });
  }

  var form = document.getElementById('reserve-form');
  var email = document.getElementById('reserve-email');
  var note = document.getElementById('reserve-note');
  var error = document.getElementById('reserve-error');

  function showError(message) {
    if (!error) return;
    error.textContent = message;
    error.hidden = false;
    if (email) email.setAttribute('aria-invalid', 'true');
  }

  if (form && email && note) {
    email.addEventListener('input', function () {
      if (error) error.hidden = true;
      email.removeAttribute('aria-invalid');
    });
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var value = String(email.value || '').trim();
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        showError('That email does not look complete. Check it and try again.');
        email.focus();
        return;
      }
      if (error) error.hidden = true;
      email.removeAttribute('aria-invalid');
      note.textContent = 'You are on the list. We will send the pre-order link on 04 October.';
      var button = form.querySelector('button[type="submit"]');
      if (button) {
        button.disabled = true;
        button.textContent = 'On the list';
      }
      form.reset();
    });
  }

  if (!window.gsap || reduced) return;

  try {
    var hero = document.querySelector('.hero');
    if (hero) {
      window.gsap.timeline({ defaults: { duration: 0.8, ease: 'power3.out' } })
        .from('.hero__meta', { y: 12, opacity: 0, duration: 0.5 })
        .from('.hero h1 .hero__line', { y: 36, opacity: 0, stagger: 0.08 }, '-=0.2')
        .from('.hero__lede, .hero__actions', { y: 16, opacity: 0, stagger: 0.08 }, '-=0.38');
    }

    var reveals = document.querySelectorAll('.story .reveal, .release .reveal, .proof .reveal');
    if ('IntersectionObserver' in window) {
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          window.gsap.fromTo(entry.target, { opacity: 0, y: 20 }, {
            opacity: 1, y: 0, duration: 0.7, ease: 'power2.out', overwrite: true,
          });
          observer.unobserve(entry.target);
        });
      }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });
      reveals.forEach(function (element) { observer.observe(element); });
    }
  } catch (error) {
    /* Motion is optional; content stays visible. */
    if (window.console && console.warn) console.warn('[hollow-roast] motion skipped', error);
  }
})();
