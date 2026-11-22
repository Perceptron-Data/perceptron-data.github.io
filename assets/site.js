/* Perceptron Data — the only script of the site. No dependencies, no tracking, nothing sent anywhere.
   1. A copy button on every code block (the labels come from <body data-copy data-copied>).
   2. The category filter of the catalogue on the home page.
   Without JavaScript the page shows everything and no dead control. */
(function () {
  "use strict";
  var body = document.body;
  var label = { copy: body.getAttribute("data-copy") || "Copy", copied: body.getAttribute("data-copied") || "Copied" };

  // --- copy buttons ----------------------------------------------------------------------------------------------
  var status = document.createElement("p");
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  status.className = "sr-only";
  body.appendChild(status);

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }
    return new Promise(function (resolve, reject) {
      var area = document.createElement("textarea");
      area.value = text;
      area.setAttribute("readonly", "");
      area.className = "sr-only";
      body.appendChild(area);
      area.select();
      var done = false;
      try { done = document.execCommand("copy"); } catch (error) { done = false; }
      body.removeChild(area);
      if (done) { resolve(); } else { reject(new Error("copy")); }
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll("main pre"), function (pre) {
    var box = document.createElement("div");
    box.className = "code";
    pre.parentNode.insertBefore(box, pre);
    box.appendChild(pre);
    var button = document.createElement("button");
    button.type = "button";
    button.className = "copy";
    button.textContent = label.copy;
    button.addEventListener("click", function () {
      copyText(pre.textContent).then(function () {
        button.textContent = label.copied;
        status.textContent = label.copied;
        window.setTimeout(function () { button.textContent = label.copy; status.textContent = ""; }, 2000);
      }, function () {
        // the clipboard is not available: select the text, so that Ctrl+C copies it
        var range = document.createRange();
        range.selectNodeContents(pre);
        var selection = window.getSelection();
        selection.removeAllRanges();
        selection.addRange(range);
      });
    });
    box.insertBefore(button, pre);
  });

  // --- category filter -------------------------------------------------------------------------------------------
  var bar = document.querySelector(".filters");
  if (!bar) { return; }
  var groups = document.querySelectorAll("#actors .family");
  var shown = document.querySelector(".filter-status");
  var buttons = bar.querySelectorAll("button[data-filter]");
  bar.hidden = false;

  function show(filter) {
    var count = 0;
    Array.prototype.forEach.call(groups, function (group) {
      var visible = filter === "all" || group.getAttribute("data-cat") === filter;
      group.hidden = !visible;
      if (visible) { count += group.querySelectorAll(".card").length; }
    });
    Array.prototype.forEach.call(buttons, function (button) {
      var on = button.getAttribute("data-filter") === filter;
      button.setAttribute("aria-pressed", on ? "true" : "false");
      button.classList.toggle("is-on", on);
    });
    if (shown) {
      shown.textContent = filter === "all" ? "" : (shown.getAttribute("data-template") || "{n}").replace("{n}", count);
    }
  }

  Array.prototype.forEach.call(buttons, function (button) {
    button.addEventListener("click", function () { show(button.getAttribute("data-filter")); });
  });
})();
