from datetime import datetime, timezone

from app.adaptation.extractor import LearningSampleExtractor
from app.journal import CompletedTradeRecord


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
        CompletedTradeRecord(
            trade_id="trade-3",
            symbol="BTCUSDT",
            opened_at=datetime(2026, 4, 3, 0, 0, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 3, 8, 0, tzinfo=timezone.utc),
            score=76,
            risk_tag="normal",
            net_edge_bps=0.2,
            projected_net_edge_bps=2.8,
            basis_bps=4.4,
            realized_pnl_bps=0.1,
            max_drawdown_bps=5.1,
            hold_periods=7,
        ),
    ]


def test_learning_sample_extractor_maps_trade_journal_records() -> None:
    samples = LearningSampleExtractor().extract(make_records())

    assert len(samples) == 3
    assert samples[0].symbol == "BTCUSDT"
    assert samples[0].realized_pnl_bps == -1.8


def test_learning_sample_extractor_supports_symbol_and_limit_filters() -> None:
    samples = LearningSampleExtractor().extract(make_records(), symbol="BTCUSDT", limit=1)

    assert len(samples) == 1
    assert samples[0].symbol == "BTCUSDT"
