from pathlib import Path
from uuid import uuid4

from app.adaptation.sample_store import LearningSampleStore
from app.schemas.adaptation import LearningTradeSample


def make_state_path() -> Path:
    base = Path("backend/.tmp-test-state")
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{uuid4().hex}-samples.json"


def make_samples() -> list[LearningTradeSample]:
    return [
        LearningTradeSample(
            symbol="BTCUSDT",
            score=95,
            risk_tag="guarded",
            net_edge_bps=-0.4,
            projected_net_edge_bps=2.6,
            basis_bps=6.8,
            realized_pnl_bps=-1.8,
            max_drawdown_bps=9.5,
            hold_periods=9,
        ),
        LearningTradeSample(
            symbol="ETHUSDT",
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


def test_learning_sample_store_appends_and_reloads_samples() -> None:
    store = LearningSampleStore(make_state_path())
    samples = make_samples()

    persisted = store.save(samples, mode="append")

    assert len(persisted) == 2
    assert len(store.load()) == 2
    assert store.load()[0].symbol == "BTCUSDT"


def test_learning_sample_store_can_replace_existing_samples() -> None:
    store = LearningSampleStore(make_state_path())
    store.save(make_samples(), mode="append")

    persisted = store.save(make_samples()[:1], mode="replace")

    assert len(persisted) == 1
    assert store.load()[0].symbol == "BTCUSDT"
