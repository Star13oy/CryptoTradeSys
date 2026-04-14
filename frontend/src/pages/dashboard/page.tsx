import { useQuery, useMutation } from "@tanstack/react-query";

import { apiGet } from "../../shared/api/client";
import { apiClient } from "../../shared/api/client";
import type { DashboardSummary, AccountSummary, SafetyStateSnapshot, EmergencyCloseResult } from "../../shared/contracts/console";
import { TerminalLayout } from "../../shared/ui/terminal-layout";

const timeFormatter = new Intl.DateTimeFormat("zh-CN", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

function describeMarketSource(source: string, marketLabel: string) {
  return `${marketLabel}${source === "depth" ? "深度回退" : "主盘口"}`;
}

function formatSignedBps(value: number) {
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}${value.toFixed(2)} bps`;
}

function formatQuotePair(bid: number | undefined, ask: number | undefined) {
  if (bid === undefined || ask === undefined) {
    return "-- / --";
  }
  return `${bid.toFixed(2)} / ${ask.toFixed(2)}`;
}

function formatFixed(value: number | undefined, digits = 2) {
  if (value === undefined) {
    return "--";
  }
  return value.toFixed(digits);
}

function formatCoverage(summary: DashboardSummary) {
  const denominator = Math.max(summary.market_status.requested_symbols, 1);
  return `${((summary.market_status.quoted_symbols / denominator) * 100).toFixed(1)}%`;
}

function formatRiskLabel(riskState: string | undefined) {
  switch (riskState) {
    case "normal":
      return "低 (ALPHA)";
    case "guarded":
      return "中 (GUARDED)";
    case "halted":
      return "高 (HALT)";
    default:
      return "同步中";
  }
}

function buildDistribution(summary: DashboardSummary | undefined) {
  if (!summary || summary.top_opportunities.length === 0) {
    return [
      { label: "USDT", value: 54, color: "#6bd8cb" },
      { label: "BTC", value: 28, color: "#f5c770" },
      { label: "ETH", value: 18, color: "#f18d8a" },
    ];
  }

  const leadingRows = summary.top_opportunities.slice(0, 3);
  const totalScore = leadingRows.reduce((sum, row) => sum + row.score, 0) || 1;

  return leadingRows.map((row, index) => ({
    label: row.symbol.replace("USDT", ""),
    value: Math.max(8, Math.round((row.score / totalScore) * 100)),
    color: ["#6bd8cb", "#f5c770", "#f18d8a"][index] ?? "#7a83ff",
  }));
}

export function DashboardPage() {
  const summaryQuery = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => apiGet<DashboardSummary>("/api/v1/dashboard/summary"),
  });

  const accountQuery = useQuery<AccountSummary>({
    queryKey: ["account-summary"],
    queryFn: () => apiClient.getAccountSummary<AccountSummary>(),
    staleTime: 30_000,
  });

  const safetyQuery = useQuery<SafetyStateSnapshot>({
    queryKey: ["safety-state"],
    queryFn: () => apiClient.getSafetyState<SafetyStateSnapshot>(),
    staleTime: 10_000,
  });

  const emergencyCloseMutation = useMutation({
    mutationFn: () => apiClient.emergencyCloseAll<EmergencyCloseResult>(),
    onSuccess: () => {
      safetyQuery.refetch();
    },
  });

  const data = summaryQuery.data;
  const averageEdge =
    data && data.top_opportunities.length > 0
      ? data.top_opportunities.reduce((sum, row) => sum + row.net_edge_bps, 0) /
        data.top_opportunities.length
      : 0;
  const distribution = buildDistribution(data);
  const topOpportunity = data?.top_opportunities[0];
  const distributionGradient = distribution.reduce<string[]>((segments, segment, index) => {
    const previousTotal = distribution
      .slice(0, index)
      .reduce((sum, currentSegment) => sum + currentSegment.value, 0);
    const nextTotal = previousTotal + segment.value;
    segments.push(`${segment.color} ${previousTotal}% ${nextTotal}%`);
    return segments;
  }, []);
  const riskLogs = [
    summaryQuery.isError
      ? "行情网关返回异常，进入人工关注态。"
      : data
        ? `最近一次扫描在 ${timeFormatter.format(new Date(data.generated_at))} 完成。`
        : "等待首批市场快照回传。",
    data
      ? `${describeMarketSource(data.market_status.spot_source, "现货")} / ${describeMarketSource(
          data.market_status.perp_source,
          "永续"
        )}`
      : "主盘口状态同步中。",
    data
      ? `当前已覆盖 ${data.market_status.quoted_symbols} / ${data.market_status.requested_symbols} 个标的。`
      : "报价覆盖率尚未就绪。",
    data?.market_status.degraded ? "系统触发深度回退，执行层应放缓开仓。" : "熔断状态已就绪，允许继续观察。",
  ];
  const metricCards = [
    {
      label: "总权益 (USDT)",
      value: accountQuery.data?.balance
        ? `$${accountQuery.data.balance.total_usdt_equity.toFixed(2)}`
        : "--.--",
      hint: "账户聚合数据将随私有账户接入替换",
    },
    {
      label: "可用余额",
      value: accountQuery.data?.balance
        ? `$${accountQuery.data.balance.available_usdt.toFixed(2)}`
        : "--.--",
      hint: "当前以行情覆盖率代理资产可动用区间",
    },
    {
      label: "净敞口",
      value: data ? `${data.paper_positions.length.toString().padStart(2, "0")} 组` : "-- 组",
      hint: "现阶段以纸面持仓与策略编组数量展示",
    },
    {
      label: "今日 PnL",
      value: data ? formatSignedBps(averageEdge) : "--.-- bps",
      hint: "使用候选机会净边际均值作为代理读数",
    },
  ];
  const opportunityRows =
    data?.top_opportunities.map((row) => ({
      symbol: row.symbol,
      funding: `${(row.funding_rate * 10000).toFixed(2)} bps`,
      edge: `${row.net_edge_bps.toFixed(2)} bps`,
      status: row.risk_tag,
    })) ?? [];
  const updatedLabel = data
    ? `最近更新 ${timeFormatter.format(new Date(data.generated_at))}`
    : "等待首批行情快照";

  return (
    <TerminalLayout activePath="/">
      {safetyQuery.data?.frozen && (
        <div style={{ background: "#ff4444", color: "white", padding: "8px 16px", textAlign: "center", fontWeight: "bold", marginBottom: "8px" }}>
          ⚠ 账户已冻结 — 所有交易已停止
        </div>
      )}
      <section className="dashboard-overview-grid">
        {metricCards.map((card, index) => (
          <article className="overview-card" key={card.label}>
            <div className={`overview-card__icon overview-card__icon--tone-${index + 1}`} aria-hidden="true">
              {String(index + 1).padStart(2, "0")}
            </div>
            <div>
              <p className="overview-card__label">{card.label}</p>
              <p className="overview-card__value">{card.value}</p>
              <p className="overview-card__hint">{card.hint}</p>
            </div>
          </article>
        ))}
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-grid__left">
          <article className="dashboard-card dashboard-card--scanner">
            <div className="dashboard-card__header">
              <div>
                <p className="dashboard-card__eyebrow">实时机会排序</p>
                <h2>机会扫描器 (实时)</h2>
              </div>
              <div className="dashboard-tag-group">
                <span className="dashboard-tag">套利</span>
                <span className="dashboard-tag">趋势</span>
                <span className="dashboard-status-chip">{updatedLabel}</span>
              </div>
            </div>

            {summaryQuery.isPending ? <p className="panel-state">正在刷新指挥台数据</p> : null}
            {summaryQuery.isError ? <p className="panel-alert">指挥台数据暂时不可用</p> : null}

            <div className="dashboard-table">
              <div className="dashboard-table__row dashboard-table__row--head">
                <span>交易对</span>
                <span>Funding</span>
                <span>净边际</span>
                <span>风险状态</span>
              </div>
              {!summaryQuery.isPending && !summaryQuery.isError && opportunityRows.length === 0 ? (
                <div className="table-empty">暂无可展示机会</div>
              ) : null}
              {opportunityRows.map((row) => (
                <div className="dashboard-table__row" key={row.symbol}>
                  <div className="pair-cell">
                    <strong className="pair-cell__title">{row.symbol}</strong>
                    <span className="pair-cell__meta">CEX Funding Carry</span>
                  </div>
                  <span>{row.funding}</span>
                  <span>{row.edge}</span>
                  <span className="dashboard-text--accent">{row.status}</span>
                </div>
              ))}
            </div>
          </article>

          <div className="dashboard-bottom-grid">
            <article className="dashboard-card">
              <div className="dashboard-card__header dashboard-card__header--compact">
                <div>
                  <p className="dashboard-card__eyebrow">Execution Book</p>
                  <h3>活跃对冲策略 (Active Hedges)</h3>
                </div>
              </div>

              <div className="strategy-list">
                {(data?.top_opportunities.slice(0, 3) ?? []).map((row, index) => (
                  <div className="strategy-list__item" key={row.symbol}>
                    <div>
                      <p className="strategy-list__title">HEDGE-{String(index + 1).padStart(2, "0")} / {row.symbol}</p>
                      <p className="strategy-list__meta">Funding Carry / 自动择时保护</p>
                    </div>
                    <div className="strategy-list__metrics">
                      <strong>{row.net_edge_bps.toFixed(2)} bps</strong>
                      <span>{row.risk_tag}</span>
                    </div>
                  </div>
                ))}

                {!summaryQuery.isPending && !summaryQuery.isError && (data?.top_opportunities.length ?? 0) === 0 ? (
                  <div className="strategy-list__empty">等待执行层接入后显示真实持仓腿。</div>
                ) : null}
              </div>
            </article>

            <article className="dashboard-card">
              <div className="dashboard-card__header dashboard-card__header--compact">
                <div>
                  <p className="dashboard-card__eyebrow">Allocation</p>
                  <h3>实时资产分布</h3>
                </div>
              </div>

              <div className="distribution-card">
                <div
                  className="distribution-card__ring"
                  style={{
                    background: `conic-gradient(${distributionGradient.join(", ")})`,
                  }}
                >
                  <div className="distribution-card__core">LIVE</div>
                </div>

                <div className="distribution-card__legend">
                  {distribution.map((segment) => (
                    <div className="distribution-card__legend-row" key={segment.label}>
                      <span className="distribution-card__legend-label">
                        <span
                          className="distribution-card__legend-dot"
                          style={{ backgroundColor: segment.color }}
                        />
                        {segment.label}
                      </span>
                      <strong>{segment.value}%</strong>
                    </div>
                  ))}
                </div>
              </div>
            </article>
          </div>
        </div>

        <div className="dashboard-grid__right">
          <article className="dashboard-card dashboard-card--risk">
            <div className="dashboard-card__header dashboard-card__header--compact">
              <div>
                <p className="dashboard-card__eyebrow">Risk Control</p>
                <h2>风险状态中心</h2>
              </div>
            </div>

            <div className="risk-panel">
              <div className="risk-panel__headline">
                <div>
                  <p className="risk-panel__label">当前风险等级</p>
                  <strong>{formatRiskLabel(data?.account_health.risk_state)}</strong>
                </div>
                <div className="risk-panel__radar" aria-hidden="true" />
              </div>

              <div className="risk-panel__stats">
                <div className="risk-stat">
                  <span>系统熔断状态</span>
                  <strong>{data?.market_status.degraded ? "观察中" : "已就绪 (READY)"}</strong>
                </div>
                <div className="risk-stat">
                  <span>运行模式</span>
                  <strong>
                    {data ? `${data.account_health.mode.toUpperCase()} / ${data.account_health.exchange}` : "同步中"}
                  </strong>
                </div>
                <div className="risk-stat">
                  <span>行情链路</span>
                  <strong>
                    {data
                      ? `${describeMarketSource(data.market_status.spot_source, "现货")} / ${describeMarketSource(
                          data.market_status.perp_source,
                          "永续"
                        )}`
                      : "同步中"}
                  </strong>
                </div>
              </div>

              <button
                className="risk-panel__force-button"
                type="button"
                onClick={() => {
                  if (window.confirm("确认紧急平仓所有持仓？此操作不可撤销！")) {
                    emergencyCloseMutation.mutate();
                  }
                }}
                disabled={emergencyCloseMutation.isPending}
              >
                {emergencyCloseMutation.isPending ? "平仓中..." : "紧急一键平仓 (FORCE CLOSE)"}
              </button>
            </div>
          </article>

          <article className="dashboard-card">
            <div className="dashboard-card__header dashboard-card__header--compact">
              <div>
                <p className="dashboard-card__eyebrow">Market Pulse</p>
                <h2>实时行情脉冲</h2>
              </div>
            </div>

            <div className="market-pulse">
              <div className="market-pulse__headline">
                <strong>{topOpportunity?.symbol ?? "等待行情"}</strong>
                <span>
                  {topOpportunity && topOpportunity.basis_bps !== undefined
                    ? `${topOpportunity.basis_bps.toFixed(2)} bps basis`
                    : "等待首批机会"}
                </span>
              </div>

              <div className="market-pulse__grid">
                <div className="risk-stat">
                  <span>现货买一 / 卖一</span>
                  <strong>{formatQuotePair(topOpportunity?.spot_bid, topOpportunity?.spot_ask)}</strong>
                </div>
                <div className="risk-stat">
                  <span>永续买一 / 卖一</span>
                  <strong>{formatQuotePair(topOpportunity?.perp_bid, topOpportunity?.perp_ask)}</strong>
                </div>
                <div className="risk-stat">
                  <span>现货中间价</span>
                  <strong>{formatFixed(topOpportunity?.spot_mid)}</strong>
                </div>
                <div className="risk-stat">
                  <span>永续中间价</span>
                  <strong>{formatFixed(topOpportunity?.perp_mid)}</strong>
                </div>
              </div>
            </div>
          </article>

          <article className="dashboard-card dashboard-card--log">
            <div className="dashboard-card__header dashboard-card__header--compact">
              <div>
                <p className="dashboard-card__eyebrow">Timeline</p>
                <h2>风险管理日志</h2>
              </div>
            </div>

            <div className="timeline-list">
              {riskLogs.map((log, index) => (
                <div className="timeline-list__item" key={`${log}-${index}`}>
                  <span className="timeline-list__dot" aria-hidden="true" />
                  <div>
                    <p>{log}</p>
                    <span>{index === 0 ? updatedLabel : `事件 ${String(index + 1).padStart(2, "0")}`}</span>
                  </div>
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>
    </TerminalLayout>
  );
}
