import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from app.adaptation.sample_store import LearningSampleStore
from app.adaptation.store import TuningStateStore
from app.audit import AuditEventStore
from app.backtest.dataset_store import BacktestDatasetStore
from app.core.settings import get_settings
from app.journal.store import TradeJournalStore
from app.ledger.store import TradeLedgerStore
from app.persistence.migration import JsonToMySQLBackfillService
from app.reconciliation.store import ExchangeOrderReportStore
from app.schemas.adaptation import LearningTradeSample, TuningState
from app.reconciliation.schemas import ExchangeOrderReport
from app.journal.schemas import CompletedTradeRecord
from app.ledger.schemas import TradeLedgerRecord
from app.audit.schemas import AuditEventRecord
from app.backtest.dataset_store import BacktestDataset
from app.backtest.engine import BacktestPeriod
from app.schemas.market import MarketSnapshot


pytestmark = pytest.mark.skipif(
    os.getenv("FUNDING_ARB_RUN_MYSQL_TESTS") != "1",
    reason="set FUNDING_ARB_RUN_MYSQL_TESTS=1 to run MySQL integration tests",
)


@pytest.fixture()
def mysql_backfill_settings(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    database = f"crypto_funding_arb_test_{uuid4().hex[:10]}"
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    paths = {
        "tuning": base / f"{uuid4().hex}-tuning.json",
        "samples": base / f"{uuid4().hex}-samples.json",
        "journal": base / f"{uuid4().hex}-journal.json",
        "datasets": base / f"{uuid4().hex}-datasets.json",
        "ledger": base / f"{uuid4().hex}-ledger.json",
        "audit": base / f"{uuid4().hex}-audit.json",
        "reports": base / f"{uuid4().hex}-reports.json",
    }
    monkeypatch.setenv("FUNDING_ARB_STORAGE_BACKEND", "mysql")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_HOST", "127.0.0.1")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_PORT", "3306")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_USER", "root")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_PASSWORD", "root")
    monkeypatch.setenv("FUNDING_ARB_MYSQL_DATABASE", database)
    monkeypatch.setenv("FUNDING_ARB_TUNING_STATE_PATH", str(paths["tuning"]))
    monkeypatch.setenv("FUNDING_ARB_LEARNING_SAMPLE_PATH", str(paths["samples"]))
    monkeypatch.setenv("FUNDING_ARB_TRADE_JOURNAL_PATH", str(paths["journal"]))
    monkeypatch.setenv("FUNDING_ARB_BACKTEST_DATASET_PATH", str(paths["datasets"]))
    monkeypatch.setenv("FUNDING_ARB_TRADE_LEDGER_PATH", str(paths["ledger"]))
    monkeypatch.setenv("FUNDING_ARB_AUDIT_EVENT_PATH", str(paths["audit"]))
    monkeypatch.setenv("FUNDING_ARB_EXCHANGE_ORDER_REPORT_PATH", str(paths["reports"]))
    get_settings.cache_clear()
    yield {name: str(path) for name, path in paths.items()}
    get_settings.cache_clear()


def _write_json(path: str, payload: object) -> None:
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _seed_source_files(paths: dict[str, str]) -> None:
    _write_json(
        paths["tuning"],
        TuningState(active_package_id="mysql-balanced", active_package_title="MySQL 平衡方案").model_dump(mode="json"),
    )
    _write_json(
        paths["samples"],
        [
            LearningTradeSample(
                trade_id="sample-1",
                symbol="BTCUSDT",
                closed_at=datetime(2026, 4, 5, 0, 0, tzinfo=timezone.utc),
                score=123.4,
                risk_tag="allow",
                projected_net_edge_bps=4.5,
                realized_pnl_bps=3.2,
            ).model_dump(mode="json")
        ],
    )
    _write_json(
        paths["journal"],
        [
            CompletedTradeRecord(
                trade_id="journal-1",
                symbol="BTCUSDT",
                opened_at=datetime(2026, 4, 4, 0, 0, tzinfo=timezone.utc),
                closed_at=datetime(2026, 4, 5, 0, 0, tzinfo=timezone.utc),
                score=110,
                risk_tag="allow",
                net_edge_bps=5.0,
                projected_net_edge_bps=4.2,
                basis_bps=1.2,
                realized_pnl_bps=3.1,
            ).model_dump(mode="json")
        ],
    )
    _write_json(
        paths["datasets"],
        [
            BacktestDataset(
                dataset_id="dataset-1",
                title="Funding Replay",
                periods=[
                    BacktestPeriod(
                        observed_at=datetime(2026, 4, 1, 0, 0, tzinfo=timezone.utc),
                        snapshots=[
                            MarketSnapshot(
                                symbol="BTCUSDT",
                                funding_rate=0.0008,
                                perp_mid=60010,
                                spot_mid=60000,
                                perp_spread_bps=0.4,
                                spot_spread_bps=0.3,
                            )
                        ],
                    )
                ],
            ).model_dump(mode="json")
        ],
    )
    _write_json(
        paths["ledger"],
        [
            TradeLedgerRecord(
                trade_id="ledger-1",
                mode="live",
                strategy_id="funding-arb",
                symbol="BTCUSDT",
                status="hedged",
                opened_at=datetime(2026, 4, 5, 0, 0, tzinfo=timezone.utc),
                spot_notional=15000,
                perp_notional=14990,
            ).model_dump(mode="json")
        ],
    )
    _write_json(
        paths["audit"],
        [
            AuditEventRecord(
                event_id="audit-1",
                event_type="execution.completed",
                source="execution-orchestrator",
                occurred_at=datetime(2026, 4, 5, 0, 1, tzinfo=timezone.utc),
                summary="Execution completed",
                payload={"trade_id": "ledger-1"},
                tags=["execution", "completed"],
            ).model_dump(mode="json")
        ],
    )
    _write_json(
        paths["reports"],
        [
            ExchangeOrderReport(
                report_id="report-1",
                venue="binance",
                order_id="order-1",
                trade_id="ledger-1",
                symbol="BTCUSDT",
                leg="spot",
                status="FILLED",
                executed_qty=0.2,
                cum_quote_qty=15000,
                updated_at=datetime(2026, 4, 5, 0, 2, tzinfo=timezone.utc),
            ).model_dump(mode="json")
        ],
    )


def test_json_to_mysql_backfill_imports_all_supported_sources(mysql_backfill_settings: dict[str, str]) -> None:
    _seed_source_files(mysql_backfill_settings)

    summary = JsonToMySQLBackfillService().run()

    assert summary.backend == "mysql"
    assert summary.sections["tuning_state"].imported == 1
    assert summary.sections["learning_samples"].imported == 1
    assert summary.sections["trade_journal"].imported == 1
    assert summary.sections["backtest_datasets"].imported == 1
    assert summary.sections["trade_ledger"].imported == 1
    assert summary.sections["audit_events"].imported == 1
    assert summary.sections["exchange_order_reports"].imported == 1
    assert TuningStateStore().load().active_package_id == "mysql-balanced"
    assert len(LearningSampleStore().load()) == 1
    assert len(TradeJournalStore().list()) == 1
    assert len(BacktestDatasetStore().list_datasets()) == 1
    assert len(TradeLedgerStore().list()) == 1
    assert len(AuditEventStore().list()) == 1
    assert len(ExchangeOrderReportStore().list()) == 1


def test_json_to_mysql_backfill_is_idempotent_for_duplicate_sources(mysql_backfill_settings: dict[str, str]) -> None:
    _seed_source_files(mysql_backfill_settings)
    service = JsonToMySQLBackfillService()

    first = service.run()
    second = service.run()

    assert first.sections["trade_ledger"].imported == 1
    assert second.sections["trade_ledger"].imported == 0
    assert second.sections["trade_ledger"].skipped == 1
    assert second.sections["audit_events"].imported == 0
    assert second.sections["audit_events"].skipped == 1
