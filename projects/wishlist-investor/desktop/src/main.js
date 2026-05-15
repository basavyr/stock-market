const { invoke } = window.__TAURI__.core;

const $ = (id) => document.getElementById(id);

const LS = {
  wishlist: "wi_desktop_wishlist",
  settings: "wi_desktop_settings",
};

function formatMoney(v) {
  const n = Number(v || 0);
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function escapeHtml(s) {
  return String(s || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function parseCsvLine(line) {
  const out = [];
  let cur = "";
  let inQ = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      inQ = !inQ;
      continue;
    }
    if (ch === "," && !inQ) {
      out.push(cur);
      cur = "";
    } else {
      cur += ch;
    }
  }
  out.push(cur);
  return out.map((s) => s.trim());
}

function extractPortfolioSymbols(csvText) {
  const lines = String(csvText || "")
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter(Boolean);
  if (!lines.length) return [];

  let headerIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes("Symbol") && lines[i].includes("Quantity")) {
      headerIdx = i;
      break;
    }
  }
  if (headerIdx === -1) return [];

  const header = parseCsvLine(lines[headerIdx]);
  const idxSym = header.findIndex((x) => x.replaceAll('"', "").trim() === "Symbol");
  const idxQty = header.findIndex((x) => x.replaceAll('"', "").trim() === "Quantity");
  if (idxSym === -1) return [];

  const out = [];
  const seen = new Set();
  for (let i = headerIdx + 1; i < lines.length; i++) {
    const row = parseCsvLine(lines[i]);
    const sym = String(row[idxSym] || "")
      .replaceAll('"', "")
      .trim()
      .toUpperCase();
    if (!sym) continue;
    if (idxQty !== -1) {
      const qty = Number(String(row[idxQty] || "0").replaceAll(",", ""));
      if (!qty) continue;
    }
    if (!/^[A-Z0-9.\-]{1,12}$/.test(sym)) continue;
    if (seen.has(sym)) continue;
    seen.add(sym);
    out.push(sym);
    if (out.length >= 120) break;
  }
  return out;
}

async function generate() {
  const file = $("portfolioFile").files?.[0];
  if (!file) throw new Error("Upload Report-With-Cash.csv first");

  const tickers = getWishlist();
  if (!tickers.length) throw new Error("Enter at least one wishlist ticker");

  const settings = {
    whole_shares: $("optWholeShares").checked,
    min_order_usd: Number($("optMinOrder").value || 25),
    price_tilt: Number($("optPriceTilt").value || 0.2),
    score_temperature: Number($("optScoreTemp").value || 10),
    max_new_alloc_pct: Number($("optMaxNewAlloc").value || 40) / 100,
  };

  const portfolioCsv = await file.text();
  const res = await invoke("generate_report", {
    req: { portfolio_csv: portfolioCsv, wishlist: tickers, settings },
  });
  if (!res.ok) throw new Error(res.error || "Generate failed");
  return res.report;
}

let prefetchTimer = null;
let prefetchInFlight = false;
let prefetchPending = null;

function prefetchQuotes(tickers) {
  const uniq = Array.from(new Set((tickers || []).map((t) => String(t || "").trim().toUpperCase()).filter(Boolean)));
  if (!uniq.length) return;

  prefetchPending = uniq;
  if (prefetchTimer) clearTimeout(prefetchTimer);
  prefetchTimer = setTimeout(async () => {
    if (prefetchInFlight) return;
    const cur = prefetchPending;
    prefetchPending = null;
    if (!cur || !cur.length) return;

    prefetchInFlight = true;
    try {
      await invoke("prefetch_quotes", { req: { tickers: cur } });
    } catch {
      // Best-effort warming; ignore errors.
    } finally {
      prefetchInFlight = false;
      if (prefetchPending && prefetchPending.length) prefetchQuotes(prefetchPending);
    }
  }, 250);
}

function loadJson(key) {
  const raw = localStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function saveJson(key, v) {
  localStorage.setItem(key, JSON.stringify(v));
}

function getWishlist() {
  const w = loadJson(LS.wishlist);
  if (Array.isArray(w)) return w;
  if (w && Array.isArray(w.tickers)) return w.tickers;
  return [];
}

function setWishlist(tickers) {
  const out = [];
  const seen = new Set();
  tickers.forEach((t) => {
    const x = String(t || "").trim().toUpperCase();
    if (!x) return;
    if (!/^[A-Z0-9.\-]{1,12}$/.test(x)) return;
    if (seen.has(x)) return;
    seen.add(x);
    out.push(x);
  });
  saveJson(LS.wishlist, { tickers: out });
  renderWishlistChips();
  prefetchQuotes(out);
}

function renderWishlistChips() {
  const wrap = $("wishlistChips");
  if (!wrap) return;
  wrap.innerHTML = "";
  getWishlist().forEach((t) => {
    const chip = document.createElement("div");
    chip.className = "chip";
    const code = document.createElement("code");
    code.textContent = t;
    const x = document.createElement("button");
    x.type = "button";
    x.title = "Remove";
    x.textContent = "×";
    x.addEventListener("click", () => setWishlist(getWishlist().filter((z) => z !== t)));
    chip.appendChild(code);
    chip.appendChild(x);
    wrap.appendChild(chip);
  });
}

const TICKERS_DB = [
  { ticker: "VALE", name: "Vale S.A.", exchange: "NYSE" },
  { ticker: "DUK", name: "Duke Energy", exchange: "NYSE" },
  { ticker: "SO", name: "Southern Company", exchange: "NYSE" },
  { ticker: "BX", name: "Blackstone", exchange: "NYSE" },
  { ticker: "OKE", name: "ONEOK, Inc.", exchange: "NYSE" },
  { ticker: "PFE", name: "Pfizer Inc", exchange: "NYSE" },
  { ticker: "XOM", name: "Exxon Mobil", exchange: "NYSE" },
  { ticker: "CVX", name: "Chevron", exchange: "NYSE" },
  { ticker: "MRK", name: "Merck & Co", exchange: "NYSE" },
  { ticker: "MU", name: "Micron Technology", exchange: "NASDAQ" },
  { ticker: "GEV", name: "GE Vernova Inc", exchange: "NYSE" },
  { ticker: "AEP", name: "American Electric Power", exchange: "NASDAQ" },
  { ticker: "VST", name: "Vistra Corp", exchange: "NYSE" },
  { ticker: "AVGO", name: "Broadcom Inc", exchange: "NASDAQ" },
];

function setSuggest(items) {
  const suggest = $("suggest");
  if (!suggest) return;
  suggest.innerHTML = "";
  if (!items || !items.length) return;
  items.slice(0, 8).forEach((it) => {
    const d = document.createElement("div");
    d.className = "suggest__item";
    d.innerHTML = `
      <div class="suggest__top">
        <div class="suggest__ticker">${it.ticker}</div>
        <div class="muted">${it.exchange || ""}</div>
      </div>
      <div class="suggest__name">${it.name || ""}</div>
    `;
    d.addEventListener("click", () => {
      setWishlist([...getWishlist(), it.ticker]);
      $("tickerSearch").value = "";
      setSuggest([]);
    });
    suggest.appendChild(d);
  });
}

function searchTickers(q) {
  const s = String(q || "").trim().toUpperCase();
  if (!s) return [];
  const res = [];
  for (let i = 0; i < TICKERS_DB.length; i++) {
    const it = TICKERS_DB[i];
    if (it.ticker.includes(s) || (it.name || "").toUpperCase().includes(s)) {
      res.push(it);
      if (res.length >= 8) break;
    }
  }
  return res;
}

function addTickerFromInput() {
  const inp = $("tickerSearch");
  const v = String(inp.value || "").trim().toUpperCase();
  if (!v) return;
  if (!/^[A-Z0-9.\-]{1,12}$/.test(v)) return;
  setWishlist([...getWishlist(), v]);
  inp.value = "";
  setSuggest([]);
}

let suggestHideTimer = null;

function maybeHideSuggest() {
  if (suggestHideTimer) clearTimeout(suggestHideTimer);
  suggestHideTimer = setTimeout(() => setSuggest([]), 150);
}

function loadSettings() {
  return loadJson(LS.settings) || {};
}

function persistSettings() {
  const settings = {
    whole_shares: $("optWholeShares").checked,
    min_order_usd: Number($("optMinOrder").value || 25),
    price_tilt: Number($("optPriceTilt").value || 0.2),
    score_temperature: Number($("optScoreTemp").value || 10),
    max_new_alloc_pct: Number($("optMaxNewAlloc").value || 40) / 100,
  };
  saveJson(LS.settings, settings);
  return settings;
}

function render(report) {
  const p = report.portfolio || {};
  const perf = report.perf || {};
  $("meta").innerHTML = `
    <div class="meta"><div class="meta__k">Generated</div><div class="meta__v">${report.generated_at || "-"}</div></div>
    <div class="meta"><div class="meta__k">Cash</div><div class="meta__v">$${formatMoney(p.cash)}</div></div>
    <div class="meta"><div class="meta__k">Investable</div><div class="meta__v">$${formatMoney(p.investable_cash)}</div></div>
    <div class="meta"><div class="meta__k">Holdings Value</div><div class="meta__v">$${formatMoney(p.holdings_total_value)}</div></div>
    <div class="meta"><div class="meta__k">Quotes ms</div><div class="meta__v">${perf.quotes_ms ?? "-"}</div></div>
    <div class="meta"><div class="meta__k">Total ms</div><div class="meta__v">${perf.total_ms ?? "-"}</div></div>
  `;

  const tbody = $("recBody");
  tbody.innerHTML = "";
  const recs = Array.isArray(report.recommendations) ? report.recommendations : [];
  recs
    .slice()
    .sort((a, b) => (b.recommended_amount || 0) - (a.recommended_amount || 0))
    .forEach((r) => {
      const tr = document.createElement("tr");

      const held = (r.current_holding_value || 0) > 0 ? "Yes" : "No";
      const w = ((Number(r.current_weight || 0) * 100) || 0).toFixed(1);

      const why = document.createElement("details");
      const whySum = document.createElement("summary");
      whySum.textContent = "Open";
      why.appendChild(whySum);
      const whyUl = document.createElement("ul");

      if (r.score != null) {
        const li = document.createElement("li");
        li.textContent = `Score: ${r.score}`;
        whyUl.appendChild(li);

        if (r.score_components) {
          const c = r.score_components;
          const parts = [
            ["Quality", c.quality],
            ["Growth", c.growth],
            ["Value", c.value],
            ["Income", c.income],
            ["Risk", c.risk],
            ["Price", c.afford],
            ["Concentration", c.concentration],
          ]
            .filter((x) => x[1] != null)
            .map((x) => `${x[0]} ${Number(x[1]).toFixed(1)}`)
            .join(" | ");

          if (parts) {
            const li2 = document.createElement("li");
            li2.textContent = `Score components: ${parts}`;
            whyUl.appendChild(li2);
          }
        }

        if (Array.isArray(r.score_notes) && r.score_notes.length) {
          r.score_notes.slice(0, 2).forEach((n) => {
            const li3 = document.createElement("li");
            li3.textContent = String(n);
            whyUl.appendChild(li3);
          });
        }
      }

      (r.why || []).forEach((x) => {
        const li = document.createElement("li");
        li.textContent = String(x);
        whyUl.appendChild(li);
      });
      why.appendChild(whyUl);

      const keep = document.createElement("details");
      const keepSum = document.createElement("summary");
      keepSum.textContent = "Open";
      keep.appendChild(keepSum);
      const keepUl = document.createElement("ul");
      (r.keep_in_mind || []).forEach((x) => {
        const li = document.createElement("li");
        li.textContent = String(x);
        keepUl.appendChild(li);
      });
      keep.appendChild(keepUl);

      tr.innerHTML = `
        <td><code>${escapeHtml(r.symbol || "")}</code></td>
        <td>${r.price ? `$${escapeHtml(formatMoney(r.price))}` : "-"}</td>
        <td>${r.score != null ? escapeHtml(String(r.score)) : "-"}</td>
        <td>${held}</td>
        <td>${escapeHtml(w)}%</td>
        <td>$${escapeHtml(formatMoney(r.recommended_amount))}</td>
        <td>${r.recommended_shares_est ? escapeHtml(String(r.recommended_shares_est)) : "-"}</td>
      `;

      const tdWhy = document.createElement("td");
      tdWhy.appendChild(why);
      tr.appendChild(tdWhy);

      const tdKeep = document.createElement("td");
      tdKeep.appendChild(keep);
      tr.appendChild(tdKeep);

      tbody.appendChild(tr);
    });
}

window.addEventListener("DOMContentLoaded", () => {
  // bootstrap wishlist UI
  const hint = $("tickerHint");
  if (hint) hint.textContent = "Tip: type any ticker and press Enter.";
  renderWishlistChips();

  // best-effort cache warm on app open
  prefetchQuotes(getWishlist());

  const q = $("tickerSearch");
  q.addEventListener("input", () => setSuggest(searchTickers(q.value)));
  q.addEventListener("blur", () => maybeHideSuggest());
  q.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTickerFromInput();
    }
  });

  // restore settings
  const s = loadSettings();
  if (s) {
    if (s.whole_shares != null) $("optWholeShares").checked = !!s.whole_shares;
    if (s.min_order_usd != null) $("optMinOrder").value = String(s.min_order_usd);
    if (s.price_tilt != null) $("optPriceTilt").value = String(s.price_tilt);
    if (s.score_temperature != null) $("optScoreTemp").value = String(s.score_temperature);
    if (s.max_new_alloc_pct != null) $("optMaxNewAlloc").value = String(Number(s.max_new_alloc_pct) * 100);
  }

  const pf = $("portfolioFile");
  if (pf) {
    pf.addEventListener("change", async () => {
      const f = pf.files?.[0];
      if (!f) return;
      try {
        const text = await f.text();
        const syms = extractPortfolioSymbols(text);
        prefetchQuotes([...getWishlist(), ...syms]);
      } catch {
        // ignore
      }
    });
  }

  $("btnGenerate").addEventListener("click", async () => {
    $("status").textContent = "Generating...";
    try {
      persistSettings();
      const report = await generate();
      render(report);
      $("status").textContent = "Done.";
    } catch (e) {
      $("status").textContent = `Failed: ${e}`;
    }
  });
});
