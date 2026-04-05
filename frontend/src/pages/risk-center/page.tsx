import { TerminalLayout } from "../../shared/ui/terminal-layout";

const anomalyCards = [
  { value: "04", label: "阈值告警", tone: "warning" },
  { value: "00", label: "系统性异常", tone: "danger" },
];

const thresholdRows = [
  { label: "总风险预算 (USD)", value: "$1,200,000", min: "$0", max: "$5,000,000", width: "64%", tone: "accent" },
  { label: "单标的上限 (BTC/USDT)", value: "2.5%", min: "0.1%", max: "10.0%", width: "36%", tone: "accent" },
  { label: "最低保证金率阈值", value: "15.0%", min: "5%", max: "50%", width: "28%", tone: "warning" },
  { label: "执行延迟阈值 (ms)", value: "120ms", min: "10ms", max: "1000ms", width: "18%", tone: "danger" },
];

const rules = [
  ["异常滑点保护", "Slippage > 0.5%", "CANCEL_ORDER", "12", "20:42:11", "accent"],
  ["单日亏损熔断", "Daily_PnL < -2%", "KILL_SWITCH", "0", "--", "danger"],
  ["API 速率限制告警", "Rate > 80% Cap", "ALERT_ONLY", "154", "21:15:04", "warning"],
  ["延迟敏感性过滤", "Lat > 100ms", "RE_ROUTE", "42", "12:00:59", "muted"],
];

export function RiskCenterPage() {
  return (
    <TerminalLayout activePath="/risk">
      <section className="proto-page">
        <header className="proto-header">
          <div>
            <h2 className="proto-page__title">风控中心</h2>
            <p className="proto-page__subtitle">系统级风险监控与实时干预工作台</p>
          </div>
          <div className="proto-header__actions">
            <button className="proto-button proto-button--danger" type="button">
              全账户冻结
            </button>
            <button className="proto-button proto-button--ghost" type="button">
              停止新开仓
            </button>
          </div>
        </header>

        <section className="proto-main-grid">
          <div className="proto-side-stack">
            <article className="proto-panel">
              <p className="proto-panel__eyebrow">Current Risk</p>
              <h3>当前风险等级</h3>
              <div className="proto-risk-badge">NORMAL</div>
              <span className="proto-meta">风险评分: 12 / 100</span>
            </article>

            <article className="proto-panel">
              <p className="proto-panel__eyebrow">24h Stats</p>
              <h3>24h 异常情况统计</h3>
              <div className="proto-mini-grid">
                {anomalyCards.map((card) => (
                  <div className={`proto-mini-card proto-mini-card--${card.tone}`} key={card.label}>
                    <strong>{card.value}</strong>
                    <span>{card.label}</span>
                  </div>
                ))}
              </div>
            </article>

            <article className="proto-panel">
              <p className="proto-panel__eyebrow">Entity Access</p>
              <h3>实体访问控制</h3>
              <div className="proto-meter">
                <div className="proto-meter__row">
                  <span>白名单 (White-List)</span>
                  <strong>142 地址</strong>
                </div>
                <div className="proto-progress">
                  <div className="proto-progress__fill" style={{ width: "68%" }} />
                </div>
              </div>
              <div className="proto-meter">
                <div className="proto-meter__row">
                  <span>黑名单 (Black-List)</span>
                  <strong>1,204 地址</strong>
                </div>
                <div className="proto-progress">
                  <div className="proto-progress__fill proto-progress__fill--danger" style={{ width: "26%" }} />
                </div>
              </div>
              <div className="proto-action-grid proto-action-grid--two">
                <button className="proto-button proto-button--ghost" type="button">
                  编辑名单
                </button>
                <button className="proto-button proto-button--ghost" type="button">
                  同步规则
                </button>
              </div>
            </article>
          </div>

          <article className="proto-panel proto-panel--wide">
            <div className="proto-panel__header">
              <div>
                <p className="proto-panel__eyebrow">Threshold Engine</p>
                <h3>风险阈值动态配置</h3>
              </div>
              <span className="proto-chip proto-chip--active">实时生效</span>
            </div>

            <div className="proto-threshold-grid">
              {thresholdRows.map((row) => (
                <div className="proto-threshold" key={row.label}>
                  <div className="proto-threshold__top">
                    <span>{row.label}</span>
                    <strong>{row.value}</strong>
                  </div>
                  <div className="proto-progress">
                    <div className={`proto-progress__fill proto-progress__fill--${row.tone}`} style={{ width: row.width }} />
                  </div>
                  <div className="proto-threshold__axis">
                    <span>{row.min}</span>
                    <span>{row.max}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="proto-panel__header proto-panel__header--spaced">
              <div>
                <p className="proto-panel__eyebrow">Realtime Rules</p>
                <h3>实时风险规则与告警</h3>
              </div>
              <button className="proto-link-button" type="button">
                添加规则
              </button>
            </div>

            <div className="proto-table-shell">
              <div className="proto-table-row proto-table-row--risk proto-table-row--head">
                <span>状态</span>
                <span>规则名称</span>
                <span>触发条件</span>
                <span>响应动作</span>
                <span>触发次数</span>
                <span>最后活动</span>
              </div>
              {rules.map(([name, condition, action, count, lastSeen, tone]) => (
                <div className="proto-table-row proto-table-row--risk" key={name}>
                  <span className={`proto-dot proto-dot--${tone}`} />
                  <strong>{name}</strong>
                  <span>{condition}</span>
                  <span className="proto-pill">{action}</span>
                  <span>{count}</span>
                  <span>{lastSeen}</span>
                </div>
              ))}
            </div>
          </article>
        </section>
      </section>
    </TerminalLayout>
  );
}
