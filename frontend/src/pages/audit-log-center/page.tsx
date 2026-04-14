import { useQuery } from "@tanstack/react-query";
import { TerminalLayout } from "../../shared/ui/terminal-layout";
import { apiClient } from "../../shared/api/client";
import type { AuditEventListResponse, AuditEventRecord } from "../../shared/contracts/console";
import { useState } from "react";

function mapSeverityToTone(severity: string): "danger" | "warning" | "accent" | "muted" {
  if (severity === "critical" || severity === "error") return "danger";
  if (severity === "warning") return "warning";
  return "accent";
}

function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("zh-CN", { hour12: false });
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function getSeverityLabel(severity: string): string {
  const labels: Record<string, string> = {
    critical: "严重",
    error: "错误",
    warning: "警告",
    info: "信息",
    debug: "调试",
  };
  return labels[severity] || severity;
}

export function AuditLogCenterPage() {
  const [severityFilter, setSeverityFilter] = useState<string | undefined>(undefined);

  const { data, isLoading, error } = useQuery<AuditEventListResponse>({
    queryKey: ["audit-events", severityFilter],
    queryFn: () => apiClient.getAuditEvents<AuditEventListResponse>({ severity: severityFilter }),
  });

  const events = data?.events ?? [];

  // Timeline: 3 most recent events
  const timelineItems = events.slice(0, 3).map((event: AuditEventRecord) => ({
    title: event.event_type,
    time: formatTime(event.occurred_at),
    detail: event.summary,
    tone: mapSeverityToTone(event.severity),
  }));

  // Summary cards computed from events
  const totalEvents = events.length;
  const riskInterventions = events.filter((e: AuditEventRecord) => e.severity === "warning" || e.severity === "critical").length;
  const systemChanges = events.filter((e: AuditEventRecord) => e.event_type.toLowerCase().includes("config") || e.event_type.toLowerCase().includes("change")).length;
  const criticalAlerts = events.filter((e: AuditEventRecord) => e.severity === "critical").length;

  const summaryCards = [
    { title: "事件总数", value: totalEvents.toString(), subtitle: "当前查询范围" },
    { title: "风险干预次数", value: riskInterventions.toString(), subtitle: "警告及以上级别" },
    { title: "系统变更", value: systemChanges.toString(), subtitle: "配置或参数变更" },
    { title: "严重告警", value: criticalAlerts.toString(), subtitle: "需要立即处理" },
  ];

  // Health score: start at 100, subtract for critical/error events
  const criticalCount = events.filter((e: AuditEventRecord) => e.severity === "critical").length;
  const errorCount = events.filter((e: AuditEventRecord) => e.severity === "error").length;
  const healthScore = Math.max(0, 100 - (criticalCount * 10) - (errorCount * 5));

  const lastAuditTime = events.length > 0 ? formatTime(events[0].occurred_at) : "-";
  const unresolvedWarnings = events.filter((e: AuditEventRecord) => e.severity === "warning" || e.severity === "error").length;

  const handleFilterClick = (filter: string | undefined) => {
    setSeverityFilter(filter);
  };

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
            <span
              className={`proto-chip ${severityFilter === undefined ? "proto-chip--active" : ""}`}
              onClick={() => handleFilterClick(undefined)}
              style={{ cursor: "pointer" }}
            >
              所有事件
            </span>
            <span
              className={`proto-chip ${severityFilter === "warning" ? "proto-chip--active" : ""}`}
              onClick={() => handleFilterClick("warning")}
              style={{ cursor: "pointer" }}
            >
              风控报警
            </span>
            <span
              className={`proto-chip ${severityFilter === "info" ? "proto-chip--active" : ""}`}
              onClick={() => handleFilterClick("info")}
              style={{ cursor: "pointer" }}
            >
              系统变更
            </span>
            <button className="proto-button proto-button--primary" type="button">
              导出报告
            </button>
          </div>
        </header>

        {isLoading ? (
          <div className="proto-panel">
            <p className="proto-text--muted">正在加载...</p>
          </div>
        ) : error ? (
          <div className="proto-panel">
            <p className="proto-text--danger">数据暂时不可用</p>
          </div>
        ) : events.length === 0 ? (
          <div className="proto-panel">
            <p className="proto-text--muted">暂无审计事件</p>
          </div>
        ) : (
          <>
            <section className="proto-main-grid">
              <article className="proto-panel proto-panel--wide">
                <div className="proto-panel__header">
                  <div>
                    <p className="proto-panel__eyebrow">Lifecycle</p>
                    <h3>近期核心事件链路</h3>
                  </div>
                </div>
                <div className="proto-timeline">
                  {timelineItems.map((item) => (
                    <div className="proto-timeline__item" key={`${item.title}-${item.time}`}>
                      <span className={`proto-dot proto-dot--${item.tone}`} />
                      <strong>{item.title}</strong>
                      <span className="proto-meta">{item.time}</span>
                      <p>{item.detail}</p>
                    </div>
                  ))}
                </div>
              </article>

              <article className="proto-panel">
                <p className="proto-panel__eyebrow">Health</p>
                <h3>系统健康指数</h3>
                <div className="proto-score-ring">
                  <div className="proto-score-ring__core">{healthScore}%</div>
                </div>
                <div className="proto-kv-list">
                  <div><span>审计一致性验证通过</span><strong className="proto-text--accent">极佳</strong></div>
                  <div><span>最后审计时间</span><strong>{lastAuditTime}</strong></div>
                  <div><span>未解决警告</span><strong>{unresolvedWarnings}</strong></div>
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
                {events.map((event: AuditEventRecord) => (
                  <div className="proto-table-row proto-table-row--audit" key={event.event_id}>
                    <span>{formatTimestamp(event.occurred_at)}</span>
                    <span>{event.event_type}</span>
                    <strong>{event.event_id}</strong>
                    <span>{event.summary}</span>
                    <span className={`proto-text--${event.severity === "critical" || event.severity === "error" ? "danger" : event.severity === "warning" ? "warning" : "accent"}`}>
                      {getSeverityLabel(event.severity)}
                    </span>
                  </div>
                ))}
              </div>
            </article>

            <section className="proto-stat-grid">
              {summaryCards.map((card) => (
                <article className="proto-stat-card" key={card.title}>
                  <p>{card.title}</p>
                  <strong>{card.value}</strong>
                  <span>{card.subtitle}</span>
                </article>
              ))}
            </section>
          </>
        )}
      </section>
    </TerminalLayout>
  );
}
