# NSE Cup & Handle Scanner

Multi-timeframe Cup & Handle pattern scanner for NSE equities, built on
William O'Neil's CANSLIM entry/exit framework. Detection is deliberately
loose (maximum sensitivity); entry and exit rules are strict (capital
protection). See `spec_v3_full.txt` for the full design rationale.

## How it works

1. **Detection** (`cup_handle_detector.py`) — scans daily, weekly, and
   monthly price series for Cup & Handle shapes with a single hard gate
   (50% recovery from cup bottom to right rim). Everything else — prior
   uptrend, cup depth, shape, handle quality — is scored and tagged,
   never used to reject a pattern.
2. **Breakout Readiness** (`readiness.py`) — a separate 0-100% score
   for signals near their pivot, answering "is this actionable now?"
3. **Entry/Exit** (`entry_exit.py`) — strict O'Neil rules: volume
   confirmation, 8% max stop loss, 20%/cup-depth/Fibonacci targets,
   position sizing, and a sell-rule checklist.
4. **Report** (`report.py`) — a 5-sheet Excel workbook: Today's
   Signals, Near Breakout Watchlist, Active Tracking, Historical
   Signals, and Strategy Summary.

## Local setup

```bash
pip install -r requirements.txt
python main.py                       # incremental scan (downloads only new bars)
python main.py --full-refresh        # wipe and redownload full history
python main.py --refresh-universe    # force-refresh the NSE symbol list
python main.py --debug-symbol TCS.NS # verbose single-symbol diagnosis
```

Reports are written to `reports/cup_handle_report_YYYY-MM-DD.xlsx`.

## GitHub Actions

`.github/workflows/daily_scan.yml` runs the scanner automatically at
4:00 PM IST on trading days. It:

- Restores the previous run's Parquet data from cache (so only new
  bars get downloaded — first run downloads everything, every run
  after that is incremental)
- Runs the full scan
- Saves the updated data cache for next time
- Uploads the Excel report as a workflow artifact (90-day retention)

Trigger manually from the Actions tab with `workflow_dispatch` to set
`full_refresh`, `refresh_universe`, or `debug_symbol`.

## Configuration

All thresholds live in `config.py` — portfolio size, risk per trade,
detection lookback windows, entry/exit rules, and Breakout Readiness
weights. Detection thresholds are commented with the rationale for
keeping them loose; entry/exit thresholds are commented with the
rationale for keeping them strict. Read the comments before changing
either.

## File overview

| File | Purpose |
|---|---|
| `config.py` | All tuneable constants |
| `logger_utils.py` | Shared logging setup |
| `universe.py` | NSE symbol list fetcher/cache |
| `downloader.py` | Parquet data download, incremental updates |
| `indicators.py` | RSI, ADX, ATR, MAs, RS Rating |
| `cup_handle_detector.py` | Core pattern detection engine |
| `readiness.py` | Breakout Readiness scoring |
| `entry_exit.py` | Strict entry/exit/position-sizing calculator |
| `database.py` | SQLite persistence for signals and tracking |
| `report.py` | Excel report generator |
| `main.py` | Orchestrator / CLI entry point |
