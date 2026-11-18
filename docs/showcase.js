/* Stitchcraft showcase — progressive enhancement only.
   - Scroll reveal with IntersectionObserver.
   - Full respect for prefers-reduced-motion.
   - Copy-to-clipboard for the quickstart block.
   - No dependencies, no trackers, no network requests. */

(function () {
  "use strict";

  var root = document.documentElement;
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  var revealItems = Array.prototype.slice.call(
    document.querySelectorAll("[data-reveal]")
  );

  root.classList.add("js");

  function revealAll() {
    revealItems.forEach(function (item) {
      item.classList.add("is-visible");
    });
  }

  if (reduceMotion.matches || !("IntersectionObserver" in window)) {
    revealAll();
  } else {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) {
            return;
          }
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      {
        threshold: 0.1,
        rootMargin: "0px 0px -7% 0px"
      }
    );

    revealItems.forEach(function (item) {
      observer.observe(item);
    });

    if (typeof reduceMotion.addEventListener === "function") {
      reduceMotion.addEventListener("change", function (event) {
        if (event.matches) {
          revealAll();
        }
      });
    }
  }

  /* Header gets a little more opaque once the page moves. */
  var header = document.querySelector("[data-header]");
  var headerTicking = false;

  function updateHeader() {
    if (!header) {
      return;
    }
    header.classList.toggle("is-scrolled", window.scrollY > 14);
    headerTicking = false;
  }

  if (header) {
    updateHeader();
    window.addEventListener(
      "scroll",
      function () {
        if (headerTicking) {
          return;
        }
        headerTicking = true;
        window.requestAnimationFrame(updateHeader);
      },
      { passive: true }
    );
  }

  /* Copy quickstart commands. The "$" prompt is decorative and stripped. */
  var copyButtons = Array.prototype.slice.call(
    document.querySelectorAll("[data-copy]")
  );
  var copyStatus = document.querySelector("[data-copy-status]");

  function commandText(source) {
    return source.innerText
      .replace(/^\s*\$\s?/gm, "")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }

  function legacyCopy(text) {
    var textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.top = "-1000px";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();

    var copied = false;
    try {
      copied = document.execCommand("copy");
    } finally {
      document.body.removeChild(textarea);
    }

    if (!copied) {
      throw new Error("Copy command was rejected.");
    }
  }

  function writeClipboard(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return Promise.resolve().then(function () {
      legacyCopy(text);
    });
  }

  copyButtons.forEach(function (button) {
    var resetTimer = 0;

    button.addEventListener("click", function () {
      var sourceId = button.getAttribute("data-copy");
      var source = sourceId ? document.getElementById(sourceId) : null;

      if (!source) {
        return;
      }

      var text = commandText(source);
      button.disabled = true;

      writeClipboard(text)
        .then(function () {
          window.clearTimeout(resetTimer);
          button.textContent = "Copied";
          button.classList.add("is-copied");
          if (copyStatus) {
            copyStatus.textContent = "Quickstart commands copied to the clipboard.";
          }
          resetTimer = window.setTimeout(function () {
            button.textContent = "Copy";
            button.classList.remove("is-copied");
          }, 2200);
        })
        .catch(function () {
          if (copyStatus) {
            copyStatus.textContent =
              "Copy failed. Select the commands and copy them manually.";
          }
          button.textContent = "Copy failed";
          resetTimer = window.setTimeout(function () {
            button.textContent = "Copy";
          }, 2200);
        })
        .then(function () {
          button.disabled = false;
        });
    });
  });
})();
