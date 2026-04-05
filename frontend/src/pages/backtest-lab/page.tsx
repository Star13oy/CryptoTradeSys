import { TerminalLayout } from "../../shared/ui/terminal-layout";

const resultCards = [
  { label: "总收益率 (Total Return)", value: "+142.85%", tone: "accent" },
  { label: "最大回撤 (Max Drawdown)", value: "-12.41%", tone: "danger" },
  { label: "夏普比率 (Sharpe Ratio)", value: "2.84", tone: "warning" },
];

const historyRows = [
  ["#BK-9421", "MA-CROSS-v2 (Aggressive)", "2023-Q1", "+42.1%", "2.14", "-8.2%", "SUCCESS"],
  ["#BK-9418", "STAT-ARB (High Freq)", "2023-Q1", "+12.5%", "4.82", "-2.1%", "SUCCESS"],
  ["#BK-9415", "VOL-BREAK (Daily)", "2023-Q1", "-5.4%", "0.82", "-14.5%", "FAILED"],
];

export function BacktestLabPage() {
  const footerContent = (
    <>
      <span>引擎状态: 运行中</span>
      <span>GPU 加速: 已开启</span>
      <span>回测队列: 0 任务</span>
    </>
  );

  return (
    <TerminalLayout activePath="/backtest" footerContent={footerContent}>
      <section className="proto-page">
        <header className="proto-header">
          <div>
            <h2 className="proto-page__title">回测实验室</h2>
            <p className="proto-page__subtitle">BTC/USDT 永续合约回测引擎 v4.2.0</p>
          </div>
          <div className="proto-header__actions">
            <button className="proto-button proto-button--ghost" type="button">
              导出报告
            </button>
            <button className="proto-button proto-button--primary" type="button">
              执行回测
            </button>
          </div>
        </header>

        <section className="proto-main-grid">
          <div className="proto-side-stack">
            <article className="proto-panel">
              <p className="proto-panel__eyebrow">Config</p>
              <h3>策略配置</h3>
              <div className="proto-form-stack">
                <label className="proto-field">
                  <span>策略选择</span>
                  <select defaultValue="多重均线趋势追踪 (MA-CROSS-v2)">
                    <option>多重均线趋势追踪 (MA-CROSS-v2)</option>
                    <option>均值回归统计套利 (STAT-ARB)</option>
                    <option>波动率突破策略 (VOL-BREAK)</option>
                  </select>
                </label>
                <label className="proto-field">
                  <span>时间范围</span>
                  <input type="text" value="2023-01-01 至 2023-12-31" readOnly />
                </label>
              </div>
            </article>

            <article className="proto-panel">
              <p className="proto-panel__eyebrow">Parameter Matrix</p>
              <h3>参数矩阵</h3>
              <div className="proto-form-stack">
                <div className="proto-threshold">
                  <div className="proto-threshold__top">
                    <span>收益阈值 (Alpha)</span>
                    <strong>2.4%</strong>
                  </div>
                  <div className="proto-progress">
                    <div className="proto-progress__fill proto-progress__fill--warning" style={{ width: "54%" }} />
                  </div>
                </div>
                <div className="proto-chip-row">
                  {[2, 5, 10, 15, 20].map((value) => (
                    <span className={`proto-chip${value === 5 ? " proto-chip--active" : ""}`} key={value}>
                      {value}
                    </span>
                  ))}
                </div>
                <label className="proto-field">
                  <span>风控阈值 (Drawdown Limit)</span>
                  <input type="text" value="15.00%" readOnly />
                </label>
              </div>
            </article>
          </div>

          <div className="proto-wide-stack">
            <section className="proto-stat-grid">
              {resultCards.map((card) => (
                <article className="proto-stat-card" key={card.label}>
                  <p>{card.label}</p>
                  <strong className={`proto-text--${card.tone}`}>{card.value}</strong>
                </article>
              ))}
            </section>

            <article className="proto-panel">
              <div className="proto-panel__header">
                <div>
                  <p className="proto-panel__eyebrow">Performance Curve</p>
                  <h3>净值曲线 (Equity Curve)</h3>
                </div>
                <div className="proto-chip-row">
                  <span className="proto-chip proto-chip--active">Log Scale</span>
                  <span className="proto-chip">Benchmarks</span>
                </div>
              </div>
              <svg className="proto-chart" preserveAspectRatio="none" viewBox="0 0 800 240">
                <defs>
                  <linearGradient id="backtest-curve" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#6bd8cb" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="#6bd8cb" stopOpacity="0" />
                  </linearGradient>
                </defs>
                <path d="M 0,220 Q 80,210 160,180 T 320,150 T 480,100 T 640,60 T 800,40 L 800,240 L 0,240 Z" fill="url(#backtest-curve)" />
                <path
                  d="M 0,220 Q 80,210 160,180 T 320,150 T 480,100 T 640,60 T 800,40"
                  fill="none"
                  stroke="#6bd8cb"
                  strokeLinecap="round"
                  strokeWidth="3"
                />
              </svg>
            </article>

            <div className="proto-dual-grid">
              <article className="proto-panel">
                <p className="proto-panel__eyebrow">Drawdown</p>
                <h3>回测回撤 (Drawdown Depth)</h3>
                <div className="proto-drawdown">
                  {[20, 35, 10, 5, 60, 45, 30, 15, 8].map((height, index) => (
                    <div className="proto-drawdown__bar" key={`${height}-${index}`} style={{ height: `${height}%` }} />
                  ))}
                </div>
              </article>
              <article className="proto-panel">
                <p className="proto-panel__eyebrow">Sensitivity</p>
                <h3>参数敏感度热力图</h3>
                <div className="proto-heatmap">
                  {Array.from({ length: 36 }, (_, index) => (
                    <span className={`proto-heatmap__cell proto-heatmap__cell--${(index % 6) + 1}`} key={index} />
                  ))}
                </div>
              </article>
            </div>
          </div>

          <div className="proto-side-stack">
            <article className="proto-panel">
              <p className="proto-panel__eyebrow">Summary</p>
              <h3>交易统计摘要</h3>
              <div className="proto-kv-list">
                <div><span>总交易笔数</span><strong>428</strong></div>
                <div><span>胜率 (Win Rate)</span><strong>64.2%</strong></div>
                <div><span>盈亏比 (P/L Ratio)</span><strong>1.82</strong></div>
                <div><span>平均每笔盈亏</span><strong className="proto-text--accent">0.34%</strong></div>
                <div><span>恢复因子</span><strong>11.51</strong></div>
              </div>
            </article>
          </div>
        </section>

        <article className="proto-panel">
          <div className="proto-panel__header">
            <div>
              <p className="proto-panel__eyebrow">History</p>
              <h3>历史回测记录</h3>
            </div>
          </div>

          <div className="proto-table-shell">
            <div className="proto-table-row proto-table-row--history proto-table-row--head">
              <span>任务ID</span>
              <span>策略模型</span>
              <span>时间段</span>
              <span>总收益</span>
              <span>夏普</span>
              <span>回撤</span>
              <span>状态</span>
            </div>
            {historyRows.map((row) => (
              <div className="proto-table-row proto-table-row--history" key={row[0]}>
                <span>{row[0]}</span>
                <strong>{row[1]}</strong>
                <span>{row[2]}</span>
                <span className={row[3].startsWith("+") ? "proto-text--accent" : "proto-text--danger"}>{row[3]}</span>
                <span>{row[4]}</span>
                <span className="proto-text--danger">{row[5]}</span>
                <span className="proto-pill">{row[6]}</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </TerminalLayout>
  );
}
