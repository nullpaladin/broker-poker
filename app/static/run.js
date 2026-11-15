(function () {
  var ICON = {pending: "·", in_progress: "🔄", waiting_captcha: "⏳", completed: "✅", failed: "❌", skipped: "➖"};
  var since = "", done = false, notified = {}, flash = null, baseTitle = document.title;
  var rows = {}, panel = document.getElementById("panel");
  document.querySelectorAll(".site").forEach(function (el) { rows[el.dataset.id] = el; });

  function esc(s) { var d = document.createElement("div"); d.textContent = s == null ? "" : s; return d.innerHTML; }
  function notify(msg) {
    try { if ("Notification" in window && Notification.permission === "granted") new Notification("Broker Poker", {body: msg}); } catch (e) {}
    if (!flash) { var on = false; flash = setInterval(function () { document.title = (on = !on) ? "❗ " + msg : baseTitle; }, 1000); }
  }
  window.addEventListener("focus", function () { if (flash) { clearInterval(flash); flash = null; document.title = baseTitle; } });
  try { if ("Notification" in window && Notification.permission === "default") Notification.requestPermission(); } catch (e) {}

  function paintRow(s) {
    var el = rows[s.id]; if (!el) return;
    el.className = "site " + s.status;
    el.querySelector(".st").textContent = ICON[s.status] + (s.warnings && s.status === "completed" ? "⚠" : "");
    el.querySelector(".nt").textContent = s.note || "";
    var open = el.querySelector("details") && el.querySelector("details").open;
    var shots = (s.screenshots || []).map(function (p) {
      var u = "/runs/" + BP.run + "/shot/" + encodeURIComponent(s.slug) + "/" + p.split("/").map(encodeURIComponent).join("/");
      return '<a href="' + u + '" target="_blank"><img loading="lazy" src="' + u + '" alt="screenshot"></a>';
    }).join("");
    el.querySelector(".detail").innerHTML = (s.status === "pending" || s.status === "skipped") && !s.log_tail ? "" :
      "<details" + (open ? " open" : "") + "><summary class='muted'>Details</summary>" +
      "<div class='muted'>Profile data available: " + esc((s.fields || []).join(", ")) + "<br>Rights requested: " + esc((s.rights || []).join(", ")) + "</div>" +
      (shots ? "<div class='thumbs'>" + shots + "</div>" : "") + "<pre>" + esc(s.log_tail) + "</pre></details>";
  }
  function paintPanel(waiting) {
    if (!waiting) { panel.className = "hidden"; panel.innerHTML = ""; return; }
    var c = waiting.captcha, key = c.id + ":" + c.kind;
    if (panel.dataset.key === key && !panel.classList.contains("hidden")) return;
    panel.dataset.key = key; panel.className = "";
    var html = "<h3 style='margin-top:0'>" + esc(waiting.name) + " needs you</h3>";
    if (c.kind === "text") {
      html += "<p>Look at the browser window, type what the site asks for here (" + esc(c.prompt) + ")</p><input type='text' id='ans' autocomplete='off'>";
    } else {
      html += "<p>A browser window opened. Solve the CAPTCHA / complete the step there" + (c.prompt ? " (" + esc(c.prompt) + ")" : "") + ", then click Continue here.</p>";
    }
    html += "<div class='actions'><button id='go'>Continue</button></div><p class='err' id='perr'></p>";
    panel.innerHTML = html;
    document.getElementById("go").onclick = function () {
      var v = c.kind === "text" ? document.getElementById("ans").value : "";
      fetch("/api/runs/" + BP.run + "/captcha/" + c.id + "/answer/", {method: "POST", credentials: "same-origin",
        headers: {"Content-Type": "application/json", "X-CSRFToken": csrf()}, body: JSON.stringify({answer: v})})
        .then(function (r) { if (!r.ok) return r.json().then(function (j) { document.getElementById("perr").textContent = j.error || "Failed"; }); panel.className = "hidden"; });
    };
    if (!notified[key]) { notified[key] = 1; notify(waiting.name + " needs you"); }
  }
  function csrf() { var m = document.cookie.match(/csrftoken=([^;]+)/); return m ? m[1] : ""; }

  function poll() {
    fetch("/api/runs/" + BP.run + "/status/" + (since ? "?since=" + encodeURIComponent(since) : ""), {credentials: "same-origin"})
      .then(function (r) { return r.json(); }).then(function (d) {
        d.sites.forEach(function (s) { paintRow(s); if (s.updated_at > since) since = s.updated_at; });
        paintPanel(d.waiting && d.waiting.captcha ? d.waiting : null);
        var c = d.counts;
        document.getElementById("counts").innerHTML = ["total", "completed", "failed", "skipped"].map(function (k) { return k + ": " + c[k]; }).join(" · ") +
          " · remaining: " + (c.pending + c.in_progress + c.waiting_captcha);
        var b = document.getElementById("banner");
        b.hidden = !BP.dry; b.textContent = "Practice run — forms are filled but nothing is submitted.";
        if (d.run.status === "complete" || d.run.status === "cancelled") {
          if (!done) { done = true; notify("Run finished"); if (location.search.indexOf("live=1") < 0) setTimeout(function () { location.href = "/runs/" + BP.run + "/done/"; }, 1500); }
          return;
        }
        setTimeout(poll, 1500);
      }).catch(function () { setTimeout(poll, 3000); });
  }
  poll();
})();
