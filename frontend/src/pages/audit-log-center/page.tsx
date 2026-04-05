import { TerminalLayout } from "../../shared/ui/terminal-layout";

const timelineItems = [
  ["订单执行", "12:45:01 PM", "BTC/USDT 限价买入 $64,210.50", "accent"],
  ["风控扫描", "12:45:02 PM", "订单滑点率 0.12% - 安全", "warning"],
  ["链上存证", "12:45:15 PM", "TxID: 0x82f...a12b 已验证", "muted"],
] as const;

const auditRows = [
  ["2023-10-27 12:45:01", "订单成交", "BTC/USDT-20231027-001", "策略 [Momentum_Alpha_v3] 触发买入指令，价格 $64,210.50，数量 0.45 BTC", "成功"],
  ["2023-10-27 12:44:59", "风控干预", "RMS-CIRCUIT-092", "由于波动率激增 1.5%，触发自动调整最大持仓规模限制。", "自动调整"],
  ["2023-10-27 12:43:12", "配置变更", "USER-ADMIN-001", "管理员 [Quant_Master] 更新了策略网格参数。", "已存档"],
  ["2023-10-27 12:40:05", "异常告警", "API-BINANCE-WSS", "Websocket 连接延迟 > 200ms。自动切换至备用节点。", "已恢复"],
];

const summaryCards = [
  ["今日订单总数", "1,428", "+12.5%"],
  ["风险干预次数", "42", "较昨日持平"],
  ["系统变更日志", "18", "仅管理员"],
  ["日志存储占用", "4.2 GB", "健康状态"],
] as const;

export function AuditLogCenterPage() {
  return (
    <TerminalLayout activePath="/audit">
      <section className="proto-page">
        <header className="proto-header">
          <div>
            <h2 className="proto-page__title">审计与日志中心</h2>
            <p className="proto-page__subtitle">
              实时监控系统运行状态、订单生命周期以及风控干预记录。所有操作均已由区块链存证系统进行异步验证。
            </p>
          </div>
          <div className="proto-header__actions proto-header__actions--filter">
            <span className="proto-chip proto-chip--active">所有事件</span>
            <span className="proto-chip">风控报警</span>
            <span className="proto-chip">系统变更</span>
            <button className="proto-button proto-button--primary" type="button">
              导出报告
            </button>
          </div>
        </header>

        <section className="proto-main-grid">
          <article className="proto-panel proto-panel--wide">
            <div className="proto-panel__header">
              <div>
                <p className="proto-panel__eyebrow">Lifecycle</p>
                <h3>近期核心事件链路</h3>
              </div>
            </div>
            <div className="proto-timeline">
              {timelineItems.map(([title, time, detail, tone]) => (
                <div className="proto-timeline__item" key={`${title}-${time}`}>
                  <span className={`proto-dot proto-dot--${tone}`} />
                  <strong>{title}</strong>
                  <span className="proto-meta">{time}</span>
                  <p>{detail}</p>
                </div>
              ))}
            </div>
          </article>

          <article className="proto-panel">
            <p className="proto-panel__eyebrow">Health</p>
            <h3>系统健康指数</h3>
            <div className="proto-score-ring">
              <div className="proto-score-ring__core">98%</div>
            </div>
            <div className="proto-kv-list">
              <div><span>审计一致性验证通过</span><strong className="proto-text--accent">极佳</strong></div>
              <div><span>最后审计时间</span><strong>13:00:05</strong></div>
              <div><span>未解决警告</span><strong>0</strong></div>
            </div>
          </article>
        </section>

        <article className="proto-panel">
          <div className="proto-panel__header">
            <div>
              <p className="proto-panel__eyebrow">Detailed Logs</p>
              <h3>详细审计日志</h3>
            </div>
          </div>
          <div className="proto-table-shell">
            <div className="proto-table-row proto-table-row--audit proto-table-row--head">
              <span>时间戳</span>
              <span>事件类型</span>
              <span>关联对象</span>
              <span>摘要</span>
              <span>状态</span>
            </div>
            {auditRows.map((row) => (
              <div className="proto-table-row proto-table-row--audit" key={row[0]}>
                <span>{row[0]}</span>
                <span>{row[1]}</span>
                <strong>{row[2]}</strong>
                <span>{row[3]}</span>
                <span className="proto-text--accent">{row[4]}</span>
              </div>
            ))}
          </div>
        </article>

        <section className="proto-stat-grid">
          {summaryCards.map((card) => (
            <article className="proto-stat-card" key={card[0]}>
              <p>{card[0]}</p>
              <strong>{card[1]}</strong>
              <span>{card[2]}</span>
            </article>
          ))}
        </section>
      </section>
    </TerminalLayout>
  );
}
