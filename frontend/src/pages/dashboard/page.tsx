import { useEffect, useState } from "react";

import { apiGet } from "../../shared/api/client";

const topOpportunities = [
  { symbol: "BTCUSDT", funding: "+2.00 bps", spread: "0.17 bps", status: "可执行" },
  { symbol: "ETHUSDT", funding: "+1.65 bps", spread: "0.24 bps", status: "观察中" },
  { symbol: "SOLUSDT", funding: "+1.31 bps", spread: "0.42 bps", status: "等待窗口" },
];

type DashboardSummary = {
  account_health: {
    mode: string;
    exchange: string;
    risk_state: string;
  };
  top_opportunities: Array<{
    symbol: string;
    funding_rate: number;
    net_edge_bps: number;
    score: number;
    risk_tag: string;
  }>;
};

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    void apiGet<DashboardSummary>("/api/v1/dashboard/summary")
      .then(setData)
      .catch(() => setData(null));
  }, []);

  const healthCards = [
    {
      label: "风险状态",
      value: data?.account_health.risk_state ?? "Normal",
      hint: "保证金缓冲充足",
    },
    {
      label: "运行模式",
      value: `${data?.account_health.mode ?? "paper"} / ${data?.account_health.exchange ?? "binance"}`,
      hint: "仿真盘与交易所来源",
    },
    {
      label: "下一次 Funding",
      value: "07:58",
      hint: "自动再平衡待命",
    },
  ];

  const opportunityRows =
    data?.top_opportunities.map((row) => ({
      symbol: row.symbol,
      funding: `${(row.funding_rate * 10000).toFixed(2)} bps`,
      spread: `${row.net_edge_bps.toFixed(2)} bps`,
      status: row.risk_tag,
    })) ?? topOpportunities;

  return (
    <main className="console-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Paper Trading / Binance / Funding Arb</p>
          <h1>总览指挥台</h1>
          <p className="hero-text">
            盯住高质量 funding 机会、账户健康度和自动执行节奏，让套利系统的状态一眼可读。
          </p>
        </div>
        <div className="hero-actions">
          <a className="nav-pill nav-pill-active" href="/">
            指挥台
          </a>
          <a className="nav-pill" href="/scan">
            机会扫描
          </a>
        </div>
      </section>

      <section className="metric-grid">
        {healthCards.map((card) => (
          <article className="metric-card" key={card.label}>
            <p className="metric-label">{card.label}</p>
            <strong className="metric-value">{card.value}</strong>
            <p className="metric-hint">{card.hint}</p>
          </article>
        ))}
      </section>

      <section className="content-grid">
        <article className="section-card section-card-wide">
          <div className="section-header">
            <div>
              <p className="section-kicker">Top Opportunities</p>
              <h2>机会总览</h2>
            </div>
            <span className="status-chip">实时仿真</span>
          </div>
          <div className="table-shell">
            <div className="table-row table-row-head">
              <span>交易对</span>
              <span>Funding</span>
              <span>净边际</span>
              <span>状态</span>
            </div>
            {opportunityRows.map((row) => (
              <div className="table-row" key={row.symbol}>
                <strong>{row.symbol}</strong>
                <span>{row.funding}</span>
                <span>{row.spread}</span>
                <span className="status-text">{row.status}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="section-card">
          <div className="section-header">
            <div>
              <p className="section-kicker">Account Health</p>
              <h2>账户健康</h2>
            </div>
          </div>
          <ul className="signal-list">
            <li>
              <span>保证金率</span>
              <strong>74%</strong>
            </li>
            <li>
              <span>自动对冲</span>
              <strong>已开启</strong>
            </li>
            <li>
              <span>风控策略</span>
              <strong>均衡模式</strong>
            </li>
            <li>
              <span>系统告警</span>
              <strong>0 条待处理</strong>
            </li>
          </ul>
        </article>
      </section>
    </main>
  );
}
