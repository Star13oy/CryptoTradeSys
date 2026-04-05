from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.ledger.schemas import TradeLedgerRecord
from app.ledger.store import TradeLedgerStore


def make_path() -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-ledger.json"


def make_records() -> list[TradeLedgerRecord]:
    return [
        TradeLedgerRecord(
            trade_id="ledger-1",
            mode="paper",
            strategy_id="funding-arb",
            symbol="BTCUSDT",
            status="open",
            opened_at=datetime(2026, 4, 5, 0, 0, tzinfo=timezone.utc),
            closed_at=None,
            net_exposure=0.0,
            spot_notional=15000,
            perp_notional=14980,
            realized_pnl=0.0,
            notes="paper open",
        ),
        TradeLedgerRecord(
            trade_id="ledger-2",
            mode="live",
            strategy_id="carry-v2",
            symbol="ETHUSDT",
            status="closed",
            opened_at=datetime(2026, 4, 4, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 4, 12, 0, tzinfo=timezone.utc),
            net_exposure=12.5,
            spot_notional=10000,
            perp_notional=9950,
            realized_pnl=42.8,
            notes="live close",
        ),
    ]


def test_trade_ledger_store_appends_and_loads_records() -> None:
    store = TradeLedgerStore(make_path())

    persisted = store.save(make_records(), mode="append")

    assert len(persisted) == 2
    assert len(store.list()) == 2
    assert store.list()[0].trade_id == "ledger-1"


def test_trade_ledger_store_can_replace_records() -> None:
    store = TradeLedgerStore(make_path())
    store.save(make_records(), mode="append")

    replaced = store.save(make_records()[:1], mode="replace")

    assert len(replaced) == 1
    assert store.list()[0].mode == "paper"
