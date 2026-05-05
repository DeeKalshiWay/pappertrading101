# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

This repository is at a very early stage. As of writing it contains a single module, `src/traders/trade_executor.py`, and no project metadata files (no `README.md`, `pyproject.toml`/`setup.py`, `requirements.txt`, lockfile, tests, CI config, or linter config). Treat anything not present as not yet decided — do not invent build, lint, or test commands; ask the user or propose a setup before adding tooling.

The repository name (`pappertrading101`) and the active feature branch (`feature/kalshi-trading-bot`) indicate this is intended to be a **paper-trading bot for Kalshi prediction markets**.

## Architecture

The codebase is being built around a producer/consumer split that is only partly implemented:

- **Market monitor (not yet in the repo)** — expected to produce `signal` objects. `TradeExecutor` consumes these but never imports a concrete type; it accesses `signal.confidence`, `signal.contract_id`, `signal.signal_type` (string `"BUY"` or `"SELL"`), and `signal.title` via duck typing. When you add the monitor, keep that interface stable or update both sides together.
- **Trade executor (`src/traders/trade_executor.py`)** — `TradeExecutor` validates a signal against a confidence threshold and account balance, then constructs an `Order` (dataclass) and "executes" it locally by mutating in-memory state. There is no broker integration yet; the comment at line 74 (`# Execute order (in real implementation, would call Kalshi API)`) marks where the Kalshi API call belongs.

Design points worth preserving when extending:

- Order IDs are `f"ORD-{YYYYMMDDHHMMSS}-{contract_id}"`. They will collide if two orders for the same contract are created in the same second — fine for current single-threaded use, revisit before adding concurrency.
- `Order.signal_id` is currently set to `signal.contract_id` (line 68), not to a real signal identifier. If/when signals get their own IDs, fix this assignment rather than papering over it downstream.
- `position_size_limit = 500` is set in `__init__` but **not enforced** anywhere in `can_execute_trade`. The docstring/comment ("Max per trade unless trade exceeds $500") is ambiguous — clarify the rule with the user before relying on it.
- `_calculate_win_rate` is a stub returning `0.0` (line 119 `# TODO`). Win-rate requires tracking position open/close pairs and PnL, which the current `Order` model does not represent. Adding it likely means introducing a `Position` concept rather than extending `Order`.
- Buys subtract `quantity * price` from `account_balance` and sells add it (lines 81–84). This treats every sell as closing an existing position; there is no inventory check, so a sell with no prior buy will silently inflate the balance. Keep this in mind when writing tests or adding shorting logic.

## Conventions in use

- Python 3.10+ syntax (`tuple[bool, str]` return annotation at line 42 requires 3.9+; `dataclass` + `field(default_factory=...)` is standard).
- Module-level `logger = logging.getLogger(__name__)`; user-facing execution lines use `logger.info` with a leading `✓`, failures use `logger.warning`. Match this when adding sibling modules.
- Dataclasses for value objects (`Order`), `Enum` for closed sets (`OrderStatus`). Prefer the same when adding signals, positions, etc.

## Branching

The user's instructions for this session pin development to `claude/add-claude-documentation-OOH0C`. Feature work is happening on `feature/kalshi-trading-bot`. There is no `main` branch yet locally or on the remote that's been fetched.
