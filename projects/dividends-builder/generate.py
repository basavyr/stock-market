import csv
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import yfinance as yf  # type: ignore[import-not-found]

try:
    import yfinance as _yf  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    _yf = None


if _yf is not None:
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)


REPO_ROOT = Path(__file__).resolve().parent
EXPORT_PATH = REPO_ROOT / "export.json"


def load_dotenv(dotenv_path: Path) -> None:
    """Minimal .env loader (no external dependency).

    - Only sets keys that are not already present in the environment.
    - Supports simple KEY=VALUE lines (optionally quoted). Ignores comments/blanks.
    """

    if not dotenv_path.exists():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        os.environ.setdefault(key, value)


load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class SourceConfig:
    key: str
    name: str
    env_path_key: str
    env_glob_key: str
    default_glob: str
    currency_symbol: str


SOURCES: List[SourceConfig] = [
    SourceConfig(
        key="ibkr",
        name="Interactive Brokers",
        env_path_key="IBKR_CSV_PATH",
        env_glob_key="IBKR_CSV_GLOB",
        default_glob="Report-With-Cash*.csv",
        currency_symbol="$",
    ),
    SourceConfig(
        key="tradeville",
        name="Tradeville",
        env_path_key="TRADEVILLE_CSV_PATH",
        env_glob_key="TRADEVILLE_CSV_GLOB",
        default_glob="portof*.csv",
        currency_symbol="RON",
    ),
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _local_now_human() -> str:
    # Example: Feb 11, 2026 10:33
    return datetime.now().astimezone().strftime("%b %d, %Y %H:%M")


def _local_from_iso_human(iso_ts: str) -> str:
    # Example: Feb 11, 2026 10:33
    try:
        dt = datetime.fromisoformat(iso_ts)
        return dt.astimezone().strftime("%b %d, %Y %H:%M")
    except Exception:
        return iso_ts


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return default
    # handle thousands separators
    s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return default


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    _ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=False)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _downloads_dir() -> Path:
    # Avoid hard-coded absolute paths (privacy).
    return Path.home() / "Downloads"


def _latest_match(directory: Path, pattern: str) -> Optional[Path]:
    try:
        matches = [p for p in directory.glob(pattern) if p.is_file()]
    except Exception:
        matches = []
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def resolve_input_path(source: SourceConfig) -> Optional[Path]:
    # 1) Explicit path wins.
    raw = os.environ.get(source.env_path_key)
    if raw:
        p = Path(raw).expanduser()
        return p if p.exists() and p.is_file() else None

    # 2) Otherwise search Downloads by glob.
    downloads = _downloads_dir()
    glob_pat = os.environ.get(source.env_glob_key, source.default_glob)
    return _latest_match(downloads, glob_pat)


def sniff_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample)
        return dialect.delimiter
    except Exception:
        return ","


def parse_ibkr_report(path: Path) -> List[Dict[str, Any]]:
    """Parse an IBKR report CSV and return rows with at least Symbol + Quantity."""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    header_idx: Optional[int] = None
    for i, line in enumerate(lines):
        if "Symbol" in line and ("Quantity" in line or "Position" in line):
            header_idx = i
            break
    if header_idx is None:
        for i, line in enumerate(lines):
            if "Symbol" in line:
                header_idx = i
                break
    if header_idx is None:
        raise ValueError("Could not find a header row containing 'Symbol'.")

    sample = "\n".join(lines[header_idx : header_idx + 5])
    delimiter = sniff_delimiter(sample)
    reader = csv.DictReader(lines[header_idx:], delimiter=delimiter)

    parsed: List[Dict[str, Any]] = []
    qty_candidates = [
        "Quantity",
        "Position",
        "Position (Quantity)",
        "Position Quantity",
    ]
    for row in reader:
        symbol = (row.get("Symbol") or row.get("symbol") or row.get("Ticker") or "").strip()
        if not symbol:
            continue
        qty_raw = None
        for key in qty_candidates:
            if key in row and row.get(key) not in (None, ""):
                qty_raw = row.get(key)
                break
        if qty_raw is None:
            qty_raw = row.get("Quantity")

        qty = _safe_float(qty_raw, default=0.0)
        if qty == 0.0:
            continue

        parsed.append({"Symbol": symbol, "Quantity": qty})

    return parsed


def parse_tradeville_portof(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8", errors="replace") as reader:
        first_line = reader.readline()
        delimiter = "\t"
        if first_line.startswith("SEP="):
            delimiter = first_line.split("=", 1)[1].strip("\n\r")
        else:
            reader.seek(0)

        reader_csv = csv.DictReader(reader, delimiter=delimiter)
        parsed: List[Dict[str, Any]] = []
        for row in reader_csv:
            ticker = (row.get("simbol") or row.get("Simbol") or row.get("SYMBOL") or "").strip()
            if not ticker or ticker == "RON":
                continue
            if not ticker.endswith(".RO"):
                ticker = f"{ticker}.RO"

            qty = _safe_float(row.get("sold") or row.get("Sold") or row.get("quantity"), default=0.0)
            if qty == 0.0:
                continue

            parsed.append({"Symbol": ticker, "Quantity": qty})
        return parsed


def get_stock_data(ticker: str) -> Optional[Tuple[float, float, float, str, str]]:
    """Return (yield_pct, annual_div_per_share, price, currency, dividend_basis).

    We aim for a forward-looking annual dividend estimate:
    - Prefer Yahoo's annualized dividend rate (typically forward) when available.
    - Fall back to trailing 12-month dividends when needed.
    - Compute yield from annual_div / price for consistent units.
    """
    if _yf is None:
        raise RuntimeError(
            "Missing dependency: yfinance. Install with: pip install yfinance"
        )
    try:
        stock = _yf.Ticker(ticker)

        currency = "USD"
        price: Optional[float] = None

        try:
            fi = getattr(stock, "fast_info", None)
            if fi:
                currency = fi.get("currency") or currency
                price = fi.get("last_price") or fi.get("lastPrice") or fi.get("regular_market_price")
        except Exception:
            pass

        if price is None:
            hist = stock.history(period="5d")
            if hist is not None and not hist.empty:
                price = float(hist["Close"].iloc[-1])

        info = {}
        try:
            info = stock.info or {}
        except Exception:
            info = {}

        currency = info.get("currency") or currency

        if price is None:
            price = info.get("currentPrice")
        if price is None:
            return None

        dividend_basis = "none"

        forward_rate = info.get("dividendRate")
        if forward_rate is None:
            forward_rate = info.get("forwardAnnualDividendRate")

        annual_div = _safe_float(forward_rate, default=0.0)
        if annual_div > 0.0:
            dividend_basis = "forward_rate"
        else:
            # Fallback: trailing 12 months sum of dividends (not forward, but better than guessing).
            try:
                divs = stock.dividends
                if divs is not None and not divs.empty:
                    # Use timezone-aware cutoff in local time to avoid surprises.
                    cutoff = datetime.now().astimezone() - timedelta(days=365)
                    # pandas index is datetime-like
                    trailing = divs[divs.index >= cutoff]
                    annual_div = float(trailing.sum()) if trailing is not None else 0.0
                    if annual_div > 0.0:
                        dividend_basis = "trailing_12m"
            except Exception:
                annual_div = 0.0

        yield_pct = (annual_div / float(price) * 100.0) if float(price) > 0 else 0.0

        return float(yield_pct), float(annual_div), float(price), str(currency), dividend_basis
    except Exception:
        return None


def build_portfolio_data(holdings: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float]:
    rows: List[Dict[str, Any]] = []
    total_adi = 0.0
    for h in holdings:
        ticker = str(h["Symbol"]).strip()
        quantity = _safe_float(h.get("Quantity"), default=0.0)
        if not ticker or quantity <= 0:
            continue

        sd = get_stock_data(ticker)
        if sd is None:
            continue

        yield_pct, annual_div_per_share, current_price, listing_currency, dividend_basis = sd
        annual_revenue = round(annual_div_per_share * quantity, 2)

        rows.append(
            {
                "ticker": ticker,
                "quantity": round(quantity, 6),
                "yield": round(yield_pct, 2),
                "annual_dividend_per_share": round(annual_div_per_share, 6),
                "current_price": round(float(current_price), 6),
                "annual_revenue": annual_revenue,
                "currency": listing_currency,
                "dividend_basis": dividend_basis,
            }
        )
        total_adi += annual_revenue

    return rows, round(total_adi, 2)


def generate_for_source(source: SourceConfig) -> Dict[str, Any]:
    # Only returns a new source payload when we successfully update.
    input_path = resolve_input_path(source)
    if not input_path:
        raise FileNotFoundError("input CSV not found")

    if source.key == "ibkr":
        holdings = parse_ibkr_report(input_path)
    elif source.key == "tradeville":
        holdings = parse_tradeville_portof(input_path)
    else:
        raise ValueError(f"Unknown source key: {source.key}")

    portfolio_rows, total_adi = build_portfolio_data(holdings)
    if not portfolio_rows:
        raise ValueError("no holdings parsed or no market data available")

    updated_at = _utc_now_iso()
    return {
        "name": source.name,
        "display_currency": source.currency_symbol,
        "updated_at": updated_at,
        "updated_at_human": _local_from_iso_human(updated_at),
        "status": "updated",
        "message": None,
        "total_adi": total_adi,
        "portfolio": portfolio_rows,
    }


def main() -> None:
    export: Dict[str, Any] = {}
    if EXPORT_PATH.exists():
        try:
            export = read_json(EXPORT_PATH)
        except Exception:
            export = {}

    export.setdefault("schema_version", 1)
    export["generated_at"] = _utc_now_iso()
    export["generated_at_human"] = _local_from_iso_human(export["generated_at"])
    sources_out: Dict[str, Any] = export.setdefault("sources", {})

    results: List[Tuple[str, str, Optional[str]]] = []
    for source in SOURCES:
        try:
            payload = generate_for_source(source)
        except FileNotFoundError:
            # Smart behavior: keep previous data intact.
            results.append((source.key, "skipped", "input CSV not found"))
            continue
        except Exception as e:
            # If we have a previous payload for this source, keep it.
            results.append((source.key, "error", str(e)))
            continue

        sources_out[source.key] = payload
        results.append((source.key, "updated", None))

    write_json(EXPORT_PATH, export)

    print(f"Wrote: {EXPORT_PATH}")
    print("Sources:")
    for key, status, msg in results:
        if status == "updated":
            total = sources_out.get(key, {}).get("total_adi")
            print(f"- {key}: OK (ADI={total})")
        elif status == "skipped":
            print(f"- {key}: skipped ({msg})")
        else:
            print(f"- {key}: ERROR ({msg})")


if __name__ == "__main__":
    main()
