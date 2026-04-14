import { useQuery, useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { apiGet } from "../../shared/api/client";
import type { ScanOpportunitiesResponse, OrderResult } from "../../shared/contracts/console";
import { TerminalLayout } from "../../shared/ui/terminal-layout";

const timeFormatter = new Intl.DateTimeFormat("zh-CN", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

const apyThresholdOptions = [
  { value: "apy-10", label: "> 10% 年化收益", minNetEdgeBps: undefined },
  { value: "apy-5", label: "> 5% 年化收益", minNetEdgeBps: 1 },
  { value: "apy-20", label: "> 20% 年化收益", minNetEdgeBps: 2 },
] as const;

type AnnualizedThreshold = (typeof apyThresholdOptions)[number]["value"];
type RiskFilter = "all" | "low" | "mid" | "high";

function describeMarketSource(source: string, marketLabel: string) {
  return `${marketLabel}${source === "depth" ? "深度回退" : "主盘口"}`;
}

function formatSymbol(symbol: string) {
  if (!symbol.endsWith("USDT")) {
    return symbol;
  }

  return `${symbol.slice(0, -4)}/USDT`;
}

function annualizedYield(fundingRate: number) {
  return fundingRate * 3 * 365 * 100;
}

function formatQuote(bid: number | undefined, ask: number | undefined) {
  if (bid === undefined || ask === undefined) {
    return "-- / --";
  }
  return `${bid.toFixed(4)} / ${ask.toFixed(4)}`;
}

function formatMid(value: number | undefined) {
  if (value === undefined) {
    return "--";
  }
  return value.toFixed(4);
}

function formatBps(value: number | undefined) {
  if (value === undefined) {
    return "--";
  }
  return `${value.toFixed(2)} bps`;
}

function formatCombinedBps(left: number | undefined, right: number | undefined) {
  if (left === undefined || right === undefined) {
    return "--";
  }
  return `${(left + right).toFixed(2)} bps`;
}

function normalizeRiskLevel(riskTag: string): Exclude<RiskFilter, "all"> {
  if (riskTag.includes("critical") || riskTag.includes("high") || riskTag.includes("halt")) {
    return "high";
  }

  if (riskTag.includes("guard") || riskTag.includes("warn") || riskTag.includes("elevated")) {
    return "mid";
  }

  return "low";
}

export function OpportunityScanPage() {
  const [limit, setLimit] = useState(25);
  const [searchTerm, setSearchTerm] = useState("");
  const [annualizedThreshold, setAnnualizedThreshold] = useState<AnnualizedThreshold>("apy-10");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("all");
  const [selectedSymbol, setSelectedSymbol] = useState("BTCUSDT");

  const selectedThreshold = apyThresholdOptions.find((option) => option.value === annualizedThreshold);
  const minNetEdgeBps = selectedThreshold?.minNetEdgeBps;

  const quickOpenMutation = useMutation({
    mutationFn: (symbol: string) =>
      apiGet<OrderResult>("/api/v1/trading/execute", {
        symbol,
        side: "long",
        notional: 1000,
        mode: "paper",
      }),
    onSuccess: () => {
      // Could show a success message or refresh positions
    },
  });

  const scanQuery = useQuery({
    queryKey: ["scan-opportunities", limit, minNetEdgeBps ?? null],
    queryFn: () =>
      apiGet<ScanOpportunitiesResponse>("/api/v1/scan/opportunities", {
        limit,
        positive_funding_only: true,
        min_net_edge_bps: minNetEdgeBps,
      }),
  });

  const data = scanQuery.data;
  const filteredRows = (data?.rows ?? []).filter((row) => {
    const compactSearch = searchTerm.trim().replace("/", "").toLowerCase();
    const matchesSearch =
      compactSearch.length === 0 ||
      formatSymbol(row.symbol).toLowerCase().includes(searchTerm.trim().toLowerCase()) ||
      row.symbol.toLowerCase().includes(compactSearch);
    const matchesRisk = riskFilter === "all" || normalizeRiskLevel(row.risk_tag) === riskFilter;
    return matchesSearch && matchesRisk;
  });

  useEffect(() => {
    if (filteredRows.length === 0) {
      setSelectedSymbol("BTCUSDT");
      return;
    }

    if (!filteredRows.some((row) => row.symbol === selectedSymbol)) {
      setSelectedSymbol(filteredRows[0].symbol);
    }
  }, [filteredRows, selectedSymbol]);

  const statusLabel = data
    ? `最近扫描 ${timeFormatter.format(new Date(data.generated_at))}`
    : "等待首批扫描结果";
  const coverageLabel = data
    ? `命中 ${data.total_matches} 条，当前展示 ${filteredRows.length} 条`
    : "等待过滤器与市场快照同步";
  const marketSourceLabel = data
    ? `${describeMarketSource(data.market_status.spot_source, "现货")} / ${describeMarketSource(data.market_status.perp_source, "永续")}`
    : "等待行情链路确认";
  const detailRow = filteredRows.find((row) => row.symbol === selectedSymbol) ?? null;
  const detailSymbol = formatSymbol(detailRow?.symbol ?? "BTCUSDT");
  const detailAnnualized = detailRow ? annualizedYield(detailRow.funding_rate) : 12.42;
  const detailDailyCarry = detailRow ? ((detailRow.funding_rate * 3 * 10_000) / 100).toFixed(2) : "12.20";
  const marketMetrics = [
    {
      label: "现货买一 / 卖一",
      value: formatQuote(detailRow?.spot_bid, detailRow?.spot_ask),
      hint: `Mid ${formatMid(detailRow?.spot_mid)}`,
    },
    {
      label: "永续买一 / 卖一",
      value: formatQuote(detailRow?.perp_bid, detailRow?.perp_ask),
      hint: `Mid ${formatMid(detailRow?.perp_mid)}`,
    },
    {
      label: "基差 (Basis)",
      value: formatBps(detailRow?.basis_bps),
      hint: "现货/永续偏移",
    },
    {
      label: "双腿点差成本",
      value: formatCombinedBps(detailRow?.spot_spread_bps, detailRow?.perp_spread_bps),
      hint: "Spot + Perp",
    },
  ];
  const riskMetrics = [
    {
      label: "流动性系数",
      value: detailRow ? Math.min(0.99, detailRow.score / 25).toFixed(2) : "0.98",
      hint: "优",
    },
    {
      label: "费率置信度",
      value: detailRow ? Math.min(0.99, Math.abs(detailRow.funding_rate) * 1_200).toFixed(2) : "0.91",
      hint: "稳",
    },
    {
      label: "报价覆盖率",
      value: data
        ? (data.market_status.quoted_symbols / Math.max(data.market_status.requested_symbols, 1)).toFixed(2)
        : "0.84",
      hint: "实时",
    },
    {
      label: "熔断距离",
      value: detailRow?.risk_tag === "normal" ? "0.76" : "0.42",
      hint: detailRow?.risk_tag === "normal" ? "安全" : "关注",
    },
  ];
  const footerContent = (
    <>
      <span>LIVE MARKET FEED / {marketSourceLabel}</span>
      <span>{coverageLabel}</span>
      <span>{statusLabel}</span>
    </>
  );

  return (
    <TerminalLayout activePath="/scan" footerContent={footerContent}>
      <section className="scanner-page">
        <header className="scanner-header">
          <div>
            <h2>机会扫描器 (Scanner)</h2>
            <p>实时跨市场套利与基差机会自动检测引擎</p>
          </div>

          <div className="scanner-header__actions">
            <button className="scanner-button scanner-button--ghost" type="button">
              导出报表
            </button>
            <button className="scanner-button scanner-button--primary" type="button" onClick={() => void scanQuery.refetch()}>
              即时扫描
            </button>
          </div>
        </header>

        <section className="scanner-filter-grid">
          <div className="scanner-field">
            <label htmlFor="symbol-search">交易对搜索</label>
            <input
              id="symbol-search"
              name="symbol-search"
              placeholder="例如: BTC/USDT"
              type="text"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
            />
          </div>

          <div className="scanner-field">
            <label htmlFor="apy-threshold">收益阈值 (Annualized)</label>
            <select
              id="apy-threshold"
              name="apy-threshold"
              aria-label="收益阈值 (Annualized)"
              value={annualizedThreshold}
              onChange={(event) => setAnnualizedThreshold(event.target.value as AnnualizedThreshold)}
            >
              {apyThresholdOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div className="scanner-field">
            <span className="scanner-field__label">风险等级</span>
            <div className="scanner-segmented-control">
              {[
                { value: "all", label: "全部" },
                { value: "low", label: "低" },
                { value: "mid", label: "中" },
                { value: "high", label: "高" },
              ].map((option) => (
                <button
                  className={`scanner-segmented-control__item${
                    riskFilter === option.value ? " scanner-segmented-control__item--active" : ""
                  }`}
                  key={option.value}
                  type="button"
                  onClick={() => setRiskFilter(option.value as RiskFilter)}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div className="scanner-field">
            <span className="scanner-field__label">活跃市场</span>
            <div className="scanner-market-list">
              <span className="scanner-market-chip scanner-market-chip--active">
                Binance <span className="scanner-market-chip__dot" aria-hidden="true" />
              </span>
              <button className="scanner-market-chip" type="button" onClick={() => setLimit(10)}>
                Top 10
              </button>
              <button className="scanner-market-chip" type="button" onClick={() => setLimit(25)}>
                Top 25
              </button>
            </div>
          </div>
        </section>

        <section className="scanner-workspace">
          <article className="scanner-table-card">
            {scanQuery.isPending ? <p className="panel-state">正在刷新扫描结果</p> : null}
            {scanQuery.isError ? <p className="panel-alert">扫描服务暂时不可用</p> : null}
            {!scanQuery.isError ? <p className="panel-state panel-state-subtle">{coverageLabel}</p> : null}

            <div className="scanner-table-shell">
              <div className="scanner-table scanner-table--head">
                <span>交易对</span>
                <span>资金费率</span>
                <span>年化收益</span>
                <span>净边际</span>
                <span>风险评分</span>
                <span>状态</span>
                <span>操作</span>
              </div>

              {!scanQuery.isPending && !scanQuery.isError && filteredRows.length === 0 ? (
                <div className="table-empty">暂无候选机会</div>
              ) : null}

              {filteredRows.map((row) => (
                <button
                  className={`scanner-table${selectedSymbol === row.symbol ? " scanner-table--active" : ""}`}
                  key={row.symbol}
                  type="button"
                  onClick={() => setSelectedSymbol(row.symbol)}
                >
                  <div className="pair-cell">
                    <div className="pair-dot-group" aria-hidden="true">
                      <span className="pair-dot pair-dot--primary" />
                      <span className="pair-dot pair-dot--secondary" />
                    </div>
                    <div>
                      <strong className="pair-cell__title">{formatSymbol(row.symbol)}</strong>
                      <span className="pair-cell__meta">Binance / Spot+Perp</span>
                    </div>
                  </div>
                  <span>{(row.funding_rate * 100).toFixed(4)}%</span>
                  <span>{annualizedYield(row.funding_rate).toFixed(2)}%</span>
                  <span>{row.net_edge_bps.toFixed(2)} bps</span>
                  <span>{row.score.toFixed(1)}</span>
                  <span className="scanner-table__status">
                    {row.net_edge_bps >= 2 ? "优先开仓" : row.net_edge_bps >= 1 ? "观察" : "继续跟踪"}
                  </span>
                  <span>
                    {row.risk_tag !== "blocked" ? (
                      <button
                        className="proto-button proto-button--primary"
                        type="button"
                        style={{ fontSize: 12, padding: "4px 12px" }}
                        disabled={quickOpenMutation.isPending}
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm(`确认开仓 ${formatSymbol(row.symbol)}？名义金额 $1000`)) {
                            quickOpenMutation.mutate(row.symbol);
                          }
                        }}
                      >
                        {quickOpenMutation.isPending ? "开仓中..." : "开仓"}
                      </button>
                    ) : null}
                  </span>
                </button>
              ))}
            </div>
          </article>

          <aside className="scanner-detail">
            <div className="scanner-detail__header">
              <div>
                <div className="scanner-detail__eyebrow">机会详情</div>
                <h3>{detailSymbol} 套利分析</h3>
              </div>
              <span className="scanner-detail__close" aria-hidden="true">
                ×
              </span>
            </div>

            <div className="scanner-detail__summary">
              <div>
                <span>预计年化收益率 (APY)</span>
                <strong>{detailAnnualized.toFixed(2)}%</strong>
                <div className="scanner-detail__bar">
                  <div
                    className="scanner-detail__bar-fill"
                    style={{ width: `${Math.max(12, Math.min(detailAnnualized * 3, 100))}%` }}
                  />
                </div>
              </div>
              <div>
                <span>净边际</span>
                <strong>{detailRow ? `${detailRow.net_edge_bps.toFixed(2)} bps` : "1.84 bps"}</strong>
              </div>
            </div>

            <div className="scanner-detail__narrative">
              <div>
                <div className="scanner-detail__title">资金费率收益 (Funding Fees)</div>
                <p>基于平均 funding 费率与 8 小时结算节奏，系统持续跟踪 carry 收益质量。</p>
                <strong>+{detailDailyCarry} USDT / Day</strong>
              </div>

              <div>
                <div className="scanner-detail__title">开仓建议</div>
                <p>
                  {detailRow
                    ? `${formatSymbol(detailRow.symbol)} 当前风险标签为 ${detailRow.risk_tag}，建议仅在滑点窗口稳定后执行。`
                    : "当前没有命中高质量机会，维持观察模式并等待下一轮扫描。"}
                </p>
              </div>
            </div>

            <div className="scanner-risk-grid">
              <h4>行情快照</h4>
              <div className="scanner-risk-grid__items">
                {marketMetrics.map((metric) => (
                  <div className="scanner-risk-card" key={metric.label}>
                    <span>{metric.label}</span>
                    <strong>
                      {metric.value} <em>{metric.hint}</em>
                    </strong>
                  </div>
                ))}
              </div>
            </div>

            <div className="scanner-risk-grid">
              <h4>风险评估参数</h4>
              <div className="scanner-risk-grid__items">
                {riskMetrics.map((metric) => (
                  <div className="scanner-risk-card" key={metric.label}>
                    <span>{metric.label}</span>
                    <strong>
                      {metric.value} <em>{metric.hint}</em>
                    </strong>
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </section>
      </section>
    </TerminalLayout>
  );
}
