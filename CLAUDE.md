# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

This repository is at an early stage. It contains two modules — `src/traders/trade_executor.py` and `src/monitors/market_monitor.py` (with `src/monitors/__init__.py` re-exporting the public types) — and **no project metadata files**: no `README.md`, `pyproject.toml`/`setup.py`, `requirements.txt`, lockfile, tests, CI config, or linter config. There is also no `src/__init__.py` or `src/traders/__init__.py`. Treat anything not present as not yet decided — do not invent build, lint, or test commands; ask the user or propose a setup before adding tooling.

`market_monitor.py` imports `numpy`, but there is no requirements file pinning it. If you add tooling, capture this dependency.

The repository name (`pappertrading101`) and feature branch (`feature/kalshi-trading-bot`) indicate this is a **paper-trading bot for Kalshi prediction markets**.

## Architecture

The codebase follows a producer/consumer split:

- **Market monitor (`src/monitors/market_monitor.py`)** — `MarketMonitor` ingests `MarketData` points via `add_market_data` (keeping a rolling window of `2 * lookback_period`), runs detectors, and produces `Signal` objects via `generate_signal`. Detectors currently implemented:
  - `detect_momentum`: vol-scaled momentum (mean return / stdev of returns) over `lookback_period` (default 20). Triggers BUY/SELL when `|vol_scaled_momentum| > vol_threshold` (default 0.15). Confidence is `min(0.95, 0.5 + |vol_scaled_momentum|)`.
  - `detect_structural_sub_20_no`: flags BUY when latest price < $0.20, scaling confidence by how far below $0.20.
  - `detect_bundle_arbitrage`: BUY/SELL when a basket of complementary contract prices sums outside [0.95, 1.05]. **Not wired into `generate_signal`** — callers must invoke it directly.
  - `generate_signal` only fuses momentum and sub-20¢, picks the highest confidence, and gates on `confidence >= 0.60`.
- **Trade executor (`src/traders/trade_executor.py`)** — `TradeExecutor` validates a signal against `min_confidence` (default 0.60) and `account_balance` (default $5000), then constructs an `Order` (dataclass) and "executes" it locally by mutating in-memory state. There is no broker integration yet; the comment at line 74 (`# Execute order (in real implementation, would call Kalshi API)`) marks where the Kalshi API call belongs.

### ⚠️ Known interface mismatch between the two modules

`MarketMonitor` and `TradeExecutor` were introduced separately and **do not currently fit together**. Before relying on the integration, fix or confirm these:

1. **`signal_type` type mismatch.** `Signal.signal_type` is a `SignalType` enum (`SignalType.BUY`, `SignalType.SELL`). `TradeExecutor.execute_trade` compares it as a string: `if signal.signal_type == "BUY"` (line 81) and assigns it directly to `Order.order_type` (line 69, documented as `"BUY" or "SELL"`). With the current `Signal`, that comparison is always False — every monitor-produced trade would take the SELL branch and credit the account. Either pass `signal.signal_type.value` from the monitor side, switch the comparison to enum, or have the monitor emit strings.
2. **`signal_id` is dropped.** `Signal` now has its own `signal_id` (e.g. `SIG-YYYYMMDDHHMMSS-<contract_id>`), but `TradeExecutor` still sets `Order.signal_id = signal.contract_id` (line 68). Wire this through to `signal.signal_id`.
3. **Signal carries `price` and `quantity`** that the executor ignores — `execute_trade(signal, quantity, price)` takes them as separate arguments. Decide whether the monitor's suggestion is authoritative or advisory.

### Other design points worth preserving when extending

- **Order ID format** is `f"ORD-{YYYYMMDDHHMMSS}-{contract_id}"`; **Signal ID format** is `f"SIG-{YYYYMMDDHHMMSS}-{contract_id}"`. Both will collide if two are created for the same contract in the same second — fine for current single-threaded use, revisit before adding concurrency.
- `position_size_limit = 500` is set in `TradeExecutor.__init__` but **not enforced** in `can_execute_trade`. The comment ("Max per trade unless trade exceeds $500") is ambiguous — clarify the rule with the user before relying on it. `get_large_trades(threshold=500)` reads trades over the same threshold, but the two are not connected.
- `_calculate_win_rate` is a stub returning `0.0` (line 119 `# TODO`). Win-rate requires tracking position open/close pairs and PnL, which the current `Order` model does not represent — adding it likely means introducing a `Position` concept rather than extending `Order`.
- Buys subtract `quantity * price` from `account_balance` and sells add it (lines 81–84). This treats every sell as closing an existing position; there is no inventory check, so a sell with no prior buy will silently inflate the balance. Keep this in mind when writing tests or adding shorting logic.
- `MarketMonitor.market_history` only retains the last `2 * lookback_period` points per contract — long-term analysis or backtesting will need separate persistence.

## Conventions in use

- Python 3.10+ syntax: `tuple[bool, str]` return annotation in `trade_executor.py:42` requires 3.9+; PEP 604 unions are not yet used but `Optional[...]` is.
- Module-level `logger = logging.getLogger(__name__)`. Successful executions use `logger.info` with a leading `✓`; signal events use leading emoji glyphs (`🔔`, `📍`, `🎯`); failures use `logger.warning`. Match this when adding sibling modules.
- Dataclasses for value objects (`Order`, `Signal`, `MarketData`); `Enum` for closed sets (`OrderStatus`, `SignalType`). Prefer the same when adding positions, fills, etc.
- `src/monitors/__init__.py` re-exports the public types (`MarketMonitor`, `Signal`, `SignalType`, `MarketData`). `src/traders/` has no `__init__.py` yet — add one if the package needs a public API surface.

## Branching

Per the user's session instructions, development is pinned to `claude/add-claude-documentation-IuO7O`. Feature work happens on `feature/kalshi-trading-bot`. There is no `main` branch locally or on the fetched remote.
