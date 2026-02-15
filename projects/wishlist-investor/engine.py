import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import generate


def _read_stdin_json() -> Any:
    raw = sys.stdin.read()
    if not raw.strip():
        return None
    return json.loads(raw)


def _apply_settings(settings: Any) -> None:
    if not isinstance(settings, dict):
        return

    def set_bool_env(env_name: str, key: str) -> None:
        v = settings.get(key)
        if v is None:
            return
        os.environ[env_name] = "1" if bool(v) else "0"

    def set_num_env(env_name: str, key: str) -> None:
        v = settings.get(key)
        if v is None:
            return
        try:
            os.environ[env_name] = str(float(v))
        except Exception:
            return

    set_bool_env("WI_WHOLE_SHARES", "whole_shares")
    set_num_env("WI_MIN_ORDER_USD", "min_order_usd")
    set_num_env("WI_PRICE_TILT", "price_tilt")
    set_num_env("WI_SCORE_TEMPERATURE", "score_temperature")
    set_num_env("WI_MAX_NEW_ALLOC_PCT", "max_new_alloc_pct")
    set_num_env("MAX_POSITION_WEIGHT", "max_position_weight")
    set_num_env("YF_CACHE_TTL_SECONDS", "yf_cache_ttl_seconds")


def main() -> None:
    body = _read_stdin_json() or {}
    if not isinstance(body, dict):
        raise SystemExit("Input must be a JSON object")

    portfolio_csv = body.get("portfolio_csv")
    wishlist = body.get("wishlist")
    settings = body.get("settings")

    if not isinstance(portfolio_csv, str) or not portfolio_csv.strip():
        raise SystemExit("Missing portfolio_csv")
    if not isinstance(wishlist, list) or not all(isinstance(x, str) for x in wishlist):
        raise SystemExit("Missing wishlist (array of strings)")

    _apply_settings(settings)

    base = Path(__file__).resolve().parent
    cache_run = base / ".cache" / "run"
    cache_run.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=str(cache_run)) as td:
        tdir = Path(td)
        portfolio_path = tdir / "Report-With-Cash.csv"
        wishlist_path = tdir / "wishlist.json"
        out_path = tdir / "report.json"

        portfolio_path.write_text(portfolio_csv, encoding="utf-8")
        wishlist_path.write_text(json.dumps({"tickers": wishlist}, indent=2), encoding="utf-8")

        report: Dict[str, Any] = generate.generate_report(
            portfolio_csv_path=portfolio_path,
            wishlist_json_path=wishlist_path,
            out_path=out_path,
        )
        sys.stdout.write(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
