"""
NSE Cup & Handle Scanner - Database Layer
============================================
SQLite-backed persistence for:
  - cup_handle_signals : every signal ever detected, full geometry +
                          entry/exit + readiness fields (spec Part 8)
  - active_tracking is derived from cup_handle_signals.status, not a
    separate table — simpler schema, fewer places for state to drift

Uses parameterised queries throughout; never f-strings into SQL values.
"""

from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Optional

import pandas as pd

from config import SIGNALS_DB
from logger_utils import get_logger

log = get_logger("scanner")

DB_PATH = SIGNALS_DB

DDL = """
CREATE TABLE IF NOT EXISTS cup_handle_signals (
    signal_id               TEXT PRIMARY KEY,
    symbol                  TEXT NOT NULL,
    company_name             TEXT,
    sector                   TEXT,
    scan_date                TEXT NOT NULL,
    timeframe                TEXT NOT NULL,
    pattern_type              TEXT,
    signal_type               TEXT,
    quality_score              REAL,
    mtf_confluence             INTEGER DEFAULT 0,
    mtf_timeframes             TEXT,

    cup_start_date             TEXT,
    cup_bottom_date            TEXT,
    cup_end_date               TEXT,
    left_rim_price             REAL,
    cup_bottom_price           REAL,
    right_rim_price            REAL,
    cup_depth_pct              REAL,
    cup_depth_class            TEXT,
    cup_depth_verify_flag      INTEGER DEFAULT 0,
    cup_duration_bars          INTEGER,
    cup_shape                  TEXT,
    recovery_pct               REAL,
    prior_uptrend_pct          REAL,
    prior_uptrend_tag          TEXT,

    has_handle                 INTEGER DEFAULT 0,
    handle_start_date          TEXT,
    handle_end_date            TEXT,
    handle_low_price           REAL,
    handle_depth_pct           REAL,
    handle_duration_bars       INTEGER,
    handle_quality_subscore    REAL,
    handle_vol_dryup_pts       REAL,
    handle_tightness_pts       REAL,
    handle_higher_lows_pts     REAL,
    handle_close_high_pts      REAL,
    atr_at_handle_start        REAL,

    pivot_point                REAL,
    current_price               REAL,
    price_vs_pivot_pct          REAL,

    breakout_readiness_pct      REAL,
    readiness_near_pivot        INTEGER DEFAULT 0,
    readiness_tight_handle      INTEGER DEFAULT 0,
    readiness_rising_rs         INTEGER DEFAULT 0,
    readiness_atr_contract      INTEGER DEFAULT 0,
    readiness_above_50ma        INTEGER DEFAULT 0,
    readiness_reasons           TEXT,

    entry_price                 REAL,
    entry_zone_high              REAL,
    entry_type                   TEXT,
    extended_warning              TEXT,

    stop_loss_price               REAL,
    stop_loss_pct                 REAL,
    stop_loss_type                 TEXT,
    atr_14                         REAL,
    risk_per_share                  REAL,

    target1                         REAL,
    target2                         REAL,
    target3                         REAL,
    rr_t1                           REAL,
    rr_t2                           REAL,
    rr_t3                           REAL,
    rr_t2_warning                    TEXT,
    eight_week_hold_candidate        INTEGER DEFAULT 0,

    position_size_shares              INTEGER,
    capital_required                   REAL,
    risk_amount                        REAL,
    portfolio_risk_pct                 REAL,

    volume_ratio                       REAL,
    volume_confirmed                    INTEGER DEFAULT 0,
    volume_confirmed_label               TEXT,

    rs_rating                            REAL,
    rs_trend                              TEXT,
    rs_tag                                TEXT,
    rsi_val                               REAL,
    adx_val                               REAL,
    ma_short                              REAL,
    ma_mid                                REAL,
    ma_long                               REAL,
    price_vs_ma_short_pct                 REAL,

    nifty_trend                           TEXT,
    market_note                           TEXT,
    weak_momentum_note                    TEXT,
    below_50ma_note                       TEXT,

    liquidity_ok                          INTEGER DEFAULT 1,
    liquidity_warning                     TEXT,

    sell_notes                            TEXT,
    remarks                               TEXT,

    status                                TEXT DEFAULT 'Watching',
    entry_triggered                       INTEGER DEFAULT 0,
    entry_date                            TEXT,
    t1_achieved                           INTEGER DEFAULT 0,
    t2_achieved                           INTEGER DEFAULT 0,
    t3_achieved                           INTEGER DEFAULT 0,
    stopped_out                           INTEGER DEFAULT 0,
    exit_date                             TEXT,
    exit_price                            REAL,
    exit_type                             TEXT,
    realised_rr                            REAL,
    hold_days                              INTEGER,

    expiry_date                            TEXT,
    created_at                             TEXT DEFAULT (datetime('now')),
    last_checked                           TEXT
);

CREATE INDEX IF NOT EXISTS idx_ch_status ON cup_handle_signals(status);
CREATE INDEX IF NOT EXISTS idx_ch_symbol ON cup_handle_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_ch_scan_date ON cup_handle_signals(scan_date);
"""


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.executescript(DDL)
    log.info("Database initialised: %s", DB_PATH)


# ─── Signal ID generation ──────────────────────────────────────────────────

def make_signal_id(symbol: str, timeframe: str, cup_start_date, pivot_point: float) -> str:
    """
    Deterministic ID so the same underlying pattern doesn't get
    duplicated across daily runs. Pivot is rounded to 2dp since small
    floating point drift across runs shouldn't create a new ID.
    """
    raw = f"{symbol}|{timeframe}|{cup_start_date}|{round(pivot_point, 2)}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def signal_exists(signal_id: str) -> bool:
    with _conn() as con:
        row = con.execute(
            "SELECT 1 FROM cup_handle_signals WHERE signal_id = ?", (signal_id,)
        ).fetchone()
    return row is not None


# ─── CRUD ───────────────────────────────────────────────────────────────────

def upsert_cup_handle_signal(row: dict) -> None:
    """Insert a new signal row. Existing signal_ids are left untouched
    (INSERT OR IGNORE) — use update_signal_status for live tracking
    updates on already-persisted signals."""
    cols = ", ".join(row.keys())
    placeholders = ", ".join(f":{k}" for k in row)
    sql = f"INSERT OR IGNORE INTO cup_handle_signals ({cols}) VALUES ({placeholders})"
    with _conn() as con:
        con.execute(sql, row)


def update_signal_status(signal_id: str, **kwargs) -> None:
    if not kwargs:
        return
    sets = ", ".join(f"{k} = :{k}" for k in kwargs)
    kwargs["signal_id"] = signal_id
    kwargs["last_checked"] = datetime.now().isoformat()
    with _conn() as con:
        con.execute(
            f"UPDATE cup_handle_signals SET {sets}, last_checked = :last_checked "
            f"WHERE signal_id = :signal_id",
            kwargs,
        )


def get_open_signals() -> list[dict]:
    """Signals that have triggered (entry_triggered=1) but not yet hit
    a final target or stop — i.e. currently being tracked."""
    with _conn() as con:
        rows = con.execute(
            """SELECT * FROM cup_handle_signals
               WHERE entry_triggered = 1
                 AND stopped_out = 0
                 AND t3_achieved = 0
                 AND status NOT IN ('Stopped Out', 'Target 3 Achieved', 'Expired')
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_watching_signals() -> list[dict]:
    """Signals not yet triggered — the watchlist."""
    with _conn() as con:
        rows = con.execute(
            """SELECT * FROM cup_handle_signals
               WHERE entry_triggered = 0
                 AND status NOT IN ('Expired', 'Stopped Out')
            """
        ).fetchall()
    return [dict(r) for r in rows]


def get_todays_signals_df(scan_date: Optional[str] = None) -> pd.DataFrame:
    """Today's signals excluding Cup Only — the main actionable sheet."""
    scan_date = scan_date or date.today().isoformat()
    with _conn() as con:
        return pd.read_sql(
            """SELECT * FROM cup_handle_signals
               WHERE scan_date = ?
                 AND signal_type != 'CUP ONLY'
               ORDER BY mtf_confluence DESC, quality_score DESC""",
            con, params=(scan_date,),
        )


def get_todays_early_watch_df(scan_date: Optional[str] = None) -> pd.DataFrame:
    """Today's Cup Only signals — earlier stage, own sheet."""
    scan_date = scan_date or date.today().isoformat()
    with _conn() as con:
        return pd.read_sql(
            """SELECT * FROM cup_handle_signals
               WHERE scan_date = ?
                 AND signal_type = 'CUP ONLY'
               ORDER BY quality_score DESC""",
            con, params=(scan_date,),
        )


def get_all_signals_df() -> pd.DataFrame:
    with _conn() as con:
        return pd.read_sql(
            "SELECT * FROM cup_handle_signals ORDER BY scan_date DESC", con
        )


def get_active_tracking_df() -> pd.DataFrame:
    with _conn() as con:
        return pd.read_sql(
            """SELECT * FROM cup_handle_signals
               WHERE entry_triggered = 1
                 AND stopped_out = 0
                 AND t3_achieved = 0
                 AND status NOT IN ('Stopped Out', 'Target 3 Achieved', 'Expired')
               ORDER BY scan_date DESC
            """, con,
        )


def get_historical_signals_df() -> pd.DataFrame:
    with _conn() as con:
        return pd.read_sql(
            """SELECT * FROM cup_handle_signals
               WHERE status IN ('Stopped Out', 'Target 1 Achieved',
                                 'Target 2 Achieved', 'Target 3 Achieved', 'Expired')
               ORDER BY scan_date DESC
            """, con,
        )


def get_near_breakout_watchlist_df() -> pd.DataFrame:
    with _conn() as con:
        return pd.read_sql(
            """SELECT * FROM cup_handle_signals
               WHERE signal_type IN ('NEAR BREAKOUT', 'BASING')
                 AND entry_triggered = 0
               ORDER BY breakout_readiness_pct DESC NULLS LAST,
                        quality_score DESC
            """, con,
        )


def prune_expired_watchlist(today: Optional[date] = None) -> int:
    today = today or date.today()
    with _conn() as con:
        cur = con.execute(
            """UPDATE cup_handle_signals SET status = 'Expired'
               WHERE entry_triggered = 0
                 AND expiry_date IS NOT NULL
                 AND expiry_date < ?
                 AND status NOT IN ('Expired', 'Stopped Out')
            """,
            (today.isoformat(),),
        )
        return cur.rowcount
