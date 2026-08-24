(() => {
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const FONT_MIN = 14;
  const FONT_MAX = 28;

  const state = {
    books: [],
    bookId: null,
    overview: null,
    toc: null,
    canon: null,
    continuity: null,
    outline: null,
    sessions: null,
    activeTab: "manuscript",
    canonSubTab: "characters",
    volFilter: "all",
    chapterSearch: "",
    activeChapter: null,
    font: Number(localStorage.getItem("ps-font") || 18),
    theme: localStorage.getItem("ps-theme") || "dark",
  };

  // Utilities
  function escapeHtml(s) {
    if (s == null) return "";
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function showToast(msg) {
    const el = $("#toast");
    if (!el) return;
    el.textContent = msg;
    el.classList.remove("hidden");
    clearTimeout(el._timer);
    el._timer = setTimeout(() => el.classList.add("hidden"), 2500);
  }

  function renderMarkdown(md) {
    if (!md) return "";
    const lines = md.replace(/\r\n/g, "\n").split("\n");
    const html = [];
    let inList = false;
    let para = [];

    const flushPara = () => {
      if (!para.length) return;
      const text = para.join("\n").trim();
      if (text) {
        html.push(`<p>${inline(text).replace(/\n/g, "<br>")}</p>`);
      }
      para = [];
    };

    const flushList = () => {
      if (inList) {
        html.push("</ul>");
        inList = false;
      }
    };

    const inline = (t) =>
      escapeHtml(t)
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>");

    for (let raw of lines) {
      const trimmed = raw.trim();
      if (raw.startsWith("# ")) {
        flushPara();
        flushList();
        html.push(`<h1>${inline(raw.slice(2))}</h1>`);
      } else if (raw.startsWith("## ")) {
        flushPara();
        flushList();
        html.push(`<h2>${inline(raw.slice(3))}</h2>`);
      } else if (raw.startsWith("### ")) {
        flushPara();
        flushList();
        html.push(`<h3>${inline(raw.slice(4))}</h3>`);
      } else if (trimmed === "---" || trimmed === "***") {
        flushPara();
        flushList();
        html.push("<hr>");
      } else if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        flushPara();
        if (!inList) {
          html.push("<ul>");
          inList = true;
        }
        html.push(`<li>${inline(trimmed.slice(2))}</li>`);
      } else if (trimmed === "") {
        flushPara();
        flushList();
      } else {
        flushList();
        para.push(raw);
      }
    }
    flushPara();
    flushList();
    return html.join("");
  }

  // Theme & Font
  function applyTheme() {
    document.documentElement.classList.remove("light", "parchment");
    document.documentElement.dataset.theme = state.theme;
    if (state.theme === "light") document.documentElement.classList.add("light");
    if (state.theme === "parchment") document.documentElement.classList.add("parchment");
    localStorage.setItem("ps-theme", state.theme);
    $$(".theme-opt").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.theme === state.theme);
    });
  }

  function applyFont() {
    state.font = Math.min(FONT_MAX, Math.max(FONT_MIN, state.font));
    document.documentElement.style.setProperty("--font-size", `${state.font}px`);
    $("#font-size-val").textContent = String(state.font);
    localStorage.setItem("ps-font", String(state.font));
  }

  // Data Fetching
  async function loadBooks(selectBookId = null) {
    try {
      const res = await fetch("/api/books");
      const data = await res.json();
      state.books = data.books || [];

      const select = $("#book-select");
      select.innerHTML = state.books
        .map((b) => `<option value="${escapeHtml(b.id)}">${escapeHtml(b.title)} (${escapeHtml(b.id)})</option>`)
        .join("");

      if (state.books.length > 0) {
        const targetId = selectBookId || state.bookId || state.books[0].id;
        select.value = targetId;
        await selectBook(targetId);
      }
    } catch (e) {
      showToast("加载书目失败: " + e.message);
    }
  }

  async function selectBook(bookId) {
    if (!bookId) return;
    state.bookId = bookId;
    $("#book-select").value = bookId;

    try {
      // Parallel fetch all data for selected book
      const [overviewRes, tocRes, canonRes, contRes, outlineRes, sessRes] = await Promise.all([
        fetch(`/api/books/${encodeURIComponent(bookId)}/overview`).then((r) => r.json()),
        fetch(`/api/books/${encodeURIComponent(bookId)}/toc`).then((r) => r.json()),
        fetch(`/api/books/${encodeURIComponent(bookId)}/canon`).then((r) => r.json()),
        fetch(`/api/books/${encodeURIComponent(bookId)}/continuity`).then((r) => r.json()),
        fetch(`/api/books/${encodeURIComponent(bookId)}/outline`).then((r) => r.json()),
        fetch(`/api/books/${encodeURIComponent(bookId)}/sessions`).then((r) => r.json()),
      ]);

      state.overview = overviewRes;
      state.toc = tocRes;
      state.canon = canonRes;
      state.continuity = contRes;
      state.outline = outlineRes;
      state.sessions = sessRes;

      updateStatsStrip();
      renderCurrentTab();
    } catch (e) {
      showToast("读取书籍数据失败: " + e.message);
    }
  }

  function updateStatsStrip() {
    if (!state.overview) return;
    const meta = state.overview.meta || {};
    const stats = state.overview.stats || {};
    $("#strip-title").textContent = meta.title || state.bookId;
    $("#strip-status").textContent = meta.status || "active";
    $("#strip-chars").textContent = `${stats.total_chars || 0} 字 (${stats.total_chapters || 0} 章)`;
    $("#strip-canon").textContent = `${(stats.characters || 0) + (stats.locations || 0) + (stats.rules || 0) + (stats.items || 0)} 设定`;
    $("#strip-threads").textContent = `${stats.open_threads || 0} 条未闭合`;
  }

  function switchTab(tabId) {
    state.activeTab = tabId;
    $$(".tab-btn").forEach((b) => b.classList.toggle("active", b.dataset.tab === tabId));
    $$(".tab-view").forEach((v) => v.classList.toggle("active", v.id === `view-${tabId}`));
    renderCurrentTab();
  }

  function renderCurrentTab() {
    switch (state.activeTab) {
      case "manuscript":
        renderManuscriptTree();
        break;
      case "canon":
        renderCanon();
        break;
      case "continuity":
        renderContinuity();
        break;
      case "outline":
        renderOutline();
        break;
      case "context":
        initContextTab();
        break;
      case "export":
        initExportTab();
        break;
      case "sessions":
        renderSessions();
        break;
      case "audit":
        break;
    }
  }

  // Tab 1: Manuscript
  function renderManuscriptTree() {
    const treeEl = $("#chapter-tree");
    if (!state.toc || !state.toc.volumes) {
      treeEl.innerHTML = '<div class="empty-state">暂无分册</div>';
      return;
    }

    const q = state.chapterSearch.trim().toLowerCase();
    const blocks = [];

    for (const vol of state.toc.volumes) {
      if (state.volFilter !== "all" && vol.kind !== state.volFilter) continue;
      const chaps = (vol.chapters || []).filter((ch) => {
        if (!q) return true;
        return `${ch.title} ${ch.file}`.toLowerCase().includes(q);
      });
      if (!chaps.length) continue;

      blocks.push(`<div class="vol-section">
        <div class="vol-title"><span class="kind ${escapeHtml(vol.kind)}">${escapeHtml(vol.kind_label || vol.kind)}</span> ${escapeHtml(vol.title)}</div>`);

      for (const ch of chaps) {
        const isActive = state.activeChapter && state.activeChapter.volumeId === vol.id && state.activeChapter.file === ch.file;
        blocks.push(`<button type="button" class="chapter-btn${isActive ? " active" : ""}" data-vol="${escapeHtml(vol.id)}" data-file="${escapeHtml(ch.file)}">
          <span>${escapeHtml(ch.title)}</span>
          <span class="chapter-size">${ch.size || 0}字</span>
        </button>`);
      }
      blocks.push(`</div>`);
    }

    treeEl.innerHTML = blocks.join("") || '<p class="empty" style="padding:1rem;color:var(--text-faint)">未找到匹配章节</p>';
    treeEl.querySelectorAll(".chapter-btn").forEach((btn) => {
      btn.addEventListener("click", () => openChapter(btn.dataset.vol, btn.dataset.file));
    });
  }

  async function openChapter(volumeId, filename) {
    try {
      state.activeChapter = { volumeId, file: filename };
      renderManuscriptTree();

      const res = await fetch(`/api/books/${encodeURIComponent(state.bookId)}/chapters/${encodeURIComponent(volumeId)}/${encodeURIComponent(filename)}`);
      const data = await res.json();

      const metaBanner = $("#article-meta-banner");
      metaBanner.classList.remove("hidden");
      const fm = data.front_matter || {};
      metaBanner.innerHTML = `
        <div><span class="stat-label">章节 ID：</span><strong>${escapeHtml(fm.id || data.file)}</strong></div>
        <div><span class="stat-label">类型：</span><span class="badge ${fm.kind === "continue" ? "badge-warning" : "badge-success"}">${escapeHtml(data.volume_kind || fm.kind || "original")}</span></div>
        <div><span class="stat-label">衔接上一章：</span><code>${escapeHtml(fm.source_after || fm.source_chapter || fm.source || "—")}</code></div>
        <div><span class="stat-label">字数：</span><strong>${data.chars || 0} 字</strong></div>
      `;

      $("#article-body").innerHTML = `<h1>${escapeHtml(data.title)}</h1>${renderMarkdown(data.markdown || "")}`;
      $("#reader-pane").scrollTop = 0;
    } catch (e) {
      showToast("读取章节失败: " + e.message);
    }
  }

  // Tab 2: Canon
  function renderCanon() {
    const container = $("#canon-content");
    if (!state.canon) {
      container.innerHTML = '<div class="empty-state">暂无正典数据</div>';
      return;
    }

    const sub = state.canonSubTab;
    if (sub === "characters") {
      const chars = state.canon.characters || [];
      container.innerHTML = `<div class="cards-grid">${chars
        .map((c) => {
          const tier = (c.tier || "C").toUpperCase();
          const evidenceList = (c.evidence || [])
            .map(
              (ev) => `<div class="evidence-box">
                <div class="evidence-quote">“${escapeHtml(ev.quote)}”</div>
                <div class="evidence-ref"><span>出处：<code>${escapeHtml(ev.ref)}</code></span><span class="badge badge-subtle">${escapeHtml(ev.confidence || "high")}</span></div>
              </div>`
            )
            .join("");

          return `<div class="char-card">
            <div class="card-head">
              <div class="card-title">${escapeHtml(c.name || c.id)}</div>
              <span class="tier-badge tier-${tier}">Tier ${tier}</span>
            </div>
            <p style="font-size:0.85rem;color:var(--text-dim)">${escapeHtml(c.summary || "")}</p>
            <div style="font-size:0.8rem;display:grid;gap:0.3rem;background:var(--bg-soft);padding:0.6rem;border-radius:6px;">
              <div><strong style="color:var(--text-faint)">身份：</strong>${escapeHtml((c.identity && c.identity.occupation) || "—")} · ${escapeHtml((c.identity && c.identity.gender) || "")}</div>
              <div><strong style="color:var(--text-faint)">性格：</strong>${escapeHtml((c.personality && (c.personality.traits || []).join("、")) || "—")}</div>
              <div><strong style="color:var(--text-faint)">目标：</strong>${escapeHtml((c.goals && (c.goals.short_term || []).join("；")) || "—")}</div>
            </div>
            ${evidenceList ? `<div style="margin-top:0.4rem;"><strong style="font-size:0.75rem;color:var(--accent)">📌 原文证据链 (Evidence)</strong><div style="display:grid;gap:0.4rem;margin-top:0.3rem;">${evidenceList}</div></div>` : ""}
          </div>`;
        })
        .join("")}</div>`;
    } else if (sub === "relationships") {
      container.innerHTML = `<div class="doc-card">${renderMarkdown(state.canon.relationships || "暂无关系记录")}</div>`;
    } else if (sub === "timeline") {
      const events = state.canon.timeline || [];
      container.innerHTML = `<div class="table-card"><table class="data-table">
        <thead><tr><th>时期/时间</th><th>事件</th><th>参与人物</th><th>原文依据</th></tr></thead>
        <tbody>${events.map((ev) => `<tr>
          <td><strong>${escapeHtml(ev.era || ev.date || "—")}</strong></td>
          <td>${escapeHtml(ev.summary || ev.title || "—")}</td>
          <td>${escapeHtml((ev.characters || []).join("、") || "—")}</td>
          <td><code>${escapeHtml(ev.ref || "—")}</code></td>
        </tr>`).join("")}</tbody>
      </table></div>`;
    } else {
      const items = state.canon[sub] || [];
      container.innerHTML = `<div class="cards-grid">${items
        .map((item) => {
          const evidenceList = (item.evidence || [])
            .map(
              (ev) => `<div class="evidence-box">
                <div class="evidence-quote">“${escapeHtml(ev.quote)}”</div>
                <div class="evidence-ref"><span>出处：<code>${escapeHtml(ev.ref)}</code></span></div>
              </div>`
            )
            .join("");

          return `<div class="lore-card">
            <div class="card-head">
              <div class="card-title">${escapeHtml(item.name || item.id)}</div>
              <span class="badge badge-subtle">${escapeHtml(item.kind || sub)}</span>
            </div>
            <p style="font-size:0.85rem;color:var(--text-dim)">${escapeHtml(item.summary || "")}</p>
            ${item.details ? `<p style="font-size:0.8rem;color:var(--text-faint)">${escapeHtml(item.details)}</p>` : ""}
            ${evidenceList ? `<div style="margin-top:0.4rem;">${evidenceList}</div>` : ""}
          </div>`;
        })
        .join("") || '<div class="empty-state">此分类暂无设定</div>'}</div>`;
    }
  }

  // Tab 3: Continuity
  function renderContinuity() {
    if (!state.continuity) return;
    const cstates = state.continuity.character_states || {};
    $("#cstate-asof").textContent = `as_of_chapter: ${cstates.as_of_chapter || "—"}`;

    const statesGrid = $("#character-states-grid");
    statesGrid.innerHTML = (cstates.states || [])
      .map((s) => `<div class="state-card">
        <div class="card-head">
          <div class="card-title">${escapeHtml(s.id)}</div>
          <span class="badge badge-subtle">活跃</span>
        </div>
        <div style="font-size:0.82rem;display:grid;gap:0.4rem;">
          <div><strong style="color:var(--text-faint)">📍 位置：</strong>${escapeHtml(s.location || "未知")}</div>
          <div><strong style="color:var(--text-faint)">🎒 携带：</strong>${escapeHtml((s.inventory || []).join("、") || "无")}</div>
          <div><strong style="color:var(--text-faint)">🧠 已知信息：</strong>${escapeHtml((s.knowledge || []).join("；") || "无")}</div>
          <div><strong style="color:var(--text-faint)">💭 心境：</strong>${escapeHtml(s.emotional || "平静")}</div>
          ${s.flags && s.flags.length ? `<div><strong style="color:var(--text-faint)">🚩 标志位：</strong>${escapeHtml(s.flags.join(", "))}</div>` : ""}
        </div>
      </div>`)
      .join("") || '<div class="empty-state">暂无角色状态</div>';

    const threadsTable = $("#open-threads-table-wrap");
    const threads = state.continuity.open_threads || [];
    threadsTable.innerHTML = `<table class="data-table">
      <thead><tr><th>线索/伏笔</th><th>状态</th><th>始于</th><th>核心监控</th><th>关键角色/关联</th></tr></thead>
      <tbody>${threads
        .map((t) => `<tr>
          <td><strong>${escapeHtml(t.title || t.id)}</strong><br><small style="color:var(--text-faint)">${escapeHtml(t.summary || "")}</small></td>
          <td><span class="badge ${t.status === "open" ? "badge-warning" : "badge-success"}">${escapeHtml(t.status || "open")}</span></td>
          <td><code>${escapeHtml(t.origin_chapter || "—")}</code></td>
          <td>${t.must_keep_on_continue ? '<span class="badge badge-danger">⚡ 续写必提</span>' : '<span style="color:var(--text-faint)">可选</span>'}</td>
          <td>${escapeHtml((t.entities || []).join("、") || "—")}</td>
        </tr>`)
        .join("")}</tbody>
    </table>`;

    $("#conflicts-card").innerHTML = renderMarkdown(state.continuity.conflicts || "暂无冲突记录。");
  }

  // Tab 4: Outline
  function renderOutline() {
    const treeEl = $("#outline-file-list");
    const files = (state.outline && state.outline.files) || [];
    treeEl.innerHTML = files
      .map((f) => `<button type="button" class="doc-item" data-file="${escapeHtml(f.file)}">${escapeHtml(f.file)}</button>`)
      .join("") || '<div class="empty-state">暂无大纲文件</div>';

    treeEl.querySelectorAll(".doc-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        treeEl.querySelectorAll(".doc-item").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const match = files.find((f) => f.file === btn.dataset.file);
        if (match) {
          $("#outline-doc-view").innerHTML = `<h1>${escapeHtml(match.file)}</h1>${renderMarkdown(match.content)}`;
        }
      });
    });

    if (files.length > 0) {
      treeEl.querySelector(".doc-item").click();
    }
  }

  // Tab 5: Audit & Quality
  async function runQuality() {
    const panel = $("#audit-results-panel");
    panel.innerHTML = '<div class="empty-state">⏳ 正在执行续写/改写质量门禁检查...</div>';
    try {
      const res = await fetch(`/api/books/${encodeURIComponent(state.bookId)}/quality`);
      const data = await res.json();
      const statusClass = data.ok ? "banner-pass" : "banner-fail";
      const icon = data.ok ? "✅" : "❌";

      panel.innerHTML = `
        <div class="report-banner ${statusClass}">
          <span>${icon} 质量门禁检查结果：${data.ok ? "全部通过 (PASS)" : "存在错误 (FAILED)"} · 章节 [${escapeHtml(data.chapter_id || "最新")}]</span>
          <span>${data.chars || 0} 字 / 目标 ${data.target_min || "—"}~${data.target_max || "—"}</span>
        </div>
        ${data.errors && data.errors.length ? `<div class="card" style="border-color:var(--danger);"><h4 style="color:var(--danger)">❌ 错误清单 (Errors)：</h4><ul>${data.errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul></div>` : ""}
        ${data.warnings && data.warnings.length ? `<div class="card" style="border-color:var(--warning);"><h4 style="color:var(--warning)">⚠️ 警告清单 (Warnings)：</h4><ul>${data.warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}</ul></div>` : ""}
        <div class="report-details-box">${escapeHtml(data.formatted || "")}</div>
      `;
    } catch (e) {
      panel.innerHTML = `<div class="report-banner banner-fail">运行失败: ${escapeHtml(e.message)}</div>`;
    }
  }

  async function runCheck() {
    const panel = $("#audit-results-panel");
    panel.innerHTML = '<div class="empty-state">⏳ 正在执行静态文本一致性与人名漂移检测...</div>';
    try {
      const res = await fetch(`/api/books/${encodeURIComponent(state.bookId)}/check`);
      const data = await res.json();
      const statusClass = data.ok ? (data.warnings && data.warnings.length ? "banner-warning" : "banner-pass") : "banner-fail";
      const icon = data.ok ? (data.warnings && data.warnings.length ? "⚠️" : "✅") : "❌";

      panel.innerHTML = `
        <div class="report-banner ${statusClass}">
          <span>${icon} 一致性检查结果：${data.ok ? "正典无漂移" : "检测到未入典实体"} · 扫描 ${data.chapters_scanned || 0} 章</span>
          <span>正典白名单: ${data.allowlist_size || 0} 词条</span>
        </div>
        ${data.errors && data.errors.length ? `<div class="card" style="border-color:var(--danger);"><h4 style="color:var(--danger)">❌ 人名漂移报警 (Name Drift Errors)：</h4><ul>${data.errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul></div>` : ""}
        ${data.warnings && data.warnings.length ? `<div class="card" style="border-color:var(--warning);"><h4 style="color:var(--warning)">⚠️ 状态/伏笔警告 (Warnings)：</h4><ul>${data.warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("")}</ul></div>` : ""}
        <div class="report-details-box">${escapeHtml(data.formatted || "")}</div>
      `;
    } catch (e) {
      panel.innerHTML = `<div class="report-banner banner-fail">运行失败: ${escapeHtml(e.message)}</div>`;
    }
  }

  async function runValidate() {
    const panel = $("#audit-results-panel");
    panel.innerHTML = '<div class="empty-state">⏳ 正在校验目录规范与 Schema 合规性...</div>';
    try {
      const res = await fetch(`/api/books/${encodeURIComponent(state.bookId)}/validate`);
      const data = await res.json();
      const statusClass = data.ok ? "banner-pass" : "banner-fail";
      const icon = data.ok ? "✅" : "❌";

      panel.innerHTML = `
        <div class="report-banner ${statusClass}">
          <span>${icon} 00–09 规范合规性校验：${data.ok ? "结构完全合法 (VALID)" : "存在不合规项"}</span>
        </div>
        ${data.errors && data.errors.length ? `<div class="card" style="border-color:var(--danger);"><h4 style="color:var(--danger)">❌ 违规清单：</h4><ul>${data.errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul></div>` : '<div class="card"><p style="color:var(--success)">全部 00–09 目录与 YAML Schema 校验通过！</p></div>'}
      `;
    } catch (e) {
      panel.innerHTML = `<div class="report-banner banner-fail">运行失败: ${escapeHtml(e.message)}</div>`;
    }
  }

  // Tab 6: Context Packer
  function initContextTab() {
    const chapSelect = $("#context-chapter-select");
    const chapters = [];
    if (state.toc && state.toc.volumes) {
      for (const v of state.toc.volumes) {
        for (const ch of v.chapters || []) {
          chapters.push({ id: ch.file.replace(/\.md$/i, ""), title: `${v.kind_label || v.kind}: ${ch.title}` });
        }
      }
    }
    chapSelect.innerHTML =
      '<option value="">(最新章节 / 全局)</option>' +
      chapters.map((c) => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.title)} (${escapeHtml(c.id)})</option>`).join("");
  }

  async function generateContext() {
    const chap = $("#context-chapter-select").value;
    const maxChars = $("#context-max-chars").value;
    $("#context-output").textContent = "⏳ 正在按 AGENTS §8 优先级装配上下文...";

    try {
      const res = await fetch(`/api/books/${encodeURIComponent(state.bookId)}/context?chapter=${encodeURIComponent(chap)}&max_chars=${encodeURIComponent(maxChars)}`);
      const data = await res.json();

      $("#context-stats-badge").textContent = `${data.chars || 0} 字符 / ${data.lines || 0} 行`;
      $("#context-output").textContent = data.pack || "空";

      if (data.warnings && data.warnings.length) {
        showToast("注意: " + data.warnings.join("; "));
      }
    } catch (e) {
      showToast("组装失败: " + e.message);
    }
  }

  // Tab 7: Export
  function initExportTab() {
    const volSelect = $("#export-epub-vol");
    if (state.toc && state.toc.volumes) {
      volSelect.innerHTML = state.toc.volumes
        .map((v) => `<option value="${escapeHtml(v.id)}">${escapeHtml(v.title || v.id)} (${escapeHtml(v.kind_label || v.kind)})</option>`)
        .join("");
    }
  }

  function downloadEpub() {
    const vol = $("#export-epub-vol").value || "original";
    window.location.href = `/api/download/${encodeURIComponent(state.bookId)}/epub/${encodeURIComponent(vol)}`;
    showToast("正在开始下载 EPUB...");
  }

  function downloadSt(type) {
    window.location.href = `/api/download/${encodeURIComponent(state.bookId)}/st/${encodeURIComponent(type)}`;
    showToast(`正在开始下载 SillyTavern ${type} 资产...`);
  }

  // Tab 8: Sessions
  function renderSessions() {
    const treeEl = $("#sessions-file-list");
    const sessions = (state.sessions && state.sessions.sessions) || [];
    treeEl.innerHTML = sessions
      .map((s) => `<button type="button" class="doc-item" data-file="${escapeHtml(s.file)}">${escapeHtml(s.file)}</button>`)
      .join("") || '<div class="empty-state">暂无会话日志</div>';

    treeEl.querySelectorAll(".doc-item").forEach((btn) => {
      btn.addEventListener("click", () => {
        treeEl.querySelectorAll(".doc-item").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const match = sessions.find((s) => s.file === btn.dataset.file);
        if (match) {
          $("#session-doc-view").innerHTML = `<h1>${escapeHtml(match.file)}</h1>${renderMarkdown(match.content)}`;
        }
      });
    });

    if (sessions.length > 0) {
      treeEl.querySelector(".doc-item").click();
    }
  }

  // Bind Events
  function bindEvents() {
    $("#book-select").addEventListener("change", (e) => selectBook(e.target.value));
    $("#btn-refresh").addEventListener("click", () => selectBook(state.bookId));

    // Theme buttons
    $$(".theme-opt").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.theme = btn.dataset.theme;
        applyTheme();
      });
    });

    // Font size
    $("#btn-font-dec").addEventListener("click", () => {
      state.font -= 1;
      applyFont();
    });
    $("#btn-font-inc").addEventListener("click", () => {
      state.font += 1;
      applyFont();
    });

    // Main Tabs
    $$(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => switchTab(btn.dataset.tab));
    });

    // Sub-nav for Canon
    $$(".sub-pill").forEach((btn) => {
      btn.addEventListener("click", () => {
        $$(".sub-pill").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.canonSubTab = btn.dataset.canon;
        renderCanon();
      });
    });

    // Manuscript Filters
    $("#chapter-search").addEventListener("input", (e) => {
      state.chapterSearch = e.target.value;
      renderManuscriptTree();
    });
    $$(".vol-filter-pills .pill-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        $$(".vol-filter-pills .pill-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.volFilter = btn.dataset.kind;
        renderManuscriptTree();
      });
    });

    // Audit buttons
    $("#btn-run-quality").addEventListener("click", runQuality);
    $("#btn-run-check").addEventListener("click", runCheck);
    $("#btn-run-validate").addEventListener("click", runValidate);

    // Context Packer
    $("#context-max-chars").addEventListener("input", (e) => {
      $("#max-chars-display").textContent = e.target.value;
    });
    $("#btn-gen-context").addEventListener("click", generateContext);
    $("#btn-copy-context").addEventListener("click", () => {
      const text = $("#context-output").textContent;
      navigator.clipboard.writeText(text).then(() => showToast("✅ 上下文包已复制到剪贴板"));
    });

    // Export buttons
    $("#btn-export-epub").addEventListener("click", downloadEpub);
    $("#btn-export-st-lore").addEventListener("click", () => downloadSt("lore"));
    $("#btn-export-st-writer").addEventListener("click", () => downloadSt("writer"));

    // New Book Modal
    $("#btn-open-new-book").addEventListener("click", () => {
      $("#new-book-modal").classList.remove("hidden");
    });
    $("#btn-close-modal").addEventListener("click", () => {
      $("#new-book-modal").classList.add("hidden");
    });
    $("#btn-cancel-modal").addEventListener("click", () => {
      $("#new-book-modal").classList.add("hidden");
    });
    $("#new-book-form").addEventListener("submit", async (e) => {
      e.preventDefault();
      const id = $("#new-book-id").value.trim();
      const title = $("#new-book-title").value.trim();
      if (!id) return;

      try {
        const res = await fetch("/api/books", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id, title }),
        });
        const data = await res.json();
        if (data.ok) {
          $("#new-book-modal").classList.add("hidden");
          $("#new-book-form").reset();
          showToast(`✅ 新书《${title || id}》创建成功！`);
          await loadBooks(id);
        } else {
          showToast("创建失败: " + (data.error || "未知错误"));
        }
      } catch (err) {
        showToast("请求失败: " + err.message);
      }
    });
  }

  // Initialize
  applyTheme();
  applyFont();
  bindEvents();
  loadBooks();
})();
