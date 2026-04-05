import { TerminalLayout } from "../../shared/ui/terminal-layout";

const overviewCards = [
  { label: "当前持仓数", value: "12", hint: "+2 从昨日" },
  { label: "总名义仓位", value: "$1,428,902.50", hint: "USDT 结算" },
  { label: "未实现收益 (uPnL)", value: "+$14,204.12", hint: "+3.14%" },
];

const hedgeRows = [
  {
    symbol: "BTC/USDT",
    venue: "永续合约 / Binance",
    divergence: "0.82%",
    divergenceWidth: "82%",
    leverage: "10.0x",
    funding: "0.0100%",
    takeProfit: "68,240.50",
    stopLoss: "62,100.00",
  },
  {
    symbol: "ETH/USDT",
    venue: "永续合约 / OKX",
    divergence: "1.45%",
    divergenceWidth: "45%",
    leverage: "5.0x",
    funding: "-0.0024%",
    takeProfit: "2,640.00",
    stopLoss: "2,320.50",
  },
  {
    symbol: "SOL/USDT",
    venue: "永续合约 / Binance",
    divergence: "0.12%",
    divergenceWidth: "12%",
    leverage: "20.0x",
    funding: "0.0000%",
    takeProfit: "158.20",
    stopLoss: "132.00",
  },
];

const exitConditions = [
  { title: "目标基差偏离", status: "触发中", detail: "当现货/永续基差收敛至 0.05%", tone: "accent" },
  { title: "预估资金流向", status: "等待", detail: "累计资金费率收益达到 1.2%", tone: "muted" },
  { title: "强制平仓警报", status: "关键", detail: "账户净值跌破预警线 $1,250,000", tone: "danger" },
];

export function PositionMonitorPage() {
  const footerContent = (
    <>
      <span>核心引擎: 运行中</span>
      <span>API 延迟: 12ms</span>
      <span>序列号: OBJ-2940-X1</span>
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
          {overviewCards.map((card) => (
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
                <span className="proto-chip">高偏离</span>
              </div>
            </div>

            <div className="proto-table-shell">
              <div className="proto-table-row proto-table-row--positions proto-table-row--head">
                <span>交易对</span>
                <span>对冲偏离</span>
                <span>杠杆</span>
                <span>资金费率状态</span>
                <span>止盈 / 止损</span>
                <span>操作</span>
              </div>
              {hedgeRows.map((row) => (
                <div className="proto-table-row proto-table-row--positions" key={row.symbol}>
                  <div>
                    <strong>{row.symbol}</strong>
                    <span className="proto-meta">{row.venue}</span>
                  </div>
                  <div>
                    <div className="proto-progress">
                      <div className="proto-progress__fill" style={{ width: row.divergenceWidth }} />
                    </div>
                    <span className="proto-meta">{row.divergence}</span>
                  </div>
                  <span className="proto-pill">{row.leverage}</span>
                  <span>{row.funding}</span>
                  <div>
                    <strong className="proto-text--accent">{row.takeProfit}</strong>
                    <span className="proto-meta proto-text--danger">{row.stopLoss}</span>
                  </div>
                  <span className="proto-meta">•••</span>
                </div>
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
                <button className="proto-button proto-button--ghost" type="button">
                  仅减仓
                </button>
                <button className="proto-button proto-button--ghost" type="button">
                  暂停
                </button>
                <button className="proto-button proto-button--danger" type="button">
                  立即强平 (Panic Sell)
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
                {[52, 76, 66, 100, 30, 84, 68, 52, 74, 48].map((height, index) => (
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
