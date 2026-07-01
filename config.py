"""
NSE Cup & Handle Scanner - Configuration
==========================================
All tuneable constants live here. Detection thresholds are
deliberately loose (maximum sensitivity); entry/exit thresholds are
deliberately strict (capital protection). See spec v3 Parts 3 & 4 for
the reasoning behind each value — do not tighten detection thresholds
or loosen entry/exit thresholds without re-reading that rationale.
"""

from __future__ import annotations

from pathlib import Path

# ─── Paths ──────────────────────────────────────────────────────────────────
DATA_DIR      = Path("data")
DAILY_DIR     = DATA_DIR / "daily"
REPORTS_DIR   = Path("reports")
SIGNALS_DB    = DATA_DIR / "scanner.db"
LOGS_DIR      = Path("logs")

for _d in (DATA_DIR, DAILY_DIR, REPORTS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ─── Benchmarks ────────────────────────────────────────────────────────────
NIFTY50_SYMBOL   = "^NSEI"
NIFTY500_SYMBOL  = "^CNX500"

# ─── Portfolio / position sizing ──────────────────────────────────────────
PORTFOLIO_VALUE       = 500_000     # INR, configurable
RISK_PER_TRADE_PCT    = 1.0         # % of portfolio risked per trade

# ─── Data download ─────────────────────────────────────────────────────────
BATCH_SIZE                = 50
BATCH_DELAY_SECONDS       = 3
MAX_RETRIES                = 5
RATELIMIT_RETRY_WAIT_MIN   = 2      # minutes, base for exponential backoff
EXPONENTIAL_BASE           = 2.0
TIMEOUT_RETRY_WAIT_SEC     = 30

# ─── Minimum bars required to scan a symbol on each timeframe ────────────
MIN_DAILY_BARS    = 150
MIN_WEEKLY_BARS   = 40
MIN_MONTHLY_BARS  = 12

# ─── Cup detection — lookback window sizes (in bars) ──────────────────────
DAILY_CUP_MIN_BARS    = 30
DAILY_CUP_MAX_BARS    = 500
WEEKLY_CUP_MIN_BARS   = 8
WEEKLY_CUP_MAX_BARS   = 104
MONTHLY_CUP_MIN_BARS  = 5
MONTHLY_CUP_MAX_BARS  = 36

CUP_LOOKBACKS = {
    "daily":   (DAILY_CUP_MIN_BARS, DAILY_CUP_MAX_BARS),
    "weekly":  (WEEKLY_CUP_MIN_BARS, WEEKLY_CUP_MAX_BARS),
    "monthly": (MONTHLY_CUP_MIN_BARS, MONTHLY_CUP_MAX_BARS),
}

MIN_BARS_BY_TIMEFRAME = {
    "daily":   MIN_DAILY_BARS,
    "weekly":  MIN_WEEKLY_BARS,
    "monthly": MIN_MONTHLY_BARS,
}

# ─── Cup detection — the ONLY hard gate ───────────────────────────────────
CUP_MIN_RECOVERY_PCT  = 0.50   # right rim must recover >=50% of the decline

# Left rim finding
LEFT_RIM_WINDOW_FRACTION = 0.25   # search first 25% of window for left rim
LEFT_RIM_ROLLING_BARS    = 5      # rolling max window to find local peaks
LEFT_RIM_MIN_PCT_OF_HIGH = 0.90   # left rim must be >=90% of window's high

# Recency requirement — current price must still be reasonably close
# to the right rim (we want CURRENT setups, not historical/resolved ones)
CURRENT_PRICE_MIN_PCT_OF_RIM    = 0.80   # current price >= 80% of right rim

# ─── Handle detection (relaxed geometry) ──────────────────────────────────
HANDLE_MAX_DEPTH_RATIO       = 0.50   # handle depth <= 50% of cup depth
HANDLE_MIN_PCT_FROM_BOTTOM   = 0.30   # handle low >= 30% up from cup bottom
HANDLE_MAX_BREAKOUT_PCT      = 0.05   # handle high can't exceed right rim by >5%

HANDLE_SEARCH_BARS = {
    # (min_bars, max_bars) after the right rim to search for a handle
    "daily":   (3, 65),
    "weekly":  (1, 15),
    "monthly": (1, 6),
}

# ─── Cup depth classification bands (display only, never gates) ──────────
CUP_DEPTH_BANDS = [
    ("Shallow Cup",    0.0,  15.0),
    ("Classic Cup",    15.0, 35.0),
    ("Deep Cup",       35.0, 50.0),
    ("Very Deep Cup",  50.0, 70.0),
    ("Crash Recovery", 70.0, 9999.0),
]
CUP_VERY_SHALLOW_THRESHOLD = 5.0   # below this -> "verify manually" flag

# ─── Prior uptrend tag bands (display only, never gates) ──────────────────
PRIOR_UPTREND_STRONG_PCT    = 30.0   # >= this -> "Strong Continuation"
PRIOR_UPTREND_MODERATE_PCT  = 10.0   # >= this -> "Moderate Continuation"
# below PRIOR_UPTREND_MODERATE_PCT -> "Possible Bottoming Pattern"

# ─── Quality score weights ─────────────────────────────────────────────────
QS_RIM_SYMMETRY      = {"high": 25, "mid": 15, "low": 5}     # right/left rim ratio
QS_CUP_DEPTH         = {"classic": 20, "near": 10, "far": 5, "crash": 2}
QS_PRIOR_UPTREND     = {"strong": 15, "moderate": 8, "weak": 3}
QS_VOLUME_DRYUP      = {"full": 10, "partial": 5, "none": 0}
QS_SHAPE             = {"u_shape": 10, "v_shape": 5, "irregular": 0}
QS_RS_RATING         = {"leader": 10, "rising": 5, "lagging": 0}
QS_MTF_CONFLUENCE    = 10
QS_HANDLE_MAX        = 20   # handle quality sub-score, added on top
QUALITY_SCORE_CAP    = 100

QUALITY_BAND_HIGH    = 70   # >= this -> "High Quality" (green)
QUALITY_BAND_MEDIUM  = 40   # >= this -> "Medium Quality" (yellow)
# below QUALITY_BAND_MEDIUM -> "Low Quality" (white)

# ─── Handle quality sub-score thresholds ───────────────────────────────────
HQ_VOL_DRYUP_FULL_RATIO     = 0.70   # handle avg vol <= 70% of cup avg -> 6pts
HQ_VOL_DRYUP_PARTIAL_RATIO  = 1.00   # <= 100% -> 3pts, else 0
HQ_VOL_DRYUP_PTS            = {"full": 6, "partial": 3, "none": 0}

HQ_TIGHTNESS_FULL_RATIO     = 0.60   # handle range ratio <= 60% of cup -> 5pts
HQ_TIGHTNESS_PARTIAL_RATIO  = 0.90   # <= 90% -> 3pts, else 0
HQ_TIGHTNESS_PTS            = {"full": 5, "partial": 3, "none": 0}

HQ_HIGHER_LOWS_PTS          = {"sequential": 5, "second_half": 2, "none": 0}

HQ_CLOSE_HIGH_FULL          = 0.65   # avg close position >= 0.65 -> 4pts
HQ_CLOSE_HIGH_PARTIAL       = 0.45   # >= 0.45 -> 2pts, else 0
HQ_CLOSE_HIGH_PTS           = {"full": 4, "partial": 2, "none": 0}

# ─── Signal type thresholds ─────────────────────────────────────────────────
NEAR_BREAKOUT_THRESHOLD = 0.03   # within 3% below pivot
BASING_THRESHOLD        = 0.10   # 3-10% below pivot
# >10% below pivot -> EARLY STAGE
EXTENDED_THRESHOLD      = 0.05   # >5% above pivot -> EXTENDED

# ─── Breakout Readiness weights (Part 3I) ──────────────────────────────────
READINESS_WEIGHTS = {
    "near_pivot":      25,
    "tight_handle":    20,
    "rising_rs":       20,
    "atr_contracting": 20,
    "above_50ma":      15,
}
READINESS_NEAR_PIVOT_PCT = 3.0    # within 3% of pivot, either side
READINESS_BAND_HIGH      = 80     # >= this -> bold green
READINESS_BAND_MEDIUM    = 50     # >= this -> yellow background

# ─── High-Conviction Breakout filter ("Confirmed Breakouts" tab) ─────────
# ALL conditions must be met simultaneously for a signal to appear on
# this tab. The idea is to produce a very short, genuinely actionable
# list — typically 5-30 stocks on any given day. Do NOT loosen these
# to inflate the list; the value of this tab is its selectivity.
HCB_SIGNAL_TYPES          = {"BREAKOUT NOW", "NEAR BREAKOUT"}
HCB_MIN_READINESS         = 80     # Breakout Readiness >= 80% (4-5 factors)
HCB_MIN_QUALITY           = 60     # pattern must be structurally solid
HCB_MIN_VOLUME_RATIO      = 1.40   # volume >= 140% of avg (same as entry gate)
HCB_MAX_PRICE_VS_PIVOT    = 5.0    # not more than 5% above pivot (not extended)
HCB_MIN_PRICE_VS_PIVOT    = -3.0   # not more than 3% below pivot (within zone)
HCB_MIN_HANDLE_QUALITY    = 10     # handle must be tight (>= 10/20)
HCB_REQUIRE_HANDLE        = True   # Cup Only excluded — no handle, no certainty


BREAKOUT_BUFFER_INR        = 0.10
BREAKOUT_BUFFER_PCT        = 0.001   # used instead of flat INR above ₹1000
BREAKOUT_BUFFER_PRICE_CUTOFF = 1000.0

VOLUME_CONFIRM_DAILY   = 1.40    # 140% of 50-bar avg volume
VOLUME_CONFIRM_WEEKLY  = 1.20    # 120% of 10-bar avg volume (weekly/monthly)
VOLUME_AVG_BARS_DAILY   = 50
VOLUME_AVG_BARS_WEEKLY  = 10

RSI_WEAK_MOMENTUM_THRESHOLD = 45.0

# ─── Stop loss (STRICT) ─────────────────────────────────────────────────────
MAX_STOP_PCT          = 0.08    # 8% hard cap, never exceeded
STOP_ATR_MULTIPLIER   = 1.0
CUP_ONLY_STOP_RECOVERY_FRACTION = 0.20   # cup_bottom + 20% of cup height

# ─── Targets (O'Neil / CANSLIM) ─────────────────────────────────────────────
T1_GAIN_PCT          = 0.20    # +20% first profit target
T1_FAST_DAYS         = 15      # if hit in < this many trading days -> hold rule
FIBONACCI_EXTENSION  = 1.618
MIN_RR_T2            = 2.0     # flag (not exclude) if below this

TRAILING_STOP_PCT    = 0.07    # 7% trailing stop from post-entry closing high
STUCK_BASE_WEEKS      = 8       # no new high in N weeks -> flag

# ─── RS Rating ───────────────────────────────────────────────────────────────
RS_LEADER_THRESHOLD   = 85
RS_RISING_THRESHOLD   = 70
RS_LAGGARD_THRESHOLD  = 50
RS_TREND_LOOKBACK_WEEKS = 4

# RS weighted-return blend: (weight, lookback_bars) computed in indicators.py
RS_WEIGHTS = {
    "3m":  (0.4, 63),    # ~63 trading days = 3 months
    "6m":  (0.2, 126),
    "9m":  (0.2, 189),
    "12m": (0.2, 252),
}

# ─── Liquidity filter (applied AFTER detection, gates entry/exit only) ────
MIN_PRICE          = 10.0
MIN_AVG_VOLUME     = 50_000
LIQUIDITY_LOOKBACK_BARS = 20

# ─── Pattern recency (skip stale detections) ──────────────────────────────
STALE_PATTERN_MAX_BARS = {
    "daily":   60,
    "weekly":  20,
    "monthly": 12,
}

# ─── Watchlist / signal expiry ─────────────────────────────────────────────
WATCHLIST_EXPIRY_DAYS = 90

# ─── Indicator periods ──────────────────────────────────────────────────────
RSI_PERIOD   = 14
ADX_PERIOD   = 14
ATR_PERIOD   = 14
MA_PERIODS_DAILY   = [50, 150, 200]
MA_PERIODS_WEEKLY  = [10, 30, 40]     # roughly equivalent to 50/150/200 daily
MA_PERIODS_MONTHLY = [3, 7, 9]        # roughly equivalent on monthly bars
