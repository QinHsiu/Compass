/* Compass Web — i18n + elegant pipeline results */
(() => {
  const $ = (id) => document.getElementById(id);
  const I18N = window.COMPASS_I18N || {};
  let lang = localStorage.getItem("compass_lang") || "zh";
  if (!I18N[lang]) lang = "zh";
  let t = I18N[lang];
  let lastMeta = null;
  let lastPipeline = null;
  let lifeSessionId = "";
  let lifePlan = null;
  let lifeQuestions = [];

  const toast = (msg) => {
    const el = $("toast");
    el.textContent = msg;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 2800);
  };

  function esc(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderMd(src) {
    if (!src) return "";
    let text = String(src).replace(/\r\n/g, "\n");
    // fenced code
    text = text.replace(/```[\w]*\n([\s\S]*?)```/g, (_, code) => {
      return `<pre><code>${esc(code.trimEnd())}</code></pre>`;
    });
    const lines = text.split("\n");
    const out = [];
    let listBuf = [];
    let tableBuf = [];

    const flushList = () => {
      if (!listBuf.length) return;
      out.push("<ul>" + listBuf.map((x) => `<li>${x}</li>`).join("") + "</ul>");
      listBuf = [];
    };
    const flushTable = () => {
      if (tableBuf.length < 2) {
        tableBuf.forEach((row) => out.push(`<p>${inline(row)}</p>`));
        tableBuf = [];
        return;
      }
      const rows = tableBuf
        .filter((r) => !/^\s*\|?\s*[-:]+/.test(r))
        .map((r) =>
          r
            .replace(/^\|/, "")
            .replace(/\|$/, "")
            .split("|")
            .map((c) => c.trim())
        );
      if (!rows.length) {
        tableBuf = [];
        return;
      }
      const head = rows[0];
      const body = rows.slice(1);
      out.push(
        "<table><thead><tr>" +
          head.map((c) => `<th>${inline(c)}</th>`).join("") +
          "</tr></thead><tbody>" +
          body.map((r) => "<tr>" + r.map((c) => `<td>${inline(c)}</td>`).join("") + "</tr>").join("") +
          "</tbody></table>"
      );
      tableBuf = [];
    };

    const inline = (s) => {
      let x = esc(s);
      x = x.replace(/`([^`]+)`/g, "<code>$1</code>");
      x = x.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      x = x.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
      return x;
    };

    for (const raw of lines) {
      const line = raw;
      if (/^\s*\|/.test(line) && line.includes("|")) {
        flushList();
        tableBuf.push(line);
        continue;
      }
      if (tableBuf.length) flushTable();

      if (/^\s*[-*]\s+/.test(line)) {
        listBuf.push(inline(line.replace(/^\s*[-*]\s+/, "")));
        continue;
      }
      flushList();

      if (/^###\s+/.test(line)) {
        out.push(`<h3>${inline(line.replace(/^###\s+/, ""))}</h3>`);
      } else if (/^##\s+/.test(line)) {
        out.push(`<h2>${inline(line.replace(/^##\s+/, ""))}</h2>`);
      } else if (/^#\s+/.test(line)) {
        out.push(`<h1>${inline(line.replace(/^#\s+/, ""))}</h1>`);
      } else if (/^---+$/.test(line.trim())) {
        out.push("<hr/>");
      } else if (!line.trim()) {
        out.push("");
      } else if (line.startsWith("<pre>")) {
        out.push(line);
      } else {
        out.push(`<p>${inline(line)}</p>`);
      }
    }
    flushList();
    flushTable();
    return out.join("\n");
  }

  function applyI18n() {
    t = I18N[lang] || I18N.zh;
    document.documentElement.lang = { zh: "zh-CN", en: "en", ja: "ja", es: "es" }[lang] || "zh-CN";
    document.title = t.title;
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      let val = t[key];
      if (typeof val === "function") return;
      if (val == null) return;
      if (el.getAttribute("data-i18n-html") === "1" || /<em>|<br/.test(String(val))) {
        el.innerHTML = String(val).replace(/\n/g, "<br/>");
      } else {
        el.textContent = val;
      }
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-placeholder");
      if (t[key]) el.placeholder = t[key];
    });
    // theme options
    const theme = $("themeIn");
    if (theme) {
      [...theme.options].forEach((opt) => {
        const key = opt.getAttribute("data-i18n");
        if (key && t[key]) opt.textContent = t[key];
      });
    }
    if (lastMeta) renderAbout(lastMeta);
    if (lastPipeline) renderPipeline(lastPipeline, false);
    if (appWs && appWs.readyState === 1) {
      $("connStatus").textContent = t.connReady;
    }
  }

  function renderAbout(m) {
    lastMeta = m;
    $("aboutBox").textContent = t.aboutBody(m);
  }

  function showResultTab(name) {
    document.querySelectorAll(".result-tab").forEach((b) => {
      b.classList.toggle("active", b.dataset.rtab === name);
    });
    document.querySelectorAll(".result-pane").forEach((p) => {
      p.classList.toggle("active", p.id === `rtab-${name}`);
    });
  }

  function renderPipeline(m, announce) {
    lastPipeline = m;
    $("resultIdle").hidden = true;
    $("pipeMetrics").hidden = false;
    $("resultTabs").hidden = false;
    $("pipeSummary").hidden = false;
    $("mScore").textContent = m.score ?? "—";
    $("mTheme").textContent = m.theme || "—";
    $("mBank").textContent = m.bank_n ?? "—";
    $("mJob").textContent = m.job_id || "—";
    const summaryMd =
      `## ${t.tabSummary}\n\n` +
      `- **${t.metricScore}**: ${m.score}\n` +
      `- **${t.metricTheme}**: ${m.theme}\n` +
      `- **${t.metricBank}**: ${m.bank_n}\n` +
      `- **${t.metricJob}**: \`${m.job_id}\`\n` +
      (m.export_html ? `\n${t.btnExport}: \`${m.export_html}\`\n` : "");
    $("pipeSummary").innerHTML = renderMd(summaryMd);
    $("pipeResume").innerHTML = renderMd(m.resume_md || "");
    $("pipeSession").innerHTML = renderMd(m.session_md || "");
    $("pipeReport").innerHTML = renderMd(m.report_md || "");
    const gpath = m.graph_path || "/timeline";
    $("pipeGraph").href = gpath;
    $("btnGraph").href = gpath;
    const panel = $("graphEmbedPanel");
    const frame = $("graphFrame");
    if (panel && frame) {
      panel.hidden = false;
      frame.src = gpath;
    }
    showResultTab("summary");
    if (announce) toast(t.toastDone);
  }

  let appWs = null;
  let ivWs = null;
  let currentQ = "";
  let lastJobId = "";
  let monacoEditor = null;
  let pendingStarter = null;
  const synth = window.speechSynthesis;
  const Rec = window.SpeechRecognition || window.webkitSpeechRecognition;

  function wsUrl(path) {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${location.host}${path}`;
  }

  function showView(name) {
    document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
    document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
    const view = $(`view-${name}`);
    if (view) view.classList.add("active");
    const btn = document.querySelector(`.nav-btn[data-view="${name}"]`);
    if (btn) btn.classList.add("active");
  }

  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.onclick = () => showView(btn.dataset.view);
  });
  $("btnGoPipe").onclick = () => showView("pipeline");
  $("btnGoLive").onclick = () => showView("interview");
  if ($("btnGoLife")) $("btnGoLife").onclick = () => showView("life");

  function lifeRadarSvg(scores) {
    const dims = ["R", "I", "A", "S", "E", "C"];
    const size = 260;
    const cx = size / 2;
    const cy = size / 2;
    const r = size * 0.36;
    const pts = dims.map((d, i) => {
      const ang = -Math.PI / 2 + (2 * Math.PI * i) / dims.length;
      const val = Math.max(0, Math.min(100, Number(scores?.[d] || 0))) / 100;
      return `${cx + r * val * Math.cos(ang)},${cy + r * val * Math.sin(ang)}`;
    });
    let axes = "";
    let labels = "";
    dims.forEach((d, i) => {
      const ang = -Math.PI / 2 + (2 * Math.PI * i) / dims.length;
      const x = cx + r * Math.cos(ang);
      const y = cy + r * Math.sin(ang);
      const lx = cx + (r + 20) * Math.cos(ang);
      const ly = cy + (r + 20) * Math.sin(ang);
      axes += `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#cbd5e1"/>`;
      labels += `<text x="${lx}" y="${ly}" text-anchor="middle" dominant-baseline="middle" font-size="12" fill="#334155">${d} ${scores?.[d] ?? 0}</text>`;
    });
    return `<svg viewBox="0 0 ${size} ${size}" width="${size}" height="${size}" xmlns="http://www.w3.org/2000/svg">
      <circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="#e2e8f0"/>
      ${axes}
      <polygon points="${pts.join(" ")}" fill="rgba(43,109,229,.25)" stroke="#2b6de5" stroke-width="2"/>
      ${labels}
    </svg>`;
  }

  function renderLifeQuiz(questions) {
    lifeQuestions = questions || [];
    const box = $("lifeQuiz");
    box.innerHTML = "";
    const scale = t.lifeScale || ["1", "2", "3", "4", "5"];
    lifeQuestions.forEach((q, idx) => {
      const row = document.createElement("div");
      row.className = "life-q";
      const opts = [1, 2, 3, 4, 5]
        .map(
          (v) =>
            `<label class="life-likert"><input type="radio" name="lq_${esc(q.id)}" value="${v}" ${
              v === 3 ? "checked" : ""
            }/><span>${esc(scale[v - 1] || String(v))}</span></label>`
        )
        .join("");
      row.innerHTML =
        `<div class="life-q-text"><span class="life-q-n">${idx + 1}.</span> ${esc(q.text)} ` +
        `<code>${esc(q.dim)}</code></div><div class="life-likert-row">${opts}</div>`;
      box.appendChild(row);
    });
  }

  function collectLifeAnswers() {
    const answers = {};
    lifeQuestions.forEach((q) => {
      const el = document.querySelector(`input[name="lq_${q.id}"]:checked`);
      answers[q.id] = el ? Number(el.value) : 3;
    });
    return answers;
  }

  function renderLifeReport(m) {
    const plan = m.plan || {};
    lifePlan = plan;
    lifeSessionId = m.session_id || plan.session_id || lifeSessionId;
    $("lifeReportPanel").hidden = false;
    $("lifeCode").textContent = m.holland_code || plan.holland_code || "—";
    $("lifeConf").textContent =
      plan.confidence != null ? String(plan.confidence) : m.confidence != null ? String(m.confidence) : "—";
    $("lifeRouteLabel").textContent = m.route || plan.route || "—";
    $("lifeSid").textContent = lifeSessionId || "—";
    const scores = m.scores || plan.scores || {};
    $("lifeViz").innerHTML = `<div class="life-radar">${lifeRadarSvg(scores)}</div>`;
    const dims = plan.dimensions || [];
    $("lifeDims").innerHTML = dims
      .map((d) => {
        const sc = d.score ?? scores[d.code] ?? 0;
        return `<div class="life-dim"><div class="life-dim-h"><strong>${esc(d.code)}</strong> ${esc(
          d.name || ""
        )} <span>${sc}</span></div><div class="bar"><i style="width:${sc}%"></i></div><p>${esc(
          d.blurb || ""
        )}</p></div>`;
      })
      .join("");
    $("lifePaths").innerHTML = (plan.paths || [])
      .map(
        (p) =>
          `<article class="life-path-card"><h3>${esc(p.title)}</h3>` +
          `<p class="meta">${t.lifeMetricCode}: ${esc(String(p.holland_focus))} · ${p.fit_score}</p>` +
          `<p>${esc(p.why || "")}</p>` +
          `<p class="roles">${esc((p.roles || []).join(" · "))}</p></article>`
      )
      .join("");
    $("lifeReport").innerHTML = renderMd(m.report_md || "");
  }

  function showLifeRoute(extract, route) {
    const el = $("lifeRoute");
    el.hidden = false;
    const conf = extract?.confidence ?? "—";
    const reason = extract?.reason || "";
    const label = route === "direct" ? t.lifeRouteDirect : t.lifeRouteAssess;
    el.innerHTML =
      `<strong>${esc(label)}</strong> · ${t.lifeMetricConf} ${esc(String(conf))}` +
      (reason ? `<p class="desc">${esc(reason)}</p>` : "");
  }

  document.querySelectorAll(".result-tab").forEach((btn) => {
    btn.onclick = () => showResultTab(btn.dataset.rtab);
  });

  $("langSelect").value = lang;
  $("langSelect").onchange = () => {
    lang = $("langSelect").value;
    localStorage.setItem("compass_lang", lang);
    applyI18n();
  };

  function connectApp() {
    appWs = new WebSocket(wsUrl("/ws/app"));
    $("connStatus").textContent = t.connConnecting;
    appWs.onopen = () => {
      $("connStatus").textContent = t.connReady;
    };
    appWs.onclose = () => {
      $("connStatus").textContent = t.connRetry;
      setTimeout(connectApp, 3000);
    };
    appWs.onerror = () => {
      $("connStatus").textContent = t.connError;
    };
    appWs.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.type === "ready") {
        if (m.demo) $("btnDemo").hidden = false;
        renderAbout(m);
      } else if (m.type === "progress") {
        const stepMap = {
          ingest: t.stepIngest,
          demo: t.stepDemo,
          match: t.stepMatch,
          life: t.lifeRunning,
          life_score: t.lifeScoring,
        };
        $("pipeStatus").textContent = stepMap[m.step] || m.message || t.pipeRunning;
        if (m.step === "ingest") $("ingestStatus").textContent = t.stepIngest;
        if (m.step === "life" || m.step === "life_score") {
          $("lifeStatus").textContent = stepMap[m.step];
        }
      } else if (m.type === "life_done") {
        lifeSessionId = m.session_id || "";
        showLifeRoute(m.extract, m.route);
        if (m.need_assessment || (!m.ready && m.questions)) {
          $("lifeQuizPanel").hidden = false;
          $("lifeReportPanel").hidden = true;
          renderLifeQuiz(m.questions || []);
          $("lifeStatus").textContent = t.lifeRouteAssess;
        }
        if (m.ready && m.plan) {
          $("lifeQuizPanel").hidden = true;
          renderLifeReport(m);
          $("lifeStatus").textContent = t.lifeToastReady;
          toast(t.lifeToastReady);
        }
      } else if (m.type === "life_refine_done") {
        const chat = $("lifeChat");
        const block = document.createElement("div");
        block.className = "life-chat-item";
        block.innerHTML =
          `<div class="a">${esc(($("lifeRefineIn").value || "").trim())}</div>` +
          `<div class="q">${esc(m.reply || "")}</div>`;
        chat.appendChild(block);
        $("lifeRefineIn").value = "";
        if (m.plan) renderLifeReport(m);
      } else if (m.type === "life_export_done") {
        $("lifeStatus").textContent = `${t.lifeToastExport}\n${m.html || ""}`;
        toast(t.lifeToastExport);
      } else if (m.type === "pipeline_done") {
        lastJobId = m.job_id;
        $("pipeStatus").textContent = `${t.pipeDone} · ${m.job_id}`;
        renderPipeline(m, true);
        loadJobs();
      } else if (m.type === "ingest_done") {
        $("ingestStatus").textContent = t.toastIngest(m.count);
        $("ingestPreview").hidden = false;
        $("ingestPreview").innerHTML = renderMd(m.preview || "");
        toast(t.toastIngest(m.count));
      } else if (m.type === "bank_hits") {
        const box = $("bankOut");
        box.innerHTML = `<p class="status">${esc(t.bankTotal(m.total, m.backend))}</p>`;
        (m.hits || []).forEach((h) => {
          const d = document.createElement("div");
          d.className = "bank-item";
          const primary = h.q_display || h.q_zh || h.q || "";
          const secondary = h.q_secondary || "";
          const secLabel = lang === "zh" ? (t.bankOrigEn || "英文") : (t.bankZh || "中文");
          d.innerHTML =
            `<div class="meta">${esc(h.topic || "")} · <code>${esc(h.id || "")}</code></div>` +
            `<div class="q-main">${esc(primary)}</div>` +
            (secondary
              ? `<div class="q-sub"><span class="q-sub-label">${esc(secLabel)}</span>${esc(secondary)}</div>`
              : "");
          const btn = document.createElement("button");
          btn.textContent = t.bankPractice || "练习";
          btn.onclick = () => sendApp({ type: "practice_question", id: h.id });
          d.appendChild(btn);
          box.appendChild(d);
        });
      } else if (m.type === "practice_question") {
        if (m.starter_code) {
          showView("interview");
          const codeTab = document.querySelector('[data-tab="code"]');
          if (codeTab) codeTab.click();
          if (monacoEditor) {
            monacoEditor.setValue(m.starter_code);
          } else {
            pendingStarter = m.starter_code;
          }
        }
      } else if (m.type === "export_done") {
        $("pipeStatus").textContent =
          `${t.exportDone}\n${m.html || ""}\n${m.pdf || m.warning || t.exportNoPdf}`;
        toast(t.toastExport);
      } else if (m.type === "error") {
        const errMap = { need_jd: t.errNeedJd, no_fixture: t.errNoFixture };
        const msg = errMap[m.step] || m.message || t.errPrefix;
        toast(msg);
        $("pipeStatus").textContent = msg;
        $("ingestStatus").textContent = msg;
        if (m.step === "life") $("lifeStatus").textContent = msg;
      }
    };
  }

  $("btnLifeExplore").onclick = () => {
    const text = ($("lifeIn").value || "").trim();
    if (!text) return toast(t.lifeNeedText);
    $("lifeStatus").textContent = t.lifeRunning;
    $("lifeQuizPanel").hidden = true;
    $("lifeReportPanel").hidden = true;
    sendApp({ type: "life_explore", text, session_id: lifeSessionId || undefined });
  };
  $("btnLifeSubmit").onclick = () => {
    if (!lifeSessionId) return toast(t.lifeNeedText);
    $("lifeStatus").textContent = t.lifeScoring;
    sendApp({ type: "life_answer", session_id: lifeSessionId, answers: collectLifeAnswers() });
  };
  $("btnLifeRefine").onclick = () => {
    const message = ($("lifeRefineIn").value || "").trim();
    if (!lifeSessionId || !message) return;
    sendApp({ type: "life_refine", session_id: lifeSessionId, message });
  };
  $("btnLifeExport").onclick = () => {
    if (!lifeSessionId) return;
    sendApp({ type: "life_export", session_id: lifeSessionId });
  };
  $("btnLifeHandoff").onclick = () => {
    const hint = lifePlan?.handoff_jd_hint || "";
    if (hint) $("jdIn").value = hint;
    showView("pipeline");
    toast(t.lifeToastHandoff);
  };
  $("btnLifeFile").onclick = async () => {
    const f = $("lifeFile").files?.[0];
    if (!f) return toast(t.toastNeedFile);
    const fd = new FormData();
    fd.append("file", f);
    $("lifeStatus").textContent = t.ingestRunning;
    try {
      const r = await fetch("/api/life/extract", { method: "POST", body: fd });
      const data = await r.json();
      const preview = data.text || data.preview || "";
      if (!data.ok || !preview) {
        $("lifeStatus").textContent = (data.warnings || []).join("; ") || t.errPrefix;
        return;
      }
      $("lifeIn").value = preview.slice(0, 20000);
      $("lifeStatus").textContent = t.lifeBtnExplore;
    } catch (e) {
      try {
        const raw = await f.text();
        $("lifeIn").value = raw.slice(0, 20000);
        $("lifeStatus").textContent = t.lifeBtnExplore;
      } catch (e2) {
        $("lifeStatus").textContent = String(e);
      }
    }
  };

  function sendApp(obj) {
    if (!appWs || appWs.readyState !== 1) {
      toast(t.toastNeedWs);
      return;
    }
    appWs.send(JSON.stringify(obj));
  }

  $("btnPaste").onclick = () => sendApp({ type: "ingest_text", text: $("pasteIn").value });
  $("btnUpload").onclick = async () => {
    const f = $("fileIn").files?.[0];
    if (!f) return toast(t.toastNeedFile);
    const fd = new FormData();
    fd.append("file", f);
    $("ingestStatus").textContent = t.ingestRunning;
    try {
      const r = await fetch("/api/ingest", { method: "POST", body: fd });
      const data = await r.json();
      if (!data.ok) {
        $("ingestStatus").textContent = (data.warnings || []).join("; ") || t.errPrefix;
        return;
      }
      $("ingestStatus").textContent = t.toastIngest(data.count);
      $("ingestPreview").hidden = false;
      $("ingestPreview").innerHTML = renderMd(data.preview || "");
      toast(t.toastIngest(data.count));
    } catch (e) {
      $("ingestStatus").textContent = String(e);
    }
  };

  $("btnPipeline").onclick = () => {
    $("pipeStatus").textContent = t.pipeRunning;
    sendApp({ type: "pipeline", jd: $("jdIn").value, theme: $("themeIn").value, lang });
  };
  $("btnDemo").onclick = () => {
    $("pipeStatus").textContent = t.pipeRunning;
    sendApp({ type: "demo", theme: $("themeIn").value, lang });
  };
  $("btnExport").onclick = () => sendApp({ type: "export", job_id: lastJobId });
  $("btnBank").onclick = () =>
    sendApp({
      type: "search_bank",
      query: $("bankQ").value,
      semantic: $("bankSemantic").checked,
      pack: $("bankPack").value,
      difficulty: $("bankDiff").value,
      company: $("bankCompany").value,
      limit: 12,
      lang,
    });

  async function loadJobs() {
    const r = await fetch("/api/jobs");
    const data = await r.json();
    const sel = $("job");
    sel.innerHTML = "";
    (data.jobs || []).forEach((j) => {
      const o = document.createElement("option");
      o.value = j.job_id;
      o.textContent = `${j.title || j.job_id} · ${j.company || ""} · ${j.score ?? ""}`;
      sel.appendChild(o);
    });
    if (!sel.options.length) {
      const o = document.createElement("option");
      o.value = "latest";
      o.textContent = "—";
      sel.appendChild(o);
    } else {
      lastJobId = sel.value;
    }
  }

  function addLine(html, cls = "") {
    const d = document.createElement("div");
    d.className = cls;
    d.innerHTML = html;
    $("log").appendChild(d);
    $("log").scrollTop = $("log").scrollHeight;
  }

  function speak(text) {
    if (!synth) return;
    synth.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = { zh: "zh-CN", en: "en-US", ja: "ja-JP", es: "es-ES" }[lang] || "zh-CN";
    synth.speak(u);
  }

  function connectInterview() {
    const job = $("job").value || "latest";
    if (ivWs) try { ivWs.close(); } catch (_) {}
    ivWs = new WebSocket(wsUrl(`/ws/interview/${encodeURIComponent(job)}`));
    $("ivStatus").textContent = t.ivConnecting;
    ivWs.onopen = () => { $("ivStatus").textContent = t.ivLive; };
    ivWs.onclose = () => { $("ivStatus").textContent = t.ivClosed; };
    ivWs.onerror = () => { $("ivStatus").textContent = t.connError; };
    ivWs.onmessage = (ev) => {
      const m = JSON.parse(ev.data);
      if (m.type === "question") {
        currentQ = m.question;
        lastJobId = m.job_id || lastJobId;
        addLine(`<strong>Q${m.turn}</strong> ${esc(m.question)}`, "q");
        speak(m.question);
      } else if (m.type === "gate") {
        addLine(
          `${m.ok ? t.gateOk : t.gateBad} — ${esc(m.reason)} <code>${esc((m.evidence_ids || []).join(", "))}</code>`,
          m.ok ? "gate-ok" : "gate-bad"
        );
      } else if (m.type === "coding_feedback") {
        $("codeFb").textContent = (m.hints || []).join("\n");
      } else if (m.type === "error") {
        addLine(t.errPrefix + esc(m.message), "gate-bad");
      }
    };
  }

  $("btnStart").onclick = () => {
    $("log").innerHTML = "";
    connectInterview();
  };
  $("btnSpeak").onclick = () => speak(currentQ || "");
  $("btnSend").onclick = () => {
    if (!ivWs || ivWs.readyState !== 1) return toast(t.toastNeedIv);
    const text = $("answer").value.trim();
    if (!text) return;
    addLine(esc(text), "a");
    ivWs.send(JSON.stringify({ type: "answer", text }));
    $("answer").value = "";
  };
  $("btnMic").onclick = () => {
    if ($("useWhisper")?.checked) {
      toast(t.asrHint);
      return;
    }
    if (!Rec) return toast(t.toastNoSpeech);
    const r = new Rec();
    r.lang = { zh: "zh-CN", en: "en-US", ja: "ja-JP", es: "es-ES" }[lang] || "zh-CN";
    r.onresult = (e) => {
      $("answer").value = e.results[0][0].transcript;
    };
    r.onerror = () => toast(t.toastNoSpeech);
    r.start();
    $("ivStatus").textContent = t.ivConnecting;
    r.onend = () => {
      $("ivStatus").textContent = ivWs && ivWs.readyState === 1 ? t.ivLive : t.ivIdle;
    };
  };

  let mediaRec = null;
  let mediaChunks = [];
  $("btnRec").onclick = async () => {
    const hint = $("asrHint");
    if (mediaRec && mediaRec.state !== "inactive") {
      mediaRec.stop();
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaChunks = [];
      mediaRec = new MediaRecorder(stream);
      mediaRec.ondataavailable = (e) => {
        if (e.data.size) mediaChunks.push(e.data);
      };
      mediaRec.onstop = async () => {
        stream.getTracks().forEach((tr) => tr.stop());
        const blob = new Blob(mediaChunks, { type: "audio/webm" });
        const fd = new FormData();
        fd.append("file", blob, "oral.webm");
        fd.append("language", lang === "en" ? "en" : "zh");
        if (hint) hint.textContent = t.asrRunning;
        try {
          const r = await fetch("/api/asr", { method: "POST", body: fd });
          const data = await r.json();
          if (data.text) {
            $("answer").value = (($("answer").value || "") + " " + data.text).trim();
            toast(data.text.slice(0, 40));
          } else {
            toast(data.warning || t.asrFail);
          }
          if (hint) hint.textContent = data.warning || t.asrHint;
        } catch (e) {
          toast(t.asrFail);
          if (hint) hint.textContent = t.asrFail;
        }
        $("btnRec").textContent = t.btnRec;
      };
      mediaRec.start();
      $("btnRec").textContent = "■";
      if (hint) hint.textContent = t.asrRunning;
    } catch (e) {
      toast(t.asrFail);
    }
  };

  document.querySelectorAll("[data-tab]").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll("[data-tab]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.dataset.tab;
      $("tab-chat").style.display = tab === "chat" ? "" : "none";
      $("tab-code").style.display = tab === "code" ? "" : "none";
      if (tab === "code" && !monacoEditor) {
        require.config({
          paths: { vs: "https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs" },
        });
        require(["vs/editor/editor.main"], () => {
          monacoEditor = monaco.editor.create($("editor"), {
            value: pendingStarter || "def solve(nums):\n    # TODO\n    return nums\n",
            language: "python",
            theme: "vs",
            minimap: { enabled: false },
            automaticLayout: true,
          });
          if (pendingStarter) {
            monacoEditor.setValue(pendingStarter);
            pendingStarter = null;
          }
        });
      }
    };
  });

  $("btnCode").onclick = () => {
    if (!ivWs || ivWs.readyState !== 1) return toast(t.toastNeedIv);
    const code = monacoEditor ? monacoEditor.getValue() : "";
    ivWs.send(JSON.stringify({ type: "coding_submit", code }));
  };

  $("job").addEventListener("change", () => {
    const j = $("job").value;
    lastJobId = j;
    const href = j && j !== "latest" ? `/timeline?job_id=${encodeURIComponent(j)}` : "/timeline";
    $("btnGraph").href = href;
    $("pipeGraph").href = href;
  });

  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {});
  }

  applyI18n();
  connectApp();
  loadJobs();
})();
