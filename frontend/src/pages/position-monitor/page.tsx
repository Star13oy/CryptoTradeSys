import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";

import { apiClient } from "../../shared/api/client";
import type {
  EmergencyCloseResult,
  HedgeOverviewItem,
  HedgeOverviewResponse,
  HedgeRebalancePlan,
  HedgeRebalanceWorkerStatus,
  SafetyStateSnapshot,
} from "../../shared/contracts/console";
import { TerminalLayout } from "../../shared/ui/terminal-layout";

const timeFormatter = new Intl.DateTimeFormat("zh-CN", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

function formatCurrency(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatSymbol(symbol: string) {
  return symbol.endsWith("USDT") ? `${symbol.slice(0, -4)}/USDT` : symbol;
}

function healthLabel(health: HedgeOverviewItem["health"]) {
  switch (health) {
    case "healthy":
      return "健康";
    case "monitoring":
      return "观察中";
    case "rebalance_required":
      return "需再平衡";
    case "recovery_required":
      return "待恢复";
    default:
      return "未知";
  }
}

function buildExitConditions(selectedRow: HedgeOverviewItem | null, rebalancePlan: HedgeRebalancePlan | undefined) {
  if (!selectedRow) {
    return [
      { title: "等待持仓", status: "同步中", detail: "等待后端返回第一批活跃对冲仓位。", tone: "muted" },
    ];
  }

  return [
    {
      title: "当前暴露偏移",
      status: `${selectedRow.exposure_bps.toFixed(2)} bps`,
      detail: `净暴露 ${selectedRow.net_exposure.toFixed(2)} USDT`,
      tone:
        selectedRow.health === "recovery_required"
          ? "danger"
          : selectedRow.health === "rebalance_required"
            ? "accent"
            : "muted",
    },
    {
      title: "建议动作",
      status: rebalancePlan ? rebalancePlan.recommended_action : "等待",
      detail: rebalancePlan?.notes ?? "等待再平衡建议生成。",
      tone:
        rebalancePlan?.recommended_action === "recover_trade"
          ? "danger"
          : rebalancePlan?.recommended_action === "increase_perp_hedge" ||
              rebalancePlan?.recommended_action === "reduce_perp_hedge"
            ? "accent"
            : "muted",
    },
    {
      title: "最新事件",
      status: selectedRow.latest_event_severity ?? "info",
      detail: selectedRow.latest_event_summary ?? "暂无异常事件。",
      tone:
        selectedRow.latest_event_severity === "critical" || selectedRow.latest_event_severity === "error"
          ? "danger"
          : selectedRow.latest_event_severity === "warning"
            ? "accent"
            : "muted",
    },
  ];
}

function buildHedgeWorkerState(worker: HedgeRebalanceWorkerStatus | undefined) {
  if (!worker) {
    return "SYNCING";
  }
  if (!worker.enabled) {
    return "DISABLED";
  }
  if (!worker.configured) {
    return "MISCONFIGURED";
  }
  return worker.running ? "RUNNING" : "IDLE";
}

function canManuallyRebalance(action: HedgeRebalancePlan["recommended_action"] | undefined) {
  return action === "increase_perp_hedge" || action === "reduce_perp_hedge";
}

export function PositionMonitorPage() {
  const [selectedTradeId, setSelectedTradeId] = useState<string | null>(null);

  const overviewQuery = useQuery({
    queryKey: ["hedge-overview", 50],
    queryFn: () => apiClient.getHedgeOverview<HedgeOverviewResponse>({ exposure_limit_bps: 50 }),
  });

  const rows = overviewQuery.data?.items ?? [];

  useEffect(() => {
    if (rows.length === 0) {
      setSelectedTradeId(null);
      return;
    }
    if (!selectedTradeId || !rows.some((row) => row.trade_id === selectedTradeId)) {
      setSelectedTradeId(rows[0].trade_id);
    }
  }, [rows, selectedTradeId]);

  const selectedRow = rows.find((row) => row.trade_id === selectedTradeId) ?? null;
  const rebalancePlanQuery = useQuery({
    queryKey: ["hedge-rebalance-plan", selectedTradeId, 50],
    queryFn: () => apiClient.getHedgeRebalancePlan<HedgeRebalancePlan>(selectedTradeId as string, { exposure_limit_bps: 50 }),
    enabled: selectedTradeId !== null,
  });
  const hedgeWorkerQuery = useQuery({
    queryKey: ["hedge-rebalance-worker"],
    queryFn: () => apiClient.getHedgeRebalanceWorker<HedgeRebalanceWorkerStatus>(),
  });
  const safetyQuery = useQuery<SafetyStateSnapshot>({
    queryKey: ["safety-state"],
    queryFn: () => apiClient.getSafetyState<SafetyStateSnapshot>(),
    staleTime: 10_000,
  });
  const hedgeWorkerRunMutation = useMutation({
    mutationFn: () => apiClient.runHedgeRebalanceWorker<HedgeRebalanceWorkerStatus>(),
    onSuccess: async () => {
      await Promise.all([hedgeWorkerQuery.refetch(), overviewQuery.refetch(), rebalancePlanQuery.refetch()]);
    },
  });
  const manualRebalanceMutation = useMutation({
    mutationFn: () => {
      if (!selectedRow) {
        throw new Error("No selected trade");
      }
      return apiClient.runHedgeRebalanceAuto(selectedRow.trade_id);
    },
    onSuccess: async () => {
      await Promise.all([overviewQuery.refetch(), rebalancePlanQuery.refetch()]);
    },
  });
  const reduceOnlyMutation = useMutation({
    mutationFn: () => apiClient.setReduceOnly<SafetyStateSnapshot>({ trade_id: selectedTradeId ?? undefined }),
    onSuccess: () => safetyQuery.refetch(),
  });
  const pauseMutation = useMutation({
    mutationFn: () => apiClient.pauseTrade<SafetyStateSnapshot>({ trade_id: selectedTradeId ?? undefined }),
    onSuccess: () => safetyQuery.refetch(),
  });
  const panicSellMutation = useMutation({
    mutationFn: () => apiClient.panicSell<EmergencyCloseResult>({ trade_id: selectedTradeId ?? undefined }),
    onSuccess: () => {
      safetyQuery.refetch();
      overviewQuery.refetch();
    },
  });

  const summaryCards = useMemo(() => {
    const totalNotional = rows.reduce((sum, row) => sum + Math.max(row.spot_notional, row.perp_notional), 0);
    const totalExposure = rows.reduce((sum, row) => sum + Math.abs(row.net_exposure), 0);
    const recoveryCount = overviewQuery.data?.recovery_required_count ?? 0;
    return [
      { label: "当前持仓数", value: String(overviewQuery.data?.active_trade_count ?? 0).padStart(2, "0"), hint: `${recoveryCount} 组待恢复` },
      { label: "总名义仓位", value: formatCurrency(totalNotional), hint: "按活跃仓位最大腿名义值汇总" },
      { label: "净暴露敞口", value: formatCurrency(totalExposure), hint: "用于再平衡与恢复优先级排序" },
    ];
  }, [overviewQuery.data, rows]);

  const exitConditions = buildExitConditions(selectedRow, rebalancePlanQuery.data);
  const hedgeWorker = hedgeWorkerQuery.data;
  const hedgeWorkerState = buildHedgeWorkerState(hedgeWorker);
  const manualRebalanceEnabled = canManuallyRebalance(rebalancePlanQuery.data?.recommended_action) && selectedRow !== null;
  const footerContent = (
    <>
      <span>ACTIVE HEDGES / {overviewQuery.data?.active_trade_count ?? 0} 组</span>
      <span>
        {overviewQuery.data
          ? `最近更新 ${timeFormatter.format(new Date(overviewQuery.data.generated_at))}`
          : "等待持仓摘要同步"}
      </span>
      <span>{hedgeWorkerQuery.isError ? "HEDGE WORKER OFFLINE" : `HEDGE ${hedgeWorkerState}`}</span>
      <span>REBALANCE LIMIT / 50 bps</span>
    </>
  );

  return (
    <TerminalLayout activePath="/positions" footerContent={footerContent}>
      <section className="proto-page">
        <header className="proto-header">
          <div>
            <h2 className="proto-page__title">持仓监控</h2>
            <p className="proto-page__subtitle">实时对冲仓位、退出条件与风险热区联动总览。</p>
          </div>
        </header>

        <section className="proto-stat-grid proto-stat-grid--three">
          {summaryCards.map((card) => (
            <article className="proto-stat-card" key={card.label}>
              <p>{card.label}</p>
              <strong>{card.value}</strong>
              <span>{card.hint}</span>
            </article>
          ))}
        </section>

        <section className="proto-main-grid">
          <article className="proto-panel proto-panel--table">
            <div className="proto-panel__header">
              <div>
                <p className="proto-panel__eyebrow">Execution Matrix</p>
                <h3>活跃对冲仓位 (Active Hedges)</h3>
              </div>
              <div className="proto-chip-row">
                <span className="proto-chip proto-chip--active">全部</span>
                <span className="proto-chip">{overviewQuery.data?.rebalance_required_count ?? 0} 组需再平衡</span>
              </div>
            </div>

            {overviewQuery.isPending ? <p className="panel-state">正在同步持仓监控数据</p> : null}
            {overviewQuery.isError ? <p className="panel-alert">持仓监控数据暂时不可用</p> : null}

            <div className="proto-table-shell">
              <div className="proto-table-row proto-table-row--positions proto-table-row--head">
                <span>交易对</span>
                <span>对冲偏离</span>
                <span>运行模式</span>
                <span>状态</span>
                <span>再平衡建议</span>
                <span>操作</span>
              </div>
              {!overviewQuery.isPending && !overviewQuery.isError && rows.length === 0 ? (
                <div className="table-empty">暂无活跃持仓</div>
              ) : null}
              {rows.map((row) => (
                <button
                  className={`proto-table-row proto-table-row--positions${selectedTradeId === row.trade_id ? " scanner-table--active" : ""}`}
                  key={row.trade_id}
                  type="button"
                  onClick={() => setSelectedTradeId(row.trade_id)}
                >
                  <div>
                    <strong>{formatSymbol(row.symbol)}</strong>
                    <span className="proto-meta">{row.mode.toUpperCase()} / {row.trade_id}</span>
                  </div>
                  <div>
                    <div className="proto-progress">
                      <div className="proto-progress__fill" style={{ width: `${Math.min(100, Math.max(row.exposure_bps, 8))}%` }} />
                    </div>
                    <span className="proto-meta">{row.exposure_bps.toFixed(2)} bps</span>
                  </div>
                  <span className="proto-pill">{row.mode.toUpperCase()}</span>
                  <span>
                    {healthLabel(row.health)}
                    {safetyQuery.data?.reduce_only_trades.includes(row.trade_id) && (
                      <span className="proto-chip proto-chip--active" style={{ marginLeft: "4px" }}>仅减仓</span>
                    )}
                    {safetyQuery.data?.paused_trades.includes(row.trade_id) && (
                      <span className="proto-chip proto-chip--active" style={{ marginLeft: "4px" }}>已暂停</span>
                    )}
                  </span>
                  <div>
                    <strong className="proto-text--accent">
                      {selectedTradeId === row.trade_id && rebalancePlanQuery.data
                        ? rebalancePlanQuery.data.recommended_action
                        : row.health === "rebalance_required"
                          ? "等待建议"
                          : "monitor_only"}
                    </strong>
                    <span className="proto-meta">{formatCurrency(Math.abs(row.net_exposure))}</span>
                  </div>
                  <span className="proto-meta">查看</span>
                </button>
              ))}
            </div>
          </article>

          <div className="proto-side-stack">
            <article className="proto-panel">
              <div className="proto-panel__header">
                <div>
                  <p className="proto-panel__eyebrow">Exit Conditions</p>
                  <h3>退出条件详情</h3>
                </div>
              </div>

              {rebalancePlanQuery.isPending && selectedTradeId ? <p className="panel-state panel-state-subtle">正在生成再平衡建议</p> : null}
              {rebalancePlanQuery.isError ? <p className="panel-alert">再平衡建议暂时不可用</p> : null}

              <div className="proto-alert-list">
                {exitConditions.map((item) => (
                  <div className={`proto-alert proto-alert--${item.tone}`} key={item.title}>
                    <div className="proto-alert__topline">
                      <span>{item.title}</span>
                      <strong>{item.status}</strong>
                    </div>
                    <p>{item.detail}</p>
                  </div>
                ))}
              </div>

              <div className="proto-action-grid">
                <button
                  className="proto-button proto-button--ghost"
                  type="button"
                  onClick={() => reduceOnlyMutation.mutate()}
                  disabled={!selectedTradeId || reduceOnlyMutation.isPending}
                >
                  {reduceOnlyMutation.isPending ? "设置中..." : "仅减仓"}
                </button>
                <button
                  className="proto-button proto-button--ghost"
                  type="button"
                  onClick={() => pauseMutation.mutate()}
                  disabled={!selectedTradeId || pauseMutation.isPending}
                >
                  {pauseMutation.isPending ? "暂停中..." : "暂停"}
                </button>
                <button
                  className="proto-button proto-button--accent"
                  type="button"
                  onClick={() => manualRebalanceMutation.mutate()}
                  disabled={!manualRebalanceEnabled || manualRebalanceMutation.isPending}
                >
                  {manualRebalanceMutation.isPending ? "执行中..." : "执行再平衡"}
                </button>
                <button
                  className="proto-button proto-button--danger"
                  type="button"
                  onClick={() => {
                    if (selectedTradeId && window.confirm(`确认强制平仓 ${selectedTradeId}？此操作不可撤销！`)) {
                      panicSellMutation.mutate();
                    }
                  }}
                  disabled={!selectedTradeId || panicSellMutation.isPending}
                >
                  {panicSellMutation.isPending ? "平仓中..." : "立即强平 (Panic Sell)"}
                </button>
              </div>
            </article>

            <article className="proto-panel">
              <div className="proto-panel__header">
                <div>
                  <p className="proto-panel__eyebrow">Auto Hedge Rebalance</p>
                  <h3>Auto Hedge Rebalance</h3>
                </div>
              </div>

              <div className="proto-risk-badge">{hedgeWorkerState}</div>
              <span className="proto-meta">
                {hedgeWorker ? `累计执行 ${hedgeWorker.total_executed_rebalances} 次` : "等待 hedge worker 状态同步"}
              </span>
              <div className="proto-meter">
                <div className="proto-meter__row">
                  <span>最近尝试</span>
                  <strong>{hedgeWorker ? `${hedgeWorker.last_attempted_count} 条` : "--"}</strong>
                </div>
                <div className="proto-progress">
                  <div
                    className="proto-progress__fill"
                    style={{ width: `${Math.min(100, (hedgeWorker?.last_attempted_count ?? 0) * 26)}%` }}
                  />
                </div>
              </div>
              <div className="proto-meter">
                <div className="proto-meter__row">
                  <span>最近执行</span>
                  <strong>{hedgeWorker ? `${hedgeWorker.last_executed_count} 条` : "--"}</strong>
                </div>
                <div className="proto-progress">
                  <div
                    className={`proto-progress__fill${
                      (hedgeWorker?.total_failed_runs ?? 0) > 0 ? " proto-progress__fill--warning" : ""
                    }`}
                    style={{ width: `${Math.min(100, (hedgeWorker?.last_executed_count ?? 0) * 26)}%` }}
                  />
                </div>
              </div>

              <div className="proto-action-grid proto-action-grid--two">
                <button className="proto-button proto-button--ghost" type="button">
                  间隔 {hedgeWorker?.interval_seconds ?? 30}s
                </button>
                <button
                  className="proto-button proto-button--ghost"
                  type="button"
                  onClick={() => hedgeWorkerRunMutation.mutate()}
                  disabled={hedgeWorkerRunMutation.isPending}
                >
                  {hedgeWorkerRunMutation.isPending ? "运行中..." : "运行再平衡"}
                </button>
              </div>
            </article>

            <article className="proto-panel">
              <div className="proto-panel__header">
                <div>
                  <p className="proto-panel__eyebrow">Live Risk</p>
                  <h3>实时风险热图</h3>
                </div>
                <span className="proto-tag-live">LIVE</span>
              </div>

              <div className="proto-heatbars">
                {rows.length > 0
                  ? rows.slice(0, 10).map((row) => (
                      <div
                        className="proto-heatbars__bar"
                        key={row.trade_id}
                        style={{ height: `${Math.max(18, Math.min(100, row.exposure_bps))}%` }}
                      />
                    ))
                  : [52, 76, 66, 100, 30, 84, 68, 52, 74, 48].map((height, index) => (
                      <div className="proto-heatbars__bar" key={`${height}-${index}`} style={{ height: `${height}%` }} />
                    ))}
              </div>
            </article>
          </div>
        </section>
      </section>
    </TerminalLayout>
  );
}
