import { TerminalLayout } from "../../shared/ui/terminal-layout";

const modelLibrary = [
  { name: "Alpha_Momentum_V3", status: "训练中", version: "3.4.2-stable", sharpe: "2.84", active: true },
  { name: "Trend_Follower_X", status: "已部署", version: "1.0.0-gold", sharpe: "1.95" },
  { name: "BTC_Mean_Reversion", status: "空闲", version: "0.9.1-beta", sharpe: "3.12" },
];

const checklist = [
  ["数据完整性校验", "毫秒级延时测试通过", true],
  ["回测净值覆盖", "2021-2023 历史数据", true],
  ["风险敞口限制", "需手动确认最大回撤 5%", false],
  ["风控逻辑同步", "SL/TP 自动挂单脚本", false],
] as const;

const diffRows = [
  ["夏普比", "2.45", "2.84"],
  ["年化收益", "18.2%", "24.6%"],
  ["最大回撤", "-8.1%", "-6.4%"],
];

export function ModelWorkbenchPage() {
  return (
    <TerminalLayout activePath="/models">
      <section className="proto-page">
        <header className="proto-header">
          <div>
            <h2 className="proto-page__title">模型工作台</h2>
            <p className="proto-page__subtitle">集成化的量化策略研发与部署环境</p>
          </div>
          <div className="proto-header__actions">
            <button className="proto-button proto-button--ghost" type="button">
              导出分析报告
            </button>
            <button className="proto-button proto-button--primary" type="button">
              一键部署实盘
            </button>
          </div>
        </header>

        <section className="proto-main-grid">
          <div className="proto-side-stack">
            <article className="proto-panel">
              <div className="proto-panel__header">
                <div>
                  <p className="proto-panel__eyebrow">Library</p>
                  <h3>模型库 (Library)</h3>
                </div>
              </div>
              <div className="proto-library-list">
                {modelLibrary.map((model) => (
                  <div className={`proto-library-item${model.active ? " proto-library-item--active" : ""}`} key={model.name}>
                    <div className="proto-library-item__top">
                      <strong>{model.name}</strong>
                      <span className={`proto-chip${model.active ? " proto-chip--active" : ""}`}>{model.status}</span>
                    </div>
                    <span className="proto-meta">版本: {model.version}</span>
                    <span className="proto-meta">夏普比: {model.sharpe}</span>
                  </div>
                ))}
              </div>
            </article>

            <article className="proto-panel">
              <p className="proto-panel__eyebrow">Scoring</p>
              <h3>实时打分预览 (Scoring)</h3>
              <div className="proto-kv-list">
                <div><span>BTC/USDT 现价</span><strong>68,432.10</strong></div>
              </div>
              <div className="proto-heatbars proto-heatbars--short">
                {[75, 50, 85, 60, 40, 95].map((height, index) => (
                  <div className="proto-heatbars__bar" key={`${height}-${index}`} style={{ height: `${height}%` }} />
                ))}
              </div>
              <div className="proto-score-card">
                <span>多头置信度</span>
                <strong>87.4%</strong>
              </div>
            </article>
          </div>

          <div className="proto-wide-stack">
            <article className="proto-panel">
              <div className="proto-panel__header">
                <div>
                  <p className="proto-panel__eyebrow">Model Config</p>
                  <h3>Alpha_Momentum_V3 参数配置</h3>
                </div>
                <div className="proto-chip-row">
                  <span className="proto-chip proto-chip--active">配置</span>
                  <span className="proto-chip">日志</span>
                </div>
              </div>
              <div className="proto-dual-grid">
                <div className="proto-stack-card">
                  <p className="proto-panel__eyebrow">输入特征 (Input Features)</p>
                  <div className="proto-token-list">
                    <div><span>Order_Flow_Imbalance</span><strong>启用</strong></div>
                    <div><span>Volatility_Zscore_1h</span><strong>启用</strong></div>
                    <div><span>Sentiment_Index_Twitter</span><strong>停用</strong></div>
                  </div>
                </div>
                <div className="proto-stack-card">
                  <p className="proto-panel__eyebrow">超参数 (Hyperparameters)</p>
                  <div className="proto-threshold">
                    <div className="proto-threshold__top">
                      <span>学习率 (Learning Rate)</span>
                      <strong>0.00045</strong>
                    </div>
                    <div className="proto-progress">
                      <div className="proto-progress__fill" style={{ width: "33%" }} />
                    </div>
                  </div>
                  <div className="proto-threshold">
                    <div className="proto-threshold__top">
                      <span>深度 (Depth)</span>
                      <strong>12</strong>
                    </div>
                    <div className="proto-progress">
                      <div className="proto-progress__fill" style={{ width: "66%" }} />
                    </div>
                  </div>
                </div>
              </div>
            </article>

            <article className="proto-panel">
              <div className="proto-panel__header">
                <div>
                  <p className="proto-panel__eyebrow">Interpretability</p>
                  <h3>可解释性分析 (SHAP Analysis)</h3>
                </div>
                <span className="proto-meta">基于最近 1000 个采样点</span>
              </div>
              <div className="proto-shap-list">
                {[
                  ["RSI_Divergence", "+0.42", "42%"],
                  ["Volume_Spike", "+0.28", "28%"],
                  ["MACD_Cross", "-0.15", "15%"],
                ].map(([name, value, width]) => (
                  <div className="proto-shap-item" key={name}>
                    <div className="proto-threshold__top">
                      <span>{name}</span>
                      <strong className={value.startsWith("-") ? "proto-text--danger" : "proto-text--accent"}>{value}</strong>
                    </div>
                    <div className="proto-progress">
                      <div
                        className={`proto-progress__fill${value.startsWith("-") ? " proto-progress__fill--danger" : ""}`}
                        style={{ width }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              <p className="proto-analysis-copy">
                <strong>分析结论：</strong> 当前多头预测主要受 RSI 背离支撑，但 MACD 零轴下方交叉提供了反向阻力。模型建议在波动率降至 0.82 以下时执行入场。
              </p>
            </article>
          </div>

          <div className="proto-side-stack">
            <article className="proto-panel">
              <p className="proto-panel__eyebrow">Checklist</p>
              <h3>部署清单 (Checklist)</h3>
              <div className="proto-checklist">
                {checklist.map(([title, detail, done]) => (
                  <div className="proto-checklist__item" key={title}>
                    <span className={`proto-checkmark${done ? " proto-checkmark--done" : ""}`} />
                    <div>
                      <strong>{title}</strong>
                      <span className="proto-meta">{detail}</span>
                    </div>
                  </div>
                ))}
              </div>
            </article>

            <article className="proto-panel">
              <p className="proto-panel__eyebrow">Version Diff</p>
              <h3>版本差异 (Diff)</h3>
              <div className="proto-table-shell">
                <div className="proto-table-row proto-table-row--diff proto-table-row--head">
                  <span>指标</span>
                  <span>V3.4.1</span>
                  <span>V3.4.2</span>
                </div>
                {diffRows.map((row) => (
                  <div className="proto-table-row proto-table-row--diff" key={row[0]}>
                    <span>{row[0]}</span>
                    <span>{row[1]}</span>
                    <strong className="proto-text--accent">{row[2]}</strong>
                  </div>
                ))}
              </div>
            </article>
          </div>
        </section>
      </section>
    </TerminalLayout>
  );
}
