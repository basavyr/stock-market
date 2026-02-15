import argparse
import csv
import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


try:
    import yfinance as _yf  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    _yf = None


if _yf is not None:
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)


SCHEMA_VERSION = 1
YF_CACHE_SCHEMA = 2


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in {"1", "true", "yes", "y", "on"}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _timer() -> float:
    return time.perf_counter()


def _elapsed_ms(t0: float) -> int:
    return int(round((time.perf_counter() - t0) * 1000.0))


def _safe_float(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().strip('"').strip("'")
    if not s:
        return default
    s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return default


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)


def _normalize_yf_ticker(symbol: str) -> str:
    s = symbol.strip()
    # IBKR exports can include spaces (e.g. "BRK B"); Yahoo commonly uses dashes.
    if " " in s and "." not in s and "-" not in s:
        s = s.replace(" ", "-")
    return s


@dataclass(frozen=True)
class PortfolioHolding:
    symbol: str
    description: str
    isin: str
    quantity: float
    cost_basis_price: float
    fifo_pnl_unrealized: float


@dataclass(frozen=True)
class PortfolioParsed:
    cash: float
    cash_raw: Dict[str, float]
    holdings: List[PortfolioHolding]


def _find_holdings_header_idx(lines: List[str]) -> int:
    for i, line in enumerate(lines):
        if '"Symbol"' in line and '"Quantity"' in line:
            return i
        if "Symbol" in line and "Quantity" in line:
            return i
    raise ValueError("Could not find holdings header row containing Symbol + Quantity")


def parse_ibkr_report_with_cash(csv_path: Path) -> PortfolioParsed:
    text = _read_text(csv_path)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        raise ValueError("CSV too short")

    # Cash section: first line is a header, second line is values.
    cash_header = None
    cash_values = None
    if "NetCashBalance" in lines[0]:
        cash_header = lines[0]
        cash_values = lines[1] if len(lines) > 1 else None

    cash_raw: Dict[str, float] = {}
    cash = 0.0
    if cash_header and cash_values:
        reader = csv.DictReader([cash_header, cash_values])
        row = next(reader)
        for k, v in (row or {}).items():
            if not k:
                continue
            cash_raw[k] = _safe_float(v, default=0.0)
        cash = cash_raw.get("NetCashBalanceSLB", 0.0)

    header_idx = _find_holdings_header_idx(lines)
    reader = csv.DictReader(lines[header_idx:])
    holdings: List[PortfolioHolding] = []
    for row in reader:
        symbol = (row.get("Symbol") or "").strip().strip('"')
        if not symbol:
            continue
        holdings.append(
            PortfolioHolding(
                symbol=symbol,
                description=(row.get("Description") or "").strip().strip('"'),
                isin=(row.get("ISIN") or "").strip().strip('"'),
                quantity=_safe_float(row.get("Quantity"), default=0.0),
                cost_basis_price=_safe_float(row.get("CostBasisPrice"), default=0.0),
                fifo_pnl_unrealized=_safe_float(row.get("FifoPnlUnrealized"), default=0.0),
            )
        )
    holdings = [h for h in holdings if h.quantity != 0.0]
    return PortfolioParsed(cash=cash, cash_raw=cash_raw, holdings=holdings)


def load_wishlist(path: Path) -> List[str]:
    raw = json.loads(_read_text(path))
    tickers: List[str] = []
    if isinstance(raw, dict) and isinstance(raw.get("tickers"), list):
        tickers = [str(x).strip() for x in raw["tickers"]]
    elif isinstance(raw, list):
        tickers = [str(x).strip() for x in raw]
    else:
        raise ValueError("wishlist.json must be an array of tickers or an object with {tickers: []}")

    out: List[str] = []
    seen = set()
    for t in tickers:
        if not t:
            continue
        key = t.upper()
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def _cache_dir() -> Path:
    base = os.environ.get("WISHLIST_INVESTOR_CACHE_DIR")
    if base:
        return Path(base) / "yfinance"

    # Default to a stable per-user cache dir on macOS.
    home = Path.home()
    return home / "Library" / "Caches" / "wishlist-investor" / "yfinance"


def _cache_ttl_seconds() -> int:
    return int(os.environ.get("YF_CACHE_TTL_SECONDS", "21600"))


def _read_cache(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(_read_text(path))
        if not isinstance(data, dict):
            return None
        fetched_at = data.get("fetched_at")
        if not fetched_at:
            return None
        try:
            dt = datetime.fromisoformat(str(fetched_at))
        except Exception:
            return None
        age = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds()
        if age > float(_cache_ttl_seconds()):
            return None
        payload = data.get("payload")
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None


def _write_cache(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(path, {"schema_version": YF_CACHE_SCHEMA, "fetched_at": _utc_now_iso(), "payload": payload})


def fetch_yahoo_snapshot(symbol: str) -> Optional[Dict[str, Any]]:
    if _yf is None:
        raise RuntimeError("Missing dependency: yfinance. Install with: pip install yfinance")

    yf_ticker = _normalize_yf_ticker(symbol)
    cache_path = _cache_dir() / f"{yf_ticker}.json"
    cached = _read_cache(cache_path)

    # Cache format and payload have evolved; force a refresh if this payload is
    # missing fields we now rely on for company-specific rationale.
    if cached is not None and cached.get("_cache_schema") == YF_CACHE_SCHEMA:
        return cached

    t = _yf.Ticker(yf_ticker)
    info: Dict[str, Any] = {}
    try:
        info = t.info or {}
    except Exception:
        info = {}

    price = None
    currency = None
    try:
        fi = getattr(t, "fast_info", None)
        if fi:
            currency = fi.get("currency")
            price = fi.get("last_price") or fi.get("lastPrice") or fi.get("regular_market_price")
    except Exception:
        pass

    if price is None:
        price = info.get("currentPrice")
    if currency is None:
        currency = info.get("currency")

    if price is None:
        try:
            hist = t.history(period="5d")
            if hist is not None and not hist.empty:
                price = float(hist["Close"].iloc[-1])
        except Exception:
            price = None

    if price is None:
        return None

    dy_raw = info.get("dividendYield")
    dr_raw = info.get("dividendRate") or info.get("forwardAnnualDividendRate")
    dy_norm, dy_suspicious = _normalize_dividend_yield(
        dividend_yield=dy_raw,
        dividend_rate=dr_raw,
        price=price,
    )

    payload: Dict[str, Any] = {
        "_cache_schema": YF_CACHE_SCHEMA,
        "symbol": symbol,
        "yf_ticker": yf_ticker,
        "price": _safe_float(price, default=0.0),
        "currency": currency or "USD",
        "shortName": info.get("shortName") or info.get("longName"),
        "country": info.get("country"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "marketCap": info.get("marketCap"),
        "trailingPE": info.get("trailingPE"),
        "forwardPE": info.get("forwardPE"),
        "dividendYield": dy_norm,
        "dividendYield_raw": dy_raw,
        "dividend_yield_suspicious": dy_suspicious,
        "dividendRate": dr_raw,
        "beta": info.get("beta"),
        "businessSummary": info.get("longBusinessSummary") or info.get("businessSummary"),
        # Extra factors for scoring (best-effort; many symbols are missing some of these)
        "profitMargins": info.get("profitMargins"),
        "operatingMargins": info.get("operatingMargins"),
        "grossMargins": info.get("grossMargins"),
        "returnOnEquity": info.get("returnOnEquity"),
        "returnOnAssets": info.get("returnOnAssets"),
        "revenueGrowth": info.get("revenueGrowth"),
        "earningsGrowth": info.get("earningsGrowth"),
        "freeCashflow": info.get("freeCashflow"),
        "totalCash": info.get("totalCash"),
        "totalDebt": info.get("totalDebt"),
        "debtToEquity": info.get("debtToEquity"),
        "payoutRatio": info.get("payoutRatio"),
        "priceToBook": info.get("priceToBook"),
        "pegRatio": info.get("pegRatio"),
        "recommendationMean": info.get("recommendationMean"),
        "numberOfAnalystOpinions": info.get("numberOfAnalystOpinions"),
    }
    _write_cache(cache_path, payload)
    return payload


def _normalize_dividend_yield(
    *,
    dividend_yield: Any,
    dividend_rate: Any,
    price: Any,
) -> Tuple[Optional[float], bool]:
    """Normalize Yahoo/yfinance dividend yield to a 0..1 fraction.

    Returns (yield_fraction_or_none, suspicious_flag).
    """

    p = _safe_float(price, default=0.0)
    dy = _safe_float(dividend_yield, default=0.0)
    dr = _safe_float(dividend_rate, default=0.0)

    out: Optional[float] = None

    if dy > 0:
        # yfinance is inconsistent: sometimes it returns yield as a fraction
        # (0.05) and sometimes as a percent (5). Normalize to fraction.
        if dy > 1.0 and dy <= 100.0:
            dy = dy / 100.0
        out = float(dy)
    elif dr > 0 and p > 0:
        out = float(dr) / float(p)

    if out is None:
        return None, False

    suspicious = bool(out > 0.25)
    if out < 0:
        return None, True
    return out, suspicious


def _first_sentence(text: Any, max_len: int = 160) -> Optional[str]:
    s = str(text or "").strip()
    if not s:
        return None
    for sep in (". ", ".\n", "\n"):
        if sep in s:
            s = s.split(sep, 1)[0].strip()
            if not s.endswith("."):
                s += "."
            break
    if len(s) > max_len:
        s = s[: max_len - 3].rstrip() + "..."
    return s


def _keyword_in(text: str, *needles: str) -> bool:
    t = text.lower()
    return any(n.lower() in t for n in needles)


def _company_specific_risks(sym: str, quote: Optional[Dict[str, Any]]) -> List[str]:
    if not quote:
        return ["No Yahoo snapshot available; verify symbol and broker listing."]

    out: List[str] = []

    sector = str(quote.get("sector") or "").strip()
    industry = str(quote.get("industry") or "").strip()
    country = str(quote.get("country") or "").strip()
    currency = str(quote.get("currency") or "").strip()
    beta = quote.get("beta")
    mcap = quote.get("marketCap")
    summary = str(quote.get("businessSummary") or "")
    summary_l = summary.lower()
    d2e = _safe_float(quote.get("debtToEquity"), default=0.0)
    fcf = _safe_float(quote.get("freeCashflow"), default=0.0)
    pm = _safe_float(quote.get("profitMargins"), default=0.0)

    if currency and currency.upper() != "USD":
        out.append(f"Trading currency: {currency} (returns may be sensitive to FX moves).")
    if country and country.upper() not in {"UNITED STATES", "US", "USA"}:
        out.append(f"Country exposure: {country} (local policy/regulatory/macroeconomic shifts can dominate).")

    b = _safe_float(beta, default=0.0)
    if b >= 1.3:
        out.append(f"Higher historical volatility (beta ~{b:.2f}).")

    mc = _safe_float(mcap, default=0.0)
    if 0 < mc < 10_000_000_000:
        out.append("Smaller market cap can mean higher drawdowns and thinner liquidity during stress.")

    if quote.get("dividend_yield_suspicious") and quote.get("dividendYield") is not None:
        dy = _safe_float(quote.get("dividendYield"), default=0.0)
        if dy > 0:
            out.append(
                f"Dividend yield looks unusually high (~{dy * 100.0:.1f}%), which can reflect special dividends or stale data."
            )

    if d2e >= 250:
        out.append("High leverage (debt-to-equity is elevated); refinancing costs can rise when rates are high.")
    if fcf < 0:
        out.append("Free cash flow is negative (best-effort field); funding growth may require more debt/equity.")
    if pm < 0:
        out.append("Profit margins are negative (best-effort field); results may be pressured or volatile.")

    # Sector/industry heuristics (tied to Yahoo classification for this symbol).
    si = f"{sector} {industry}".strip().lower()
    if "utilities" in si:
        out.append("Regulated returns depend on rate cases and allowed ROE; capex is sensitive to interest rates.")
    if "energy" in si or _keyword_in(summary, "oil", "gas", "refining", "upstream", "downstream", "lng"):
        out.append("Cash flows are sensitive to commodity prices/spreads and policy/ESG constraints.")
    if "basic materials" in si or _keyword_in(summary, "mining", "iron ore", "copper", "nickel", "gold"):
        out.append("Earnings are cyclical with commodity prices and permitting/environmental constraints.")
    if "healthcare" in si or _keyword_in(summary, "pharmaceutical", "drug", "clinical", "trial"):
        out.append("Pipeline/regulatory outcomes and patent expirations can drive step-changes in revenue.")
    if "financial" in si or _keyword_in(summary, "asset management", "private equity", "credit", "insurance", "bank"):
        out.append("Results can be driven by credit conditions, fundraising/flows, and valuation marks in risk-off periods.")
    if "technology" in si or _keyword_in(summary, "semiconductor", "software", "cloud", "data center"):
        out.append("Execution risk: product cycles, competition, and (for hardware) supply chain/export controls.")

    # A single explicit exposure if clearly called out.
    if _keyword_in(summary_l, "iron ore"):
        out.append("Key demand driver: iron ore usage in global steel production.")
    elif _keyword_in(summary_l, "memory", "dram", "nand"):
        out.append("Key demand driver: memory pricing cycles (DRAM/NAND), which can swing sharply.")

    dedup: List[str] = []
    seen = set()
    for x in out:
        k = x.strip().lower()
        if not k or k in seen:
            continue
        seen.add(k)
        dedup.append(x)
    return dedup[:5] if dedup else ["Company-specific risk signals were not available from Yahoo for this symbol."]


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _score_company(
    *,
    sym: str,
    quote: Optional[Dict[str, Any]],
    cur_weight: float,
    whole_shares: bool,
) -> Dict[str, Any]:
    """Return a 0..100 score and a short breakdown.

    This is heuristic and best-effort; missing data yields neutral contributions.
    """

    if not quote:
        return {
            "score": 40.0,
            "components": {"quality": 0.0, "growth": 0.0, "value": 0.0, "income": 0.0, "risk": -6.0, "afford": 0.0},
            "notes": ["No Yahoo snapshot available; score is conservative default."],
        }

    notes: List[str] = []

    price = _safe_float(quote.get("price"), default=0.0)
    pe = _safe_float(quote.get("trailingPE"), default=0.0)
    fpe = _safe_float(quote.get("forwardPE"), default=0.0)
    dy = _safe_float(quote.get("dividendYield"), default=0.0)
    beta = _safe_float(quote.get("beta"), default=0.0)
    roe = _safe_float(quote.get("returnOnEquity"), default=0.0)
    pm = _safe_float(quote.get("profitMargins"), default=0.0)
    om = _safe_float(quote.get("operatingMargins"), default=0.0)
    rg = _safe_float(quote.get("revenueGrowth"), default=0.0)
    eg = _safe_float(quote.get("earningsGrowth"), default=0.0)
    d2e = _safe_float(quote.get("debtToEquity"), default=0.0)
    payout = _safe_float(quote.get("payoutRatio"), default=0.0)
    country = str(quote.get("country") or "").strip()

    # Quality: margins + ROE + balance sheet sanity
    quality = 0.0
    if pm:
        quality += _clamp((pm - 0.05) / 0.20, -1.0, 1.0) * 10.0
    if om:
        quality += _clamp((om - 0.08) / 0.20, -1.0, 1.0) * 8.0
    if roe:
        quality += _clamp((roe - 0.10) / 0.25, -1.0, 1.0) * 10.0

    # Growth: revenue + earnings growth (YoY-ish fields)
    growth = 0.0
    if rg:
        growth += _clamp(rg / 0.20, -1.0, 1.0) * 10.0
    if eg:
        growth += _clamp(eg / 0.25, -1.0, 1.0) * 10.0

    # Value: prefer reasonable PE; neutral if missing
    value = 0.0
    ref_pe = fpe if fpe > 0 else pe
    if ref_pe > 0:
        if ref_pe < 10:
            value += 10.0
        elif ref_pe < 18:
            value += 8.0
        elif ref_pe < 28:
            value += 3.0
        elif ref_pe < 45:
            value -= 3.0
        else:
            value -= 6.0

    # Income: dividend yield, penalize suspicious or extreme payout
    income = 0.0
    if dy > 0 and not quote.get("dividend_yield_suspicious"):
        income += _clamp(dy / 0.06, 0.0, 1.5) * 10.0
    if payout > 0.85:
        income -= 6.0
        notes.append("High payout ratio can make dividends less resilient.")

    # Risk: beta + leverage + non-US country note
    risk = 0.0
    if beta:
        # beta < 1.0 still adds small benefit, but less than the penalty for high beta
        if beta >= 1.0:
            risk -= _clamp((beta - 1.0) / 0.8, 0.0, 1.5) * 10.0
        else:
            risk += _clamp((1.0 - beta) / 0.8, 0.0, 1.0) * 3.0
    if d2e:
        risk -= _clamp((d2e - 120.0) / 180.0, 0.0, 1.5) * 8.0
    if country and country.upper() not in {"UNITED STATES", "US", "USA"}:
        risk -= 3.0

    # Affordability: matters for whole-shares, but we also allow a mild price tilt.
    afford = 0.0
    if whole_shares and price > 0:
        # Penalize very high price names so the plan doesn't end up with 1 share
        # of something and dozens of another (pure UX preference).
        if price >= 700:
            afford -= 6.0
        elif price >= 350:
            afford -= 3.0
        elif price <= 80:
            afford += 2.0

    # Portfolio concentration: soft penalty for already-heavy names.
    conc = 0.0
    if cur_weight >= 0.15:
        conc -= 10.0
    elif cur_weight >= 0.10:
        conc -= 6.0
    elif cur_weight >= 0.06:
        conc -= 3.0

    # Keep raw score unbounded-ish so we can rank via softmax later.
    base = 50.0
    raw_total = base + quality + growth + value + income + risk + afford + conc
    score = _clamp(raw_total, 0.0, 100.0)

    return {
        "score": round(float(score), 1),
        "score_raw": round(float(raw_total), 2),
        "components": {
            "quality": round(float(quality), 1),
            "growth": round(float(growth), 1),
            "value": round(float(value), 1),
            "income": round(float(income), 1),
            "risk": round(float(risk), 1),
            "afford": round(float(afford), 1),
            "concentration": round(float(conc), 1),
        },
        "notes": notes,
    }


def _max_position_weight() -> float:
    return _safe_float(os.environ.get("MAX_POSITION_WEIGHT"), default=0.20)


def allocate_cash(
    investable_cash: float,
    wishlist: List[str],
    holding_values: Dict[str, float],
    total_portfolio_value: float,
) -> Dict[str, float]:
    # Deprecated: kept for compatibility with older callers.
    out: Dict[str, float] = {sym: 0.0 for sym in wishlist}
    if investable_cash <= 0:
        return out
    per = investable_cash / float(len(wishlist) or 1)
    for sym in wishlist:
        out[sym] = round(per, 2)
    return out


def allocate_cash_scored(
    *,
    investable_cash: float,
    wishlist: List[str],
    quotes: Dict[str, Dict[str, Any]],
    holding_values: Dict[str, float],
    holdings_total_value: float,
) -> Tuple[Dict[str, float], Dict[str, Any]]:
    """Allocate cash based on per-company score and guardrails."""

    max_w = _max_position_weight()
    whole_shares = _env_bool("WI_WHOLE_SHARES", default=False)
    min_order_usd = _safe_float(os.environ.get("WI_MIN_ORDER_USD"), default=25.0)
    price_tilt = _safe_float(os.environ.get("WI_PRICE_TILT"), default=0.20)
    softmax_temp = _safe_float(os.environ.get("WI_SCORE_TEMPERATURE"), default=10.0)
    max_new_alloc_pct = _safe_float(os.environ.get("WI_MAX_NEW_ALLOC_PCT"), default=0.40)

    post_total = float(holdings_total_value + investable_cash)
    denom = post_total if post_total > 0 else 1.0

    per_name_new_alloc_cap = float("inf")
    if max_new_alloc_pct > 0:
        per_name_new_alloc_cap = float(investable_cash) * float(max_new_alloc_pct)

    scored: List[Tuple[str, float, Dict[str, Any]]] = []
    for sym in wishlist:
        cur_val = float(holding_values.get(sym, 0.0))
        cur_w = (cur_val / denom) if denom > 0 else 0.0
        s = _score_company(sym=sym, quote=quotes.get(sym), cur_weight=cur_w, whole_shares=whole_shares)
        raw = _safe_float(s.get("score_raw"), default=_safe_float(s.get("score"), default=0.0))
        scored.append((sym, raw, s))

    # Price tilt reference: median price in wishlist universe.
    prices = []
    for sym in wishlist:
        q = quotes.get(sym) or {}
        p = _safe_float(q.get("price"), default=0.0)
        if p > 0:
            prices.append(p)
    prices.sort()
    p_ref = prices[len(prices) // 2] if prices else 0.0

    # Softmax on raw score to get differentiated weights.
    import math

    temp = softmax_temp if softmax_temp > 0 else 10.0
    exps: Dict[str, float] = {}
    max_raw = max((raw for _sym, raw, _s in scored), default=0.0)
    for sym, raw, _s in scored:
        exps[sym] = math.exp((raw - max_raw) / temp)
    total_exp = sum(exps.values()) or 1.0

    raw_w: Dict[str, float] = {}
    for sym in wishlist:
        w = exps.get(sym, 0.0) / total_exp
        q = quotes.get(sym) or {}
        p = _safe_float(q.get("price"), default=0.0)
        if price_tilt != 0 and p > 0 and p_ref > 0:
            # Lower price => slightly higher weight (user preference).
            tilt = (p_ref / p) ** float(price_tilt)
            w *= float(tilt)
        raw_w[sym] = float(w)

    total_w = sum(raw_w.values()) or 1.0

    # First pass: proportional allocation with max weight cap.
    alloc: Dict[str, float] = {sym: 0.0 for sym in wishlist}
    caps: Dict[str, float] = {}
    for sym in wishlist:
        cur_val = float(holding_values.get(sym, 0.0))
        cap_val = float(max_w * denom) if max_w > 0 else float("inf")
        max_add = max(0.0, cap_val - cur_val)
        caps[sym] = max_add

        ideal = investable_cash * (raw_w[sym] / total_w)
        if max_new_alloc_pct > 0:
            ideal = min(float(ideal), float(investable_cash) * float(max_new_alloc_pct))
        alloc[sym] = max(0.0, min(float(ideal), float(max_add)))

    # Remove dust allocations.
    for sym in wishlist:
        if alloc[sym] < min_order_usd:
            alloc[sym] = 0.0

    spent = sum(alloc.values())
    leftover = max(0.0, float(investable_cash) - spent)

    # Optional whole-share rounding.
    if whole_shares:
        rounded: Dict[str, float] = {}
        for sym in wishlist:
            q = quotes.get(sym) or {}
            p = _safe_float(q.get("price"), default=0.0)
            if p <= 0 or alloc[sym] <= 0:
                rounded[sym] = 0.0
                continue
            shares = int(float(alloc[sym]) // float(p))
            rounded[sym] = round(float(shares) * float(p), 2)
        alloc = rounded
        spent = sum(alloc.values())
        leftover = max(0.0, float(investable_cash) - spent)

    # Second pass: redistribute leftover to best-scoring names that still have cap room.
    if leftover > 0:
        by_score = sorted(scored, key=lambda x: x[1], reverse=True)
        for _ in range(2000):
            progressed = False
            for sym, _, _s in by_score:
                room = max(0.0, caps[sym] - alloc[sym])
                room = min(room, max(0.0, per_name_new_alloc_cap - alloc[sym]))
                if room <= 0:
                    continue
                if whole_shares:
                    q = quotes.get(sym) or {}
                    p = _safe_float(q.get("price"), default=0.0)
                    if p <= 0:
                        continue
                    if leftover < p or room < p:
                        continue
                    alloc[sym] = round(float(alloc[sym] + p), 2)
                    leftover = round(float(leftover - p), 2)
                else:
                    add = min(leftover, room)
                    if add < min_order_usd:
                        continue
                    alloc[sym] = round(float(alloc[sym] + add), 2)
                    leftover = round(float(leftover - add), 2)
                progressed = True
                if leftover < min_order_usd:
                    break
            if not progressed or leftover < min_order_usd:
                break

    meta = {
        "whole_shares": whole_shares,
        "min_order_usd": round(float(min_order_usd), 2),
        "price_tilt": float(price_tilt),
        "score_temperature": float(softmax_temp),
        "max_new_alloc_pct": float(max_new_alloc_pct),
        "max_position_weight": float(max_w),
        "scores": {sym: s for (sym, _score, s) in scored},
        "unallocated_cash": round(float(leftover), 2),
    }
    return alloc, meta


def build_reasons(
    sym: str,
    quote: Optional[Dict[str, Any]],
    is_held: bool,
    cur_weight: float,
    rec_amount: float,
) -> Tuple[List[str], List[str]]:
    why: List[str] = []
    keep: List[str] = []

    if quote and quote.get("shortName"):
        why.append(f"Company: {quote['shortName']}")
    if quote and quote.get("sector"):
        sector = quote.get("sector")
        industry = quote.get("industry")
        if industry:
            why.append(f"Sector/Industry: {sector} / {industry}")
        else:
            why.append(f"Sector: {sector}")

    if quote and quote.get("businessSummary"):
        fs = _first_sentence(quote.get("businessSummary"))
        if fs:
            why.append(f"Business: {fs}")

    # Lightweight financial highlights (best-effort fields).
    if quote:
        pm = _safe_float(quote.get("profitMargins"), default=0.0)
        if pm:
            why.append(f"Profit margin: ~{pm * 100.0:.1f}%")
        roe = _safe_float(quote.get("returnOnEquity"), default=0.0)
        if roe:
            why.append(f"ROE: ~{roe * 100.0:.1f}%")
        rg = _safe_float(quote.get("revenueGrowth"), default=0.0)
        if rg:
            why.append(f"Revenue growth (best-effort): ~{rg * 100.0:.1f}%")

    if is_held:
        why.append(f"Already held; current portfolio weight ~{cur_weight * 100.0:.1f}%")
    else:
        if quote and quote.get("sector"):
            why.append(f"Not currently held; adds exposure to {quote.get('sector')}")
        else:
            why.append("Not currently held")

    if quote and quote.get("trailingPE") is not None:
        why.append(f"Trailing P/E: {quote['trailingPE']}")

    if quote and quote.get("dividendYield") is not None and not quote.get("dividend_yield_suspicious"):
        dy = _safe_float(quote.get("dividendYield"), default=0.0)
        if dy > 0:
            why.append(f"Dividend yield (normalized): ~{dy * 100.0:.2f}%")

    if rec_amount <= 0:
        keep.append("Allocation is 0 under current risk guardrails (position weight cap).")

    keep.extend(_company_specific_risks(sym, quote))

    return why, keep


def generate_report(
    *,
    portfolio_csv_path: Path,
    wishlist_json_path: Path,
    out_path: Path,
) -> Dict[str, Any]:
    t_all = _timer()

    portfolio = parse_ibkr_report_with_cash(portfolio_csv_path)
    wishlist = load_wishlist(wishlist_json_path)

    universe = {h.symbol.upper() for h in portfolio.holdings} | {w.upper() for w in wishlist}
    quotes: Dict[str, Dict[str, Any]] = {}

    # Fetch quotes concurrently; cache will short-circuit most runs.
    t_q = _timer()
    workers = int(os.environ.get("WI_QUOTE_WORKERS", "8"))
    syms = sorted(universe)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(fetch_yahoo_snapshot, sym): sym for sym in syms}
        for fut in as_completed(futs):
            sym = futs[fut]
            try:
                q = fut.result()
            except Exception:
                q = None
            if q is not None:
                quotes[sym] = q

    holding_values: Dict[str, float] = {}
    holdings_out: List[Dict[str, Any]] = []
    for h in portfolio.holdings:
        sym = h.symbol.upper()
        q = quotes.get(sym)
        price = _safe_float(q.get("price") if q else None, default=0.0)
        mv = round(price * float(h.quantity), 2) if price > 0 else 0.0
        holding_values[sym] = mv
        holdings_out.append(
            {
                "symbol": sym,
                "description": h.description,
                "isin": h.isin,
                "quantity": round(float(h.quantity), 6),
                "cost_basis_price": round(float(h.cost_basis_price), 6),
                "fifo_pnl_unrealized": round(float(h.fifo_pnl_unrealized), 2),
                "current_price": round(price, 6) if price else None,
                "market_value": mv,
                "yf_ticker": q.get("yf_ticker") if q else _normalize_yf_ticker(sym),
            }
        )

    holdings_total_value = sum(holding_values.values())
    cash = float(portfolio.cash)
    total_value = holdings_total_value + cash

    reserve = 0.0
    investable_cash = max(0.0, cash)

    allocations, alloc_meta = allocate_cash_scored(
        investable_cash=investable_cash,
        wishlist=wishlist,
        quotes=quotes,
        holding_values=holding_values,
        holdings_total_value=holdings_total_value,
    )

    recommendations: List[Dict[str, Any]] = []
    for sym in wishlist:
        q = quotes.get(sym)
        price = _safe_float(q.get("price") if q else None, default=0.0)
        cur_val = holding_values.get(sym, 0.0)
        denom = holdings_total_value if holdings_total_value > 0 else (total_value if total_value > 0 else 1.0)
        cur_weight = (cur_val / denom) if denom > 0 else 0.0
        rec_amount = float(allocations.get(sym, 0.0))
        rec_shares = round(rec_amount / price, 6) if price > 0 and rec_amount > 0 else 0.0

        why, keep = build_reasons(
            sym=sym,
            quote=q,
            is_held=(cur_val > 0),
            cur_weight=cur_weight,
            rec_amount=rec_amount,
        )

        score_obj = (alloc_meta.get("scores") or {}).get(sym) if isinstance(alloc_meta, dict) else None
        score = None
        score_components = None
        score_notes = None
        if isinstance(score_obj, dict):
            score = score_obj.get("score")
            score_components = score_obj.get("components")
            score_notes = score_obj.get("notes")

        recommendations.append(
            {
                "symbol": sym,
                "yf_ticker": q.get("yf_ticker") if q else _normalize_yf_ticker(sym),
                "company": q.get("shortName") if q else None,
                "score": score,
                "score_components": score_components,
                "score_notes": score_notes,
                "price": round(price, 6) if price else None,
                "currency": q.get("currency") if q else "USD",
                "sector": q.get("sector") if q else None,
                "current_holding_value": round(cur_val, 2),
                "current_weight": round(cur_weight, 6),
                "recommended_amount": round(rec_amount, 2),
                "recommended_shares_est": rec_shares,
                "why": why,
                "keep_in_mind": keep,
                "fundamentals": {
                    "marketCap": q.get("marketCap") if q else None,
                    "trailingPE": q.get("trailingPE") if q else None,
                    "forwardPE": q.get("forwardPE") if q else None,
                    "dividendYield": q.get("dividendYield") if q else None,
                    "dividendRate": q.get("dividendRate") if q else None,
                    "beta": q.get("beta") if q else None,
                },
            }
        )

    report: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now_iso(),
        "portfolio": {
            "cash": round(cash, 2),
            "cash_raw": portfolio.cash_raw,
            "cash_reserve": reserve,
            "investable_cash": round(investable_cash, 2),
            "holdings_total_value": round(holdings_total_value, 2),
            "total_value": round(total_value, 2),
            "holdings": holdings_out,
        },
        "wishlist": {"tickers": wishlist},
        "quotes": quotes,
        "recommendations": recommendations,
        "allocation": {
            "method": "scored",
            "meta": alloc_meta,
        },
        "perf": {
            "quotes_ms": _elapsed_ms(t_q),
            "total_ms": _elapsed_ms(t_all),
            "quote_workers": workers,
            "universe_count": len(universe),
            "quotes_returned": len(quotes),
            "cache_dir": str(_cache_dir()),
        },
        "notes": [
            "Prototype only; not investment advice.",
            "Market data fetched from Yahoo Finance via yfinance with local caching.",
        ],
    }

    _write_json(out_path, report)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate wishlist investment report JSON")
    ap.add_argument("--portfolio-csv", required=True, help="Path to IBKR Report-With-Cash CSV")
    ap.add_argument("--wishlist-json", required=True, help="Path to wishlist.json")
    ap.add_argument("--out", default="report.json", help="Output path for report JSON")
    args = ap.parse_args()

    portfolio_path = Path(args.portfolio_csv).expanduser().resolve()
    wishlist_path = Path(args.wishlist_json).expanduser().resolve()
    out_path = Path(args.out).expanduser().resolve()

    generate_report(
        portfolio_csv_path=portfolio_path,
        wishlist_json_path=wishlist_path,
        out_path=out_path,
    )
    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
