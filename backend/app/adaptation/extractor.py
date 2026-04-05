from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from app.schemas.adaptation import LearningTradeSample, TradeJournalRecord


class TradeJournalExtractor:
    def extract(
        self,
        records: Sequence[TradeJournalRecord],
        *,
        symbol: str | None = None,
        recent_n: int | None = None,
        limit: int | None = None,
    ) -> list[LearningTradeSample]:
        filtered = [record for record in records if symbol is None or record.symbol == symbol]
        ordered = sorted(filtered, key=self._sort_key)
        window = recent_n if recent_n is not None else limit
        if window is not None:
            ordered = ordered[-window:] if window > 0 else []
        return [self._to_sample(record) for record in ordered]

    def _sort_key(self, record: TradeJournalRecord) -> tuple[datetime, str, str]:
        return (
            record.closed_at.astimezone(timezone.utc),
            record.symbol,
            record.trade_id,
        )

    def _to_sample(self, record: TradeJournalRecord) -> LearningTradeSample:
        return LearningTradeSample(
            trade_id=record.trade_id,
            symbol=record.symbol,
            closed_at=record.closed_at.astimezone(timezone.utc),
            score=record.score,
            risk_tag=record.risk_tag,
            net_edge_bps=record.net_edge_bps,
            projected_net_edge_bps=record.projected_net_edge_bps,
            basis_bps=record.basis_bps,
            realized_pnl_bps=record.realized_pnl_bps,
            max_drawdown_bps=record.max_drawdown_bps,
            hold_periods=record.hold_periods,
        )


LearningSampleExtractor = TradeJournalExtractor
