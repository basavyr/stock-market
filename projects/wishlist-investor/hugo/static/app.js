(() => {
  const LS = {
    portfolioCsv: "wi_portfolio_csv",
    portfolioParsed: "wi_portfolio_parsed",
    wishlist: "wi_wishlist",
    report: "wi_report",
  };

  const el = (id) => document.getElementById(id);
  const viewWizard = el("viewWizard");
  const viewReport = el("viewReport");

  const portfolioFile = el("portfolioFile");
  const portfolioSummary = el("portfolioSummary");
  const btnDownloadPortfolio = el("btnDownloadPortfolio");

  const tickerSearch = el("tickerSearch");
  const tickerHint = el("tickerHint");
  const suggest = el("suggest");
  const wishlistChips = el("wishlistChips");
  const btnDownloadWishlist = el("btnDownloadWishlist");

  const btnGenerate = el("btnGenerate");
  const genStatus = el("genStatus");

  const optWholeShares = el("optWholeShares");
  const optMinOrder = el("optMinOrder");
  const optPriceTilt = el("optPriceTilt");
  const optScoreTemp = el("optScoreTemp");
  const optMaxNewAlloc = el("optMaxNewAlloc");

  const reportFile = el("reportFile");
  const reportFile2 = el("reportFile2");
  const reportLoadStatus = el("reportLoadStatus");

  const btnReset = el("btnReset");
  const btnExport = el("btnExport");
  const btnEdit = el("btnEdit");

  const reportMeta = el("reportMeta");
  const recBody = el("recBody");

  const state = {
    tickersDb: [],
  };

  function dl(filename, text, mime) {
    const blob = new Blob([text], { type: mime || "application/octet-stream" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 200);
  }

  function loadJsonLS(key) {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  function saveJsonLS(key, v) {
    localStorage.setItem(key, JSON.stringify(v));
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

  function parsePortfolioCsv(text) {
    const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean);
    let cash = null;
    let cashRaw = {};
    if (lines[0] && lines[0].includes("NetCashBalance")) {
      const hdr = parseCsvLine(lines[0]);
      const row = parseCsvLine(lines[1] || "");
      hdr.forEach((k, idx) => {
        cashRaw[k] = Number(row[idx] || 0);
      });
      cash = Number(cashRaw["NetCashBalanceSLB"] || 0);
    }

    let headerIdx = -1;
    for (let i = 0; i < lines.length; i++) {
      if (lines[i].includes("Symbol") && lines[i].includes("Quantity")) {
        headerIdx = i;
        break;
      }
    }
    if (headerIdx === -1) throw new Error("Could not find holdings header row");

    const header = parseCsvLine(lines[headerIdx]);
    const holdings = [];
    for (let i = headerIdx + 1; i < lines.length; i++) {
      const row = parseCsvLine(lines[i]);
      const o = {};
      header.forEach((k, idx) => (o[k] = row[idx]));
      if (!o.Symbol) continue;
      const qty = Number(o.Quantity || 0);
      if (!qty) continue;
      holdings.push({
        symbol: String(o.Symbol).trim(),
        description: String(o.Description || "").trim(),
        quantity: qty,
        cost_basis_price: Number(o.CostBasisPrice || 0),
        fifo_pnl_unrealized: Number(o.FifoPnlUnrealized || 0),
      });
    }

    return { cash: cash ?? 0, cashRaw, holdings };
  }

  function renderPortfolioSummary(p) {
    const cash = (p.cash ?? 0).toFixed(2);
    portfolioSummary.textContent = `Cash: $${cash} | Holdings: ${p.holdings.length}`;
  }

  function getWishlist() {
    const w = loadJsonLS(LS.wishlist);
    if (Array.isArray(w)) return w;
    if (w && Array.isArray(w.tickers)) return w.tickers;
    return [];
  }

  function setWishlist(tickers) {
    const dedup = [];
    const seen = new Set();
    tickers.forEach((t) => {
      const x = String(t || "").trim().toUpperCase();
      if (!x) return;
      if (seen.has(x)) return;
      seen.add(x);
      dedup.push(x);
    });
    saveJsonLS(LS.wishlist, { tickers: dedup });
    btnDownloadWishlist.disabled = dedup.length === 0;
    if (btnGenerate) btnGenerate.disabled = dedup.length === 0 || !localStorage.getItem(LS.portfolioCsv);
    renderWishlistChips();
  }

  function renderWishlistChips() {
    const tickers = getWishlist();
    wishlistChips.innerHTML = "";
    tickers.forEach((t) => {
      const chip = document.createElement("div");
      chip.className = "chip";
      const code = document.createElement("code");
      code.textContent = t;
      const x = document.createElement("button");
      x.type = "button";
      x.title = "Remove";
      x.textContent = "×";
      x.addEventListener("click", () => {
        setWishlist(getWishlist().filter((z) => z !== t));
      });
      chip.appendChild(code);
      chip.appendChild(x);
      wishlistChips.appendChild(chip);
    });
  }

  function formatMoney(v) {
    const n = Number(v || 0);
    return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  function metaBox(k, v) {
    const d = document.createElement("div");
    d.className = "meta";
    const kk = document.createElement("div");
    kk.className = "meta__k";
    kk.textContent = k;
    const vv = document.createElement("div");
    vv.className = "meta__v";
    vv.textContent = v;
    d.appendChild(kk);
    d.appendChild(vv);
    return d;
  }

  function renderReport(report) {
    reportMeta.innerHTML = "";
    const p = report.portfolio || {};
    reportMeta.appendChild(metaBox("Generated", report.generated_at || "-"));
    reportMeta.appendChild(metaBox("Cash", `$${formatMoney(p.cash)}`));
    reportMeta.appendChild(metaBox("Investable Cash", `$${formatMoney(p.investable_cash)}`));
    reportMeta.appendChild(metaBox("Holdings Value", `$${formatMoney(p.holdings_total_value)}`));

    recBody.innerHTML = "";
    const recs = Array.isArray(report.recommendations) ? report.recommendations : [];
    recs.forEach((r) => {
      const tr = document.createElement("tr");
      const held = (r.current_holding_value || 0) > 0 ? "Yes" : "No";
      const w = Number(r.current_weight || 0) * 100;

      const why = document.createElement("details");
      const s1 = document.createElement("summary");
      s1.textContent = "Open";
      why.appendChild(s1);
      const ul1 = document.createElement("ul");

      if (r.score != null) {
        const li = document.createElement("li");
        li.textContent = `Score: ${r.score}`;
        ul1.appendChild(li);

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
            ul1.appendChild(li2);
          }
        }

        if (Array.isArray(r.score_notes) && r.score_notes.length) {
          r.score_notes.slice(0, 2).forEach((n) => {
            const li3 = document.createElement("li");
            li3.textContent = String(n);
            ul1.appendChild(li3);
          });
        }
      }
      (r.why || []).forEach((x) => {
        const li = document.createElement("li");
        li.textContent = String(x);
        ul1.appendChild(li);
      });
      why.appendChild(ul1);

      const keep = document.createElement("details");
      const s2 = document.createElement("summary");
      s2.textContent = "Open";
      keep.appendChild(s2);
      const ul2 = document.createElement("ul");
      (r.keep_in_mind || []).forEach((x) => {
        const li = document.createElement("li");
        li.textContent = String(x);
        ul2.appendChild(li);
      });
      keep.appendChild(ul2);

      const cells = [
        `<code>${r.symbol || ""}</code>`,
        r.price ? `$${formatMoney(r.price)}` : "-",
        r.score != null ? String(r.score) : "-",
        held,
        `${w.toFixed(1)}%`,
        `$${formatMoney(r.recommended_amount)}`,
        r.recommended_shares_est ? String(r.recommended_shares_est) : "-",
      ];

      cells.forEach((html) => {
        const td = document.createElement("td");
        td.innerHTML = html;
        tr.appendChild(td);
      });

      const tdWhy = document.createElement("td");
      tdWhy.appendChild(why);
      tr.appendChild(tdWhy);

      const tdKeep = document.createElement("td");
      tdKeep.appendChild(keep);
      tr.appendChild(tdKeep);

      recBody.appendChild(tr);
    });
  }

  function showWizard() {
    viewWizard.hidden = false;
    viewReport.hidden = true;
  }

  function showReport() {
    viewWizard.hidden = true;
    viewReport.hidden = false;
  }

  function backendBase() {
    return localStorage.getItem("wi_backend_base") || "http://127.0.0.1:8750";
  }

  async function generateReportViaBackend() {
    const portfolioCsv = localStorage.getItem(LS.portfolioCsv);
    const wishlist = getWishlist();
    if (!portfolioCsv) throw new Error("Missing portfolio CSV");
    if (!wishlist.length) throw new Error("Missing wishlist tickers");

    const settings = {
      whole_shares: !!(optWholeShares && optWholeShares.checked),
      min_order_usd: optMinOrder && optMinOrder.value ? Number(optMinOrder.value) : undefined,
      price_tilt: optPriceTilt && optPriceTilt.value ? Number(optPriceTilt.value) : undefined,
      score_temperature: optScoreTemp && optScoreTemp.value ? Number(optScoreTemp.value) : undefined,
      max_new_alloc_pct: optMaxNewAlloc && optMaxNewAlloc.value ? Number(optMaxNewAlloc.value) / 100 : undefined,
    };

    const r = await fetch(`${backendBase()}/generate`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ portfolio_csv: portfolioCsv, wishlist, settings }),
    });
    const j = await r.json().catch(() => null);
    if (!r.ok) {
      const msg = j && j.error ? String(j.error) : `HTTP ${r.status}`;
      throw new Error(msg);
    }
    return j;
  }

  function setSuggest(items) {
    suggest.innerHTML = "";
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
        tickerSearch.value = "";
        setSuggest([]);
      });
      suggest.appendChild(d);
    });
  }

  function searchTickers(q) {
    const s = String(q || "").trim().toUpperCase();
    if (!s) return [];
    const db = state.tickersDb;
    const res = [];
    for (let i = 0; i < db.length; i++) {
      const it = db[i];
      if (it.ticker.includes(s) || (it.name || "").toUpperCase().includes(s)) {
        res.push(it);
        if (res.length >= 8) break;
      }
    }
    return res;
  }

  function maybeShowBackendHint() {
    if (!genStatus) return;
    genStatus.textContent = "Tip: start the local backend with: python3 backend.py";
  }

  async function loadTickerDb() {
    state.tickersDb = [
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
    tickerHint.textContent = "Tip: type any ticker and press Enter (suggestions are a small built-in list).";
  }

  function boot() {
    loadTickerDb();

    maybeShowBackendHint();

    const report = loadJsonLS(LS.report);
    if (report) {
      renderReport(report);
      showReport();
    } else {
      showWizard();
    }

    const portfolioRaw = localStorage.getItem(LS.portfolioCsv);
    if (portfolioRaw) {
      try {
        const p = parsePortfolioCsv(portfolioRaw);
        saveJsonLS(LS.portfolioParsed, p);
        renderPortfolioSummary(p);
        btnDownloadPortfolio.disabled = false;
        if (btnGenerate) btnGenerate.disabled = getWishlist().length === 0;
      } catch {
        // ignore
      }
    }

    renderWishlistChips();
    btnDownloadWishlist.disabled = getWishlist().length === 0;
    if (btnGenerate) btnGenerate.disabled = getWishlist().length === 0 || !localStorage.getItem(LS.portfolioCsv);

    // Settings defaults
    if (optMinOrder && !optMinOrder.value) optMinOrder.value = localStorage.getItem("wi_opt_min_order") || "25";
    if (optPriceTilt && !optPriceTilt.value) optPriceTilt.value = localStorage.getItem("wi_opt_price_tilt") || "0.20";
    if (optScoreTemp && !optScoreTemp.value) optScoreTemp.value = localStorage.getItem("wi_opt_score_temp") || "10";
    if (optMaxNewAlloc && !optMaxNewAlloc.value) optMaxNewAlloc.value = localStorage.getItem("wi_opt_max_new_alloc") || "40";
    if (optWholeShares) optWholeShares.checked = (localStorage.getItem("wi_opt_whole_shares") || "0") === "1";
  }

  function persistSettings() {
    if (optMinOrder) localStorage.setItem("wi_opt_min_order", optMinOrder.value || "");
    if (optPriceTilt) localStorage.setItem("wi_opt_price_tilt", optPriceTilt.value || "");
    if (optScoreTemp) localStorage.setItem("wi_opt_score_temp", optScoreTemp.value || "");
    if (optMaxNewAlloc) localStorage.setItem("wi_opt_max_new_alloc", optMaxNewAlloc.value || "");
    if (optWholeShares) localStorage.setItem("wi_opt_whole_shares", optWholeShares.checked ? "1" : "0");
  }

  portfolioFile.addEventListener("change", async () => {
    const f = portfolioFile.files && portfolioFile.files[0];
    if (!f) return;
    const text = await f.text();
    localStorage.setItem(LS.portfolioCsv, text);
    try {
      const p = parsePortfolioCsv(text);
      saveJsonLS(LS.portfolioParsed, p);
      renderPortfolioSummary(p);
      btnDownloadPortfolio.disabled = false;
      if (btnGenerate) btnGenerate.disabled = getWishlist().length === 0;
    } catch (e) {
      portfolioSummary.textContent = String(e);
    }
  });

  btnDownloadPortfolio.addEventListener("click", () => {
    const raw = localStorage.getItem(LS.portfolioCsv);
    if (!raw) return;
    dl("Report-With-Cash.csv", raw, "text/csv");
  });

  function addTickerFromInput() {
    const v = String(tickerSearch.value || "").trim().toUpperCase();
    if (!v) return;
    if (!/^[A-Z0-9.\-]{1,10}$/.test(v)) return;
    setWishlist([...getWishlist(), v]);
    tickerSearch.value = "";
    setSuggest([]);
  }

  tickerSearch.addEventListener("input", () => {
    const q = tickerSearch.value;
    if (!q) {
      setSuggest([]);
      return;
    }
    setSuggest(searchTickers(q));
  });

  tickerSearch.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTickerFromInput();
    }
  });

  btnDownloadWishlist.addEventListener("click", () => {
    const payload = { tickers: getWishlist() };
    dl("wishlist.json", JSON.stringify(payload, null, 2), "application/json");
  });

  if (btnGenerate) {
    btnGenerate.addEventListener("click", async () => {
      genStatus.textContent = "Generating...";
      btnGenerate.disabled = true;
      try {
        persistSettings();
        const report = await generateReportViaBackend();
        saveJsonLS(LS.report, report);
        renderReport(report);
        showReport();
        genStatus.textContent = "Done.";
      } catch (e) {
        genStatus.textContent = `Failed: ${e}`;
        genStatus.textContent += " (Is the local backend running? Try: python3 backend.py)";
        btnGenerate.disabled = getWishlist().length === 0 || !localStorage.getItem(LS.portfolioCsv);
      }
    });
  }

  async function handleReportFile(f) {
    if (!f) return;
    try {
      const text = await f.text();
      const j = JSON.parse(text);
      saveJsonLS(LS.report, j);
      reportLoadStatus.textContent = "Loaded report.json";
      renderReport(j);
      showReport();
    } catch (e) {
      reportLoadStatus.textContent = `Failed to load report.json: ${e}`;
    }
  }

  reportFile.addEventListener("change", () => {
    const f = reportFile.files && reportFile.files[0];
    handleReportFile(f);
  });

  reportFile2.addEventListener("change", () => {
    const f = reportFile2.files && reportFile2.files[0];
    handleReportFile(f);
  });

  btnEdit.addEventListener("click", () => {
    localStorage.removeItem(LS.report);
    showWizard();
  });

  btnReset.addEventListener("click", () => {
    Object.values(LS).forEach((k) => localStorage.removeItem(k));
    location.reload();
  });

  btnExport.addEventListener("click", () => {
    const report = loadJsonLS(LS.report);
    if (report) {
      dl("wi-export.json", JSON.stringify(report, null, 2), "application/json");
      return;
    }
    const payload = {
      schema_version: 1,
      exported_at: new Date().toISOString(),
      portfolio: loadJsonLS(LS.portfolioParsed),
      wishlist: { tickers: getWishlist() },
    };
    dl("wi-export.json", JSON.stringify(payload, null, 2), "application/json");
  });

  boot();
})();
