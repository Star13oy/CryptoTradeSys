import { useQuery } from "@tanstack/react-query";

import { apiClient } from "../../shared/api/client";
import type { ExecutionSummaryResponse, ReconciliationCandidateListResponse } from "../../shared/contracts/console";
import { TerminalLayout } from "../../shared/ui/terminal-layout";

function buildRiskLevel(summary: ExecutionSummaryResponse | undefined) {
  if (!summary) {
    return { label: "SYNCING", score: 0 };
  }
  const criticalCount = summary.recent_incidents.filter((item) => item.severity === "critical").length;
  const errorCount = summary.recent_incidents.filter((item) => item.severity === "error").length;
  const warningCount = summary.recent_incidents.filter((item) => item.severity === "warning").length;
  const recoveryCount = summary.recovery_queue.length;
  const score = Math.min(100, criticalCount * 45 + errorCount * 25 + warningCount * 10 + recoveryCount * 12);

  if (criticalCount > 0 || recoveryCount >= 3) {
    return { label: "CRITICAL", score };
  }
  if (errorCount > 0 || warningCount > 0 || recoveryCount > 0) {
    return { label: "GUARDED", score };
  }
  return { label: "NORMAL", score };
}

function statusCount(summary: ExecutionSummaryResponse | undefined, status: string) {
  return summary?.status_counts.find((item) => item.status === status)?.count ?? 0;
}

function formatMissingOrderIds(missingOrderIds: string[]) {
  return missingOrderIds.length > 0 ? missingOrderIds.join(", ") : "—";
}

export function RiskCenterPage() {
  const summaryQuery = useQuery({
    queryKey: ["execution-summary", 6],
    queryFn: () => apiClient.getExecutionSummary<ExecutionSummaryResponse>({ limit_incidents: 6 }),
  });
  const candidatesQuery = useQuery({
    queryKey: ["reconciliation-candidates"],
    queryFn: () => apiClient.getReconciliationCandidates<ReconciliationCandidateListResponse>(),
  });

  const summary = summaryQuery.data;
  const riskLevel = buildRiskLevel(summary);
  const anomalyCards = [
    {
      value: String(summary?.recent_incidents.filter((item) => item.severity === "warning").length ?? 0).padStart(2, "0"),
      label: "阈值告警",
      tone: "warning",
    },
    {
      value: String(summary?.recent_incidents.filter((item) => item.severity === "critical").length ?? 0).padStart(2, "0"),
      label: "系统性异常",
      tone: "danger",
    },
  ];
  const thresholdRows = [
    {
      label: "恢复队列规模",
      value: `${summary?.recovery_queue.length ?? 0} 笔`,
      min: "0",
      max: "10+",
      width: `${Math.min(100, (summary?.recovery_queue.length ?? 0) * 18)}%`,
      tone: (summary?.recovery_queue.length ?? 0) > 0 ? "warning" : "accent",
    },
    {
      label: "失败执行数量",
      value: `${statusCount(summary, "failed")} 笔`,
      min: "0",
      max: "10+",
      width: `${Math.min(100, statusCount(summary, "failed") * 18)}%`,
      tone: statusCount(summary, "failed") > 0 ? "danger" : "accent",
    },
    {
      label: "待恢复执行数量",
      value: `${statusCount(summary, "recovery_pending")} 笔`,
      min: "0",
      max: "10+",
      width: `${Math.min(100, statusCount(summary, "recovery_pending") * 18)}%`,
      tone: statusCount(summary, "recovery_pending") > 0 ? "warning" : "accent",
    },
    {
      label: "风险评分",
      value: `${riskLevel.score} / 100`,
      min: "0",
      max: "100",
      width: `${Math.max(8, riskLevel.score)}%`,
      tone: riskLevel.label === "CRITICAL" ? "danger" : riskLevel.label === "GUARDED" ? "warning" : "accent",
    },
  ];
  const reconciliationCandidates = candidatesQuery.data?.candidates ?? [];
  const candidateRows = reconciliationCandidates.map((item) => [
      item.trade_id,
      item.symbol,
      formatMissingOrderIds(item.missing_order_ids),
      item.suggested_action,
      item.needs_attention ? "是" : "否",
      item.needs_attention ? "danger" : "accent",
    ]);
  const rules = summary?.recent_incidents.map((item) => [
    item.severity === "critical" ? "关键事故" : item.severity === "error" ? "执行异常" : "告警事件",
    item.event_type,
    item.trade_id ? `TRADE:${item.trade_id}` : "NO_TRADE",
    item.severity.toUpperCase(),
    item.summary,
    item.severity === "critical" ? "danger" : item.severity === "error" ? "warning" : "muted",
  ]) ?? [
    ["风险规则同步中", "等待 execution summary", "--", "SYNC", "暂无风险事件", "muted"],
  ];
  const footerContent = (
    <>
      <span>RISK LEVEL / {riskLevel.label}</span>
      <span>{summary ? `恢复队列 ${summary.recovery_queue.length} 笔` : "等待执行摘要同步"}</span>
      <span>
        {candidatesQuery.data ? `对账候选 ${reconciliationCandidates.length} 笔` : "等待对账候选同步"}
      </span>
      <span>{summaryQuery.isError ? "执行摘要异常" : "EXECUTION SUMMARY ONLINE"}</span>
    </>
  );

  return (
    <TerminalLayout activePath="/risk" footerContent={footerContent}>
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
              <div className="proto-risk-badge">{riskLevel.label}</div>
              <span className="proto-meta">风险评分: {riskLevel.score} / 100</span>
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
                  <span>恢复队列 (Recovery Queue)</span>
                  <strong>{summary?.recovery_queue.length ?? 0} 笔</strong>
                </div>
                <div className="proto-progress">
                  <div className="proto-progress__fill" style={{ width: `${Math.min(100, (summary?.recovery_queue.length ?? 0) * 18)}%` }} />
                </div>
              </div>
              <div className="proto-meter">
                <div className="proto-meter__row">
                  <span>最近高危事件</span>
                  <strong>{summary?.recent_incidents.filter((item) => item.severity !== "warning").length ?? 0} 条</strong>
                </div>
                <div className="proto-progress">
                  <div
                    className="proto-progress__fill proto-progress__fill--danger"
                    style={{
                      width: `${Math.min(
                        100,
                        (summary?.recent_incidents.filter((item) => item.severity !== "warning").length ?? 0) * 18
                      )}%`,
                    }}
                  />
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

            {summaryQuery.isPending ? <p className="panel-state">正在同步执行风险摘要</p> : null}
            {summaryQuery.isError ? <p className="panel-alert">执行风险摘要暂时不可用</p> : null}
            {candidatesQuery.isPending ? <p className="panel-state panel-state-subtle">正在同步对账候选项</p> : null}
            {candidatesQuery.isError ? <p className="panel-alert">对账候选项暂时不可用</p> : null}

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
                <p className="proto-panel__eyebrow">Reconciliation Candidates</p>
                <h3>对账候选项</h3>
              </div>
              <span className="proto-chip proto-chip--active">自动接入</span>
            </div>

            <div className="proto-table-shell">
              <div
                className="proto-table-row proto-table-row--risk proto-table-row--head"
                style={{ gridTemplateColumns: "1fr 0.9fr 1.4fr 1fr 0.7fr" }}
              >
                <span>交易 ID</span>
                <span>交易对</span>
                <span>缺失订单</span>
                <span>建议动作</span>
                <span>需关注</span>
              </div>
              {!candidatesQuery.isPending && !candidatesQuery.isError && candidateRows.length === 0 ? (
                <div className="table-empty">暂无需要对账的候选项</div>
              ) : null}
              {candidateRows.map(([tradeId, symbol, missingOrderIds, suggestedAction, needsAttention, tone]) => (
                <div
                  className="proto-table-row proto-table-row--risk"
                  key={tradeId}
                  style={{ gridTemplateColumns: "1fr 0.9fr 1.4fr 1fr 0.7fr" }}
                >
                  <strong>{tradeId}</strong>
                  <span>{symbol}</span>
                  <span>{missingOrderIds}</span>
                  <span className="proto-pill">{suggestedAction}</span>
                  <span className={`proto-pill proto-text--${tone}`}>{needsAttention}</span>
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
                <div className="proto-table-row proto-table-row--risk" key={`${name}-${condition}-${lastSeen}`}>
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
