/* Notes from the attic — offline editorial personal site for Ren.
 * Sections: config · storage · seed · state/helpers · rendering · filters ·
 * note editor · motion · boot.
 * All user content is rendered with textContent and <template> clones; there
 * is no innerHTML, no network call and no external asset.
 */
(function () {
  "use strict";

  /* 1. Configuration ------------------------------------------------------ */
  const DB = window.STITCHCRAFT_DB || {};
  const NS = String(DB.tablePrefix || "stitchcraft") + ":personal-space:v1:";
  const KEYS = { notes: NS + "notes", photos: NS + "photos" };
  const REDUCED = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : { matches: false };
  const fmtDate = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" });
  const fmtMonth = new Intl.DateTimeFormat("en-GB", { month: "short", year: "numeric" });

  /* 2. Storage: localStorage, with an in-memory fallback for locked file:// */
  const memory = new Map();
  let storageOk = true;
  const store = {
    read(key) {
      try { const raw = window.localStorage.getItem(key); return raw ? JSON.parse(raw) : null; }
      catch (err) { storageOk = false; return memory.has(key) ? memory.get(key) : null; }
    },
    write(key, value) {
      memory.set(key, value);
      try { window.localStorage.setItem(key, JSON.stringify(value)); storageOk = true; } catch (err) { storageOk = false; }
    }
  };

  /* 3. Seed content ------------------------------------------------------- */
  function seedNotes() {
    return [
      {
        id: "note-field-notebook", title: "The slow art of keeping a field notebook",
        tags: ["Field notes", "Craft"], created_at: "2026-11-02T19:20:00.000Z", pinned: false,
        excerpt: "What starts as a list of chores becomes a record of the weather, the neighbours and the small decisions that make a week.",
        body: "What starts as a list of chores becomes a record of the weather, the neighbours and the small decisions that make a week. I keep one page per day, never more. The rule is not to describe anything important; the rule is to describe something at all. A receipt, a bird, the exact hour the radiators came on. In three years the notebook has become the only reliable calendar I own."
      },
      {
        id: "note-rain-recorded", title: "Rain, recorded",
        tags: ["Field notes", "Weather"], created_at: "2026-10-18T08:05:00.000Z", pinned: false,
        excerpt: "Three afternoons of weather logged from the same window, and what the rhythm of it changed about the room.",
        body: "Three afternoons of weather logged from the same window. Monday: rain arrived at 14:10 and left the street darker than it found it. Wednesday: no rain, but the gutters ran anyway. Friday: rain again, softer, and the neighbour's laundry stayed out the entire time. By the third page I had stopped writing about the weather and started writing about waiting."
      },
      {
        id: "note-wrong-notebook", title: "On keeping the wrong notebook",
        tags: ["Craft"], created_at: "2026-09-27T10:40:00.000Z", pinned: false,
        excerpt: "A defence of cheap paper, blunt pencils and pages that are allowed to be ugly.",
        body: "A defence of cheap paper, blunt pencils and pages that are allowed to be ugly. The beautiful notebook asks you to be careful; the cheap one asks nothing. I buy mine in packs of five from the stationery shop by the station and keep one in every bag. Some pages get rained on. Some get used for phone numbers. None of them hesitate."
      },
      {
        id: "note-one-window", title: "A room with one window",
        tags: ["Home", "Weather"], created_at: "2026-08-30T16:15:00.000Z", pinned: false,
        excerpt: "The attic is small in the way a sentence is small: every word has to earn its place.",
        body: "The attic is small in the way a sentence is small: every word has to earn its place. One window, east-facing, a desk that faces it. In summer the light arrives before the kettle does. In winter the room is dark by four and the lamp does all the work. I have stopped wanting a bigger room; I want this one to be better arranged."
      }
    ];
  }
  function seedPhotos() {
    return [
      { id: "photo-dusk", caption: "Dusk over the canal", taken_at: "2026-09-14", palette: "dusk", glyph: "🌾",
        alt: "Gradient study in pink and slate: dusk over the canal" },
      { id: "photo-moss", caption: "North ridge, early mist", taken_at: "2026-08-03", palette: "moss", glyph: "🌿",
        alt: "Gradient study in moss green and pale mist: the north ridge at dawn" },
      { id: "photo-ink", caption: "Window light, 11pm", taken_at: "2026-07-22", palette: "ink", glyph: "🌙",
        alt: "Gradient study in ink blue with one warm square: a lit window at night" },
      { id: "photo-rust", caption: "The old dye house", taken_at: "2026-06-30", palette: "rust", glyph: "🍂",
        alt: "Gradient study in rust orange and shadow: the old dye house wall" },
      { id: "photo-sand", caption: "Beach grass, low tide", taken_at: "2026-05-11", palette: "sand", glyph: "🐚",
        alt: "Gradient study in sand gold and grey: beach grass at low tide" },
      { id: "photo-plum", caption: "Plum sky after the storm", taken_at: "2026-04-02", palette: "plum", glyph: "🪶",
        alt: "Gradient study in plum and violet: the sky clearing after a storm" }
    ];
  }

  /* 4. State and helpers -------------------------------------------------- */
  const state = { notes: [], photos: [], tag: "all", opener: null, toastTimer: 0 };
  const $ = (id) => document.getElementById(id);
  const field = (name) => noteForm.elements.namedItem(name);
  const setText = (id, value) => { $(id).textContent = value; };
  const tagsOf = (note) => (Array.isArray(note.tags) ? note.tags : []);
  const readingTime = (body) => Math.max(1, Math.round(String(body).trim().split(/\s+/).filter(Boolean).length / 200)) + " min read";
  const dateLabel = (iso) => fmtDate.format(new Date(iso));
  const monthLabel = (iso) => fmtMonth.format(new Date(iso));
  function excerptOf(note) {
    if (note.excerpt) return note.excerpt;
    const text = String(note.body || "").replace(/\s+/g, " ").trim();
    return text.length > 180 ? text.slice(0, 177).replace(/\s+\S*$/, "") + "…" : text;
  }
  function loadOrSeed(key, factory) {
    const stored = store.read(key);
    if (Array.isArray(stored)) return stored;
    const seeded = factory();
    store.write(key, seeded);
    return seeded;
  }
  function tagNodes(parent, tags) {
    parent.replaceChildren();
    tags.forEach((tag) => {
      const span = document.createElement("span");
      span.textContent = tag;
      parent.appendChild(span);
    });
  }
  function toast(message) {
    const node = $("toast");
    node.textContent = message;
    node.hidden = false;
    window.clearTimeout(state.toastTimer);
    state.toastTimer = window.setTimeout(() => { node.hidden = true; }, 3000);
  }
  function updateModeBadge() {
    const badge = $("data-mode");
    badge.textContent = storageOk ? "Local · saved" : "Local · memory only";
    badge.dataset.state = storageOk ? "local" : "memory";
  }

  /* 5. Rendering ---------------------------------------------------------- */
  function filteredNotes() {
    if (state.tag === "all") return state.notes;
    return state.notes.filter((note) => tagsOf(note).includes(state.tag));
  }
  function renderWriting() {
    const notes = filteredNotes();
    const featured = notes[0] || null;
    $("featured").hidden = !featured;
    if (featured) {
      const date = $("featured-date");
      date.textContent = dateLabel(featured.created_at);
      date.dateTime = featured.created_at;
      setText("featured-read", readingTime(featured.body));
      setText("featured-title", featured.title);
      setText("featured-excerpt", excerptOf(featured));
      tagNodes($("featured-tags"), tagsOf(featured));
    }
    const list = $("note-list");
    const template = $("note-template");
    list.replaceChildren();
    notes.slice(1).forEach((note) => {
      const fragment = template.content.cloneNode(true);
      const time = fragment.querySelector(".note-card__date");
      time.textContent = dateLabel(note.created_at);
      time.dateTime = note.created_at;
      fragment.querySelector(".note-card__read").textContent = readingTime(note.body);
      fragment.querySelector(".note-card__title").textContent = note.title;
      fragment.querySelector(".note-card__excerpt").textContent = excerptOf(note);
      fragment.querySelector(".note-card__tags").setAttribute("aria-label", "Tags");
      tagNodes(fragment.querySelector(".note-card__tags"), tagsOf(note));
      list.appendChild(fragment);
    });
    $("notes-empty").hidden = notes.length > 0;
    if (!notes.length) {
      setText("notes-empty-title", state.tag === "all" ? "No notes yet" : "Nothing tagged “" + state.tag + "” yet");
      setText("notes-empty-copy", state.tag === "all" ? "Use “New note” to write the first one." : "Try another tag, or write the first note for it.");
    }
    const total = state.notes.length;
    setText("note-count", total + " note" + (total === 1 ? "" : "s"));
  }
  function renderTags() {
    const tagbar = $("tagbar");
    const tags = Array.from(new Set(state.notes.flatMap(tagsOf))).sort((a, b) => a.localeCompare(b));
    tagbar.replaceChildren();
    const make = (tag, label) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "tag";
      button.dataset.tag = tag;
      button.textContent = label;
      button.setAttribute("aria-pressed", String(state.tag === tag));
      button.addEventListener("click", () => {
        state.tag = tag;
        tagbar.querySelectorAll("button").forEach((node) => node.setAttribute("aria-pressed", String(node.dataset.tag === tag)));
        renderWriting();
      });
      tagbar.appendChild(button);
    };
    make("all", "All");
    tags.forEach((tag) => make(tag, tag));
  }
  function renderPhotos() {
    const wall = $("photo-wall");
    const template = $("photo-template");
    wall.replaceChildren();
    state.photos.forEach((photo) => {
      const fragment = template.content.cloneNode(true);
      const tile = fragment.querySelector(".photo-card__tile");
      tile.classList.add("photo-card__tile--" + (photo.palette || "ink"));
      tile.setAttribute("aria-label", photo.alt || "Gradient study: " + photo.caption);
      fragment.querySelector(".photo-card__glyph").textContent = photo.glyph || "◐";
      fragment.querySelector(".photo-card__text").textContent = photo.caption;
      const time = fragment.querySelector(".photo-card__time");
      time.textContent = monthLabel(photo.taken_at);
      time.dateTime = photo.taken_at;
      wall.appendChild(fragment);
    });
  }

  /* 6. Note editor -------------------------------------------------------- */
  const noteDialog = $("note-dialog");
  const noteForm = $("note-form");
  function openDialog() {
    state.opener = document.activeElement;
    noteForm.reset();
    clearErrors();
    if (typeof noteDialog.showModal === "function") noteDialog.showModal();
    else noteDialog.setAttribute("open", "");
    field("title").focus();
  }
  function closeDialog() {
    if (typeof noteDialog.close === "function") noteDialog.close();
    else noteDialog.removeAttribute("open");
  }
  function clearErrors() {
    ["title", "body"].forEach((name) => {
      field(name).removeAttribute("aria-invalid");
      setText(name + "-error", "");
    });
    setText("note-error", "");
    $("note-error").hidden = true;
  }
  function showErrors(errors) {
    Object.keys(errors).forEach((name) => {
      field(name).setAttribute("aria-invalid", "true");
      setText(name + "-error", errors[name]);
    });
    setText("note-error", "Check the highlighted fields before saving.");
    $("note-error").hidden = false;
  }
  function saveNote(event) {
    event.preventDefault();
    clearErrors();
    const title = field("title").value.trim();
    const body = field("body").value.trim();
    const errors = {};
    if (title.length < 3) errors.title = "Give the note a title of at least 3 characters.";
    if (body.length < 20) errors.body = "Write at least 20 characters — a sentence or two is fine.";
    if (Object.keys(errors).length) {
      showErrors(errors);
      field(Object.keys(errors)[0]).focus();
      return;
    }
    const tags = field("tags").value.split(",").map((tag) => tag.trim()).filter(Boolean)
      .reduce((list, tag) => {
        if (list.length < 4 && !list.some((entry) => entry.toLowerCase() === tag.toLowerCase())) list.push(tag);
        return list;
      }, []);
    const note = { id: "note-" + Date.now().toString(36), title, body, excerpt: "", tags, created_at: new Date().toISOString(), pinned: false };
    state.notes.unshift(note);
    state.tag = "all";
    store.write(KEYS.notes, state.notes);
    renderTags();
    renderWriting();
    updateModeBadge();
    closeDialog();
    toast("“" + title + "” saved to this device.");
  }
  function restoreFocus() {
    const target = state.opener;
    state.opener = null;
    if (target && target.isConnected && typeof target.focus === "function") target.focus();
    else $("new-note").focus();
  }
  function wireEditor() {
    $("new-note").addEventListener("click", openDialog);
    $("empty-new-note").addEventListener("click", openDialog);
    $("empty-show-all").addEventListener("click", () => {
      state.tag = "all";
      $("tagbar").querySelectorAll("button").forEach((node) => node.setAttribute("aria-pressed", String(node.dataset.tag === "all")));
      renderWriting();
      $("new-note").focus();
    });
    noteDialog.addEventListener("close", restoreFocus);
    noteForm.addEventListener("submit", saveNote);
    document.querySelectorAll("[data-close]").forEach((button) => {
      button.addEventListener("click", closeDialog);
    });
  }

  /* 7. Motion: GSAP when vendored, CSS fallback otherwise ----------------- */
  function animate() {
    const root = document.documentElement;
    if (REDUCED.matches) { root.classList.remove("motion-pending"); return; }
    const heroLines = document.querySelectorAll("[data-hero-line]");
    const reveals = document.querySelectorAll("[data-reveal]");
    try {
      if (window.gsap) {
        root.classList.remove("motion-pending");
        /* Transform-only: content is never hidden if frames are throttled. */
        window.gsap.from(heroLines, { y: 24, duration: 0.7, stagger: 0.08, ease: "power3.out" });
        window.setTimeout(() => {
          try { window.gsap.killTweensOf(heroLines); window.gsap.set(heroLines, { clearProps: "transform,translate" }); } catch (err) { /* noop */ }
        }, 1300);
        if ("IntersectionObserver" in window) {
          window.gsap.set(reveals, { y: 18 });
          const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
              if (!entry.isIntersecting) return;
              observer.unobserve(entry.target);
              window.gsap.to(entry.target, { y: 0, duration: 0.6, ease: "power2.out", overwrite: "auto", clearProps: "transform,translate" });
            });
          }, { rootMargin: "0px 0px -6% 0px", threshold: 0.1 });
          reveals.forEach((node) => observer.observe(node));
        }
      } else {
        reveals.forEach((node) => node.classList.add("reveal"));
        heroLines.forEach((node, index) => {
          node.style.transitionDelay = index * 80 + "ms";
          node.classList.add("is-in");
        });
        if ("IntersectionObserver" in window) {
          const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
              if (!entry.isIntersecting) return;
              entry.target.classList.add("is-in");
              observer.unobserve(entry.target);
            });
          }, { threshold: 0.1 });
          reveals.forEach((node) => observer.observe(node));
        } else {
          reveals.forEach((node) => node.classList.add("is-in"));
          root.classList.remove("motion-pending");
        }
        window.setTimeout(() => {
          root.classList.remove("motion-pending");
          document.querySelectorAll(".reveal:not(.is-in)").forEach((node) => node.classList.add("is-in"));
        }, 2800);
      }
    } catch (err) {
      root.classList.remove("motion-pending");
    }
  }

  /* 8. Boot --------------------------------------------------------------- */
  function boot() {
    state.notes = loadOrSeed(KEYS.notes, seedNotes).sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    state.photos = loadOrSeed(KEYS.photos, seedPhotos);
    $("year").textContent = new Date().getFullYear();
    renderTags();
    renderWriting();
    renderPhotos();
    updateModeBadge();
    wireEditor();
    animate();
  }
  try {
    boot();
  } catch (err) {
    document.documentElement.classList.remove("motion-pending");
    toast("The note library failed to load — reload the page to try again.");
    if (window.console && window.console.error) window.console.error(err);
  }
})();
