# Dividends Builder

Static dashboard for portfolio dividend planning.

## Privacy model

This project is designed so that **no personal portfolio data is committed** or shipped on GitHub Pages.

- Your portfolio data is stored locally in `projects/dividends-builder/export.json` (gitignored).
- The website loads data from an `export.json` you upload in the browser (client-side only).

## Generate local export.json

1) Install deps (generator needs yfinance):

```bash
pip install yfinance
```

2) Put your broker CSV(s) in `~/Downloads`:

- IBKR: `Report-With-Cash*.csv`
- Tradeville: `portof*.csv`

Or set explicit paths via `.env`:

```bash
cp projects/dividends-builder/.env.example projects/dividends-builder/.env
```

3) Run:

```bash
python3 projects/dividends-builder/generate.py
```

This updates `projects/dividends-builder/export.json`.

## Notes

- `export.json` updates are *smart*: if only one broker CSV is present, only that section is updated and the other is preserved.
- `export.json` intentionally contains no absolute paths.
