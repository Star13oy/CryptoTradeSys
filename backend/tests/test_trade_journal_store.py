from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.journal import CompletedTradeRecord, TradeJournalStore


def make_path() -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-journal.json"


def make_records() -> list[CompletedTradeRecord]:
    return [
        CompletedTradeRecord(
            trade_id="trade-1",
            symbol="BTCUSDT",
            opened_at=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 1, 8, 0, tzinfo=timezone.utc),
            score=95,
            risk_tag="guarded",
            net_edge_bps=-0.4,
            projected_net_edge_bps=2.6,
            basis_bps=6.8,
            realized_pnl_bps=-1.8,
            max_drawdown_bps=9.5,
            hold_periods=9,
        ),
        CompletedTradeRecord(
            trade_id="trade-2",
            symbol="ETHUSDT",
            opened_at=datetime(2026, 4, 2, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 2, 8, 0, tzinfo=timezone.utc),
            score=82,
            risk_tag="guarded",
            net_edge_bps=-0.2,
            projected_net_edge_bps=2.2,
            basis_bps=7.4,
            realized_pnl_bps=-0.6,
            max_drawdown_bps=7.2,
            hold_periods=8,
        ),
    ]


def test_trade_journal_store_appends_and_loads_records() -> None:
    store = TradeJournalStore(make_path())

    persisted = store.save(make_records(), mode="append")

    assert len(persisted) == 2
    assert len(store.list()) == 2
    assert store.list()[0].trade_id == "trade-1"


def test_trade_journal_store_can_replace_records() -> None:
    store = TradeJournalStore(make_path())
    store.save(make_records(), mode="append")

    persisted = store.save(make_records()[:1], mode="replace")

    assert len(persisted) == 1
    assert store.list()[0].symbol == "BTCUSDT"
