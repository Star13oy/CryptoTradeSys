const scanRows = [
  { symbol: "BTCUSDT", score: "7.0", edge: "0.70 bps", risk: "normal" },
  { symbol: "ETHUSDT", score: "5.8", edge: "0.58 bps", risk: "normal" },
  { symbol: "SOLUSDT", score: "2.4", edge: "0.24 bps", risk: "thin-edge" },
];

const filters = ["全市场扫描", "白名单准入", "Funding > 0", "盘口价差 < 1 bps"];

export function OpportunityScanPage() {
  return (
    <main className="console-shell">
      <section className="hero-panel">
        <div className="hero-copy">
          <p className="eyebrow">Funding / Spread / Risk / Ranking</p>
          <h1>机会扫描页</h1>
          <p className="hero-text">
            从全市场抓取候选币对，按 funding 净边际、流动性和风控约束做分层筛选。
          </p>
        </div>
        <div className="hero-actions">
          <a className="nav-pill" href="/">
            指挥台
          </a>
          <a className="nav-pill nav-pill-active" href="/scan">
            机会扫描
          </a>
        </div>
      </section>

      <section className="filter-row">
        {filters.map((filter) => (
          <span className="filter-chip" key={filter}>
            {filter}
          </span>
        ))}
      </section>

      <section className="content-grid">
        <article className="section-card section-card-wide">
          <div className="section-header">
            <div>
              <p className="section-kicker">Candidate Table</p>
              <h2>候选机会表</h2>
            </div>
            <span className="status-chip">实时评分</span>
          </div>
          <div className="table-shell">
            <div className="table-row table-row-head">
              <span>交易对</span>
              <span>Score</span>
              <span>净边际</span>
              <span>风险标签</span>
            </div>
            {scanRows.map((row) => (
              <div className="table-row" key={row.symbol}>
                <strong>{row.symbol}</strong>
                <span>{row.score}</span>
                <span>{row.edge}</span>
                <span className="status-text">{row.risk}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="section-card">
          <div className="section-header">
            <div>
              <p className="section-kicker">Selection Notes</p>
              <h2>筛选说明</h2>
            </div>
          </div>
          <ul className="signal-list">
            <li>
              <span>当前排序主轴</span>
              <strong>资金费率套利</strong>
            </li>
            <li>
              <span>准入模式</span>
              <strong>全市场扫描 + 白名单</strong>
            </li>
            <li>
              <span>执行方式</span>
              <strong>24/7 全自动</strong>
            </li>
            <li>
              <span>详情抽屉</span>
              <strong>下一阶段接入</strong>
            </li>
          </ul>
        </article>
      </section>
    </main>
  );
}
