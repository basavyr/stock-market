import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

import generate


BASE_DIR = Path(__file__).resolve().parent


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


def _read_json_body(handler: BaseHTTPRequestHandler) -> Any:
    n = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(n) if n > 0 else b""
    if not raw:
        return None
    return json.loads(raw.decode("utf-8", errors="replace"))


def _send_json(handler: BaseHTTPRequestHandler, status: int, payload: Any) -> None:
    data = json.dumps(payload, indent=2).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(data)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "content-type")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    handler.end_headers()
    handler.wfile.write(data)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # pragma: no cover
        # Keep the console clean; uncomment for debugging.
        # super().log_message(fmt, *args)
        return

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "content-type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") == "" or self.path.rstrip("/") == "/health":
            _send_json(self, 200, {"ok": True})
            return
        _send_json(self, 404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/generate":
            _send_json(self, 404, {"error": "not_found"})
            return

        try:
            body = _read_json_body(self) or {}
            if not isinstance(body, dict):
                raise ValueError("Body must be a JSON object")

            portfolio_csv = body.get("portfolio_csv")
            wishlist = body.get("wishlist")
            settings = body.get("settings")
            if not isinstance(portfolio_csv, str) or not portfolio_csv.strip():
                raise ValueError("Missing portfolio_csv")
            if not isinstance(wishlist, list) or not all(isinstance(x, str) for x in wishlist):
                raise ValueError("Missing wishlist (array of strings)")

            _apply_settings(settings)

            # Hardcode project working directory for now.
            os.chdir(BASE_DIR)

            run_dir = BASE_DIR / ".cache" / "run"
            run_dir.mkdir(parents=True, exist_ok=True)

            with tempfile.TemporaryDirectory(dir=str(run_dir)) as td:
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
                _send_json(self, 200, report)
        except Exception as e:
            _send_json(self, 400, {"error": str(e)})


def main() -> None:
    port = int(os.environ.get("WI_BACKEND_PORT", "8750"))
    host = os.environ.get("WI_BACKEND_HOST", "127.0.0.1")
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Wishlist Investor backend listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
