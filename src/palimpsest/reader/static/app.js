(() => {
  const $ = (sel) => document.querySelector(sel);
  const FONT_MIN = 14;
  const FONT_MAX = 28;

  const state = {
    books: [],
    filter: "",
    kind: "all",
    bookId: null,
    toc: null,
    font: Number(localStorage.getItem("ps-font") || 18),
    theme: localStorage.getItem("ps-theme") || "dark",
  };

  function applyTheme() {
    document.documentElement.classList.toggle("light", state.theme === "light");
    document.documentElement.dataset.theme = state.theme;
    localStorage.setItem("ps-theme", state.theme);
    document.querySelectorAll(".theme-opt").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.theme === state.theme);
    });
  }

  function applyFont() {
    state.font = Math.min(FONT_MAX, Math.max(FONT_MIN, state.font));
    document.documentElement.style.setProperty("--font-size", `${state.font}px`);
    $("#font-label").textContent = String(state.font);
    localStorage.setItem("ps-font", String(state.font));
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderMarkdown(md) {
    const lines = md.replace(/\r\n/g, "\n").split("\n");
    const html = [];
    let para = [];
    const flush = () => {
      if (!para.length) return;
      const text = para.join("\n").trim();
      if (text) html.push(`<p>${inline(text).replace(/\n/g, "<br>")}</p>`);
      para = [];
    };
    const inline = (t) =>
      escapeHtml(t)
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>");
    for (const raw of lines) {
      if (raw.startsWith("# ")) {
        flush();
        html.push(`<h1>${inline(raw.slice(2))}</h1>`);
      } else if (raw.startsWith("## ")) {
        flush();
        html.push(`<h2>${inline(raw.slice(3))}</h2>`);
      } else if (raw.startsWith("---")) {
        flush();
        html.push("<hr>");
      } else if (raw.trim() === "") {
        flush();
      } else {
        para.push(raw);
      }
    }
    flush();
    return html.join("");
  }

  function visibleBooks() {
    const q = state.filter.trim().toLowerCase();
    return state.books.filter((b) => {
      if (q && !`${b.title} ${b.id}`.toLowerCase().includes(q)) return false;
      if (state.kind === "all") return true;
      return (b.volumes || []).some((v) => v.kind === state.kind && v.chapter_count > 0);
    });
  }

  function renderBooks() {
    const nav = $("#book-list");
    const books = visibleBooks();
    nav.innerHTML = books
      .map((b) => {
        const counts = (b.volumes || [])
          .map((v) => `${v.kind_label || v.kind} ${v.chapter_count}`)
          .join(" · ");
        return `<button type="button" class="book-item${b.id === state.bookId ? " active" : ""}" data-id="${escapeHtml(b.id)}">
          <span class="title">${escapeHtml(b.title)}</span>
          <span class="meta">${escapeHtml(b.id)} · ${escapeHtml(counts || "无章节")}</span>
        </button>`;
      })
      .join("") || `<p class="empty" style="padding:0.8rem;color:var(--text-faint)">没有匹配的书。</p>`;
    nav.querySelectorAll(".book-item").forEach((btn) => {
      btn.addEventListener("click", () => openBook(btn.dataset.id));
    });
  }

  function renderToc() {
    const panel = $("#toc-panel");
    const list = $("#chapter-list");
    if (!state.toc) {
      panel.classList.add("hidden");
      $("#book-list").style.display = "";
      return;
    }
    panel.classList.remove("hidden");
    $("#book-list").style.display = "none";
    $("#toc-title").textContent = state.toc.title;
    const blocks = [];
    for (const vol of state.toc.volumes || []) {
      if (!vol.chapters || !vol.chapters.length) continue;
      if (state.kind !== "all" && vol.kind !== state.kind) continue;
      blocks.push(`<div class="vol-head" style="padding:0.4rem 0.55rem;color:var(--text-faint);font-size:0.75rem">
        <span class="kind ${escapeHtml(vol.kind)}">${escapeHtml(vol.kind_label || vol.kind)}</span>
        ${escapeHtml(vol.title)}
      </div>`);
      for (const ch of vol.chapters) {
        blocks.push(`<button type="button" class="chapter-item" data-vol="${escapeHtml(vol.id)}" data-file="${escapeHtml(ch.file)}">${escapeHtml(ch.title)}</button>`);
      }
    }
    list.innerHTML = blocks.join("") || `<p style="padding:0.8rem;color:var(--text-faint)">此筛选下无章节。</p>`;
    list.querySelectorAll(".chapter-item").forEach((btn) => {
      btn.addEventListener("click", () => openChapter(btn.dataset.vol, btn.dataset.file, btn));
    });
  }

  async function loadBooks() {
    const res = await fetch("/api/books");
    const data = await res.json();
    state.books = data.books || [];
    renderBooks();
  }

  async function openBook(bookId) {
    state.bookId = bookId;
    const res = await fetch(`/api/books/${encodeURIComponent(bookId)}/toc`);
    state.toc = await res.json();
    const url = new URL(window.location.href);
    url.searchParams.set("book", bookId);
    history.replaceState({ bookId }, "", url.pathname + url.search);
    renderBooks();
    renderToc();
  }

  async function openChapter(volumeId, file, btn) {
    document.querySelectorAll(".chapter-item").forEach((el) => el.classList.remove("active"));
    if (btn) btn.classList.add("active");
    const res = await fetch(
      `/api/books/${encodeURIComponent(state.bookId)}/chapters/${encodeURIComponent(volumeId)}/${encodeURIComponent(file)}`
    );
    const data = await res.json();
    const kind = (state.toc.volumes || []).find((v) => v.id === volumeId);
    $("#article").innerHTML = `<div class="vol-tag">${escapeHtml((kind && kind.kind_label) || volumeId)} · ${escapeHtml(file)}</div>${renderMarkdown(data.markdown || "")}`;
    $("#reader").scrollTop = 0;
  }

  function bind() {
    $("#book-search").addEventListener("input", (e) => {
      state.filter = e.target.value;
      renderBooks();
    });
    document.querySelectorAll(".track-filter-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.kind = btn.dataset.kind;
        document.querySelectorAll(".track-filter-tab").forEach((b) => b.classList.toggle("active", b === btn));
        renderBooks();
        renderToc();
      });
    });
    $("#btn-back").addEventListener("click", () => {
      state.bookId = null;
      state.toc = null;
      const url = new URL(window.location.href);
      url.searchParams.delete("book");
      history.replaceState({}, "", url.pathname + url.search);
      renderBooks();
      renderToc();
    });
    $("#btn-refresh").addEventListener("click", loadBooks);
    document.querySelectorAll(".theme-opt").forEach((btn) => {
      btn.addEventListener("click", () => {
        state.theme = btn.dataset.theme;
        applyTheme();
      });
    });
    $("#font-down").addEventListener("click", () => {
      state.font -= 1;
      applyFont();
    });
    $("#font-up").addEventListener("click", () => {
      state.font += 1;
      applyFont();
    });
  }

  applyTheme();
  applyFont();
  bind();
  loadBooks().then(() => {
    const book = new URL(window.location.href).searchParams.get("book");
    if (book) openBook(book);
  });
})();
