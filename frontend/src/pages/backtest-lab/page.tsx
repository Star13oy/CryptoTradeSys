import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { TerminalLayout } from "../../shared/ui/terminal-layout";
import { apiClient } from "../../shared/api/client";
import type {
  BacktestDatasetListResponse,
  BacktestResult,
  BacktestConfig,
  BacktestDatasetSummary,
} from "../../shared/contracts/console";

interface HistoryEntry extends BacktestResult {
  id: string;
  datasetTitle: string;
  timestamp: string;
}

const DEFAULT_CONFIG: BacktestConfig = {
  notional_per_trade: 1000,
  min_score: 0,
  min_net_edge_bps: 0,
  top_k: 5,
  accept_reviewed: false,
};

const TOP_K_OPTIONS = [2, 5, 10, 15, 20];

export function BacktestLabPage() {
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>("");
  const [backtestConfig, setBacktestConfig] = useState<BacktestConfig>(DEFAULT_CONFIG);
  const [limitRecentPeriods, setLimitRecentPeriods] = useState<number | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  const { data: datasetsData, isLoading: datasetsLoading, error: datasetsError } = useQuery<
    BacktestDatasetListResponse
  >({
    queryKey: ["backtest-datasets"],
    queryFn: () => apiClient.getBacktestDatasets<BacktestDatasetListResponse>(),
  });

  const runBacktestMutation = useMutation<BacktestResult, Error, void>({
    mutationFn: async () => {
      if (!selectedDatasetId) {
        throw new Error("请先选择数据集");
      }
      return apiClient.runBacktestFromDataset<BacktestResult>({
        dataset_id: selectedDatasetId,
        config: backtestConfig,
        limit_recent_periods: limitRecentPeriods ?? undefined,
      });
    },
    onSuccess: (data) => {
      const selectedDataset = datasetsData?.datasets.find((d) => d.dataset_id === selectedDatasetId);
      const newEntry: HistoryEntry = {
        ...data,
        id: `BK-${Date.now()}`,
        datasetTitle: selectedDataset?.title ?? selectedDatasetId,
        timestamp: new Date().toISOString(),
      };
      setHistory((prev) => [newEntry, ...prev]);
    },
  });

  const selectedDataset = datasetsData?.datasets.find((d) => d.dataset_id === selectedDatasetId);
  const latestResult = history[0];

  const formatPnL = (value: number): string => {
    const sign = value >= 0 ? "+" : "";
    return `${sign}$${value.toFixed(2)}`;
  };

  const formatPercentage = (value: number): string => {
    const sign = value >= 0 ? "+" : "";
    return `${sign}${value.toFixed(2)}%`;
  };

  const topK = backtestConfig.top_k;

  // Compute equity curve and drawdown from trades
  const computeEquityCurve = (trades: BacktestResult["trades"]) => {
    if (!trades || trades.length === 0) return null;

    let cumulativePnL = 0;
    const points = trades.map((trade) => {
      cumulativePnL += trade.estimated_pnl;
      return cumulativePnL;
    });

    const minPnL = Math.min(...points, 0);
    const maxPnL = Math.max(...points);
    const range = maxPnL - minPnL || 1;

    // Generate SVG path
    const width = 800;
    const height = 240;
    const stepX = width / (points.length - 1 || 1);

    const pathD = points
      .map((pnl, i) => {
        const x = i * stepX;
        const y = height - ((pnl - minPnL) / range) * height;
        return `${i === 0 ? "M" : "L"} ${x},${y}`;
      })
      .join(" ");

    const areaD = `${pathD} L ${width},${height} L 0,${height} Z`;

    // Compute drawdown bars
    let peak = 0;
    const drawdowns = points.map((pnl) => {
      peak = Math.max(peak, pnl);
      const drawdown = peak - pnl;
      return drawdown;
    });

    const maxDrawdown = Math.max(...drawdowns, 1);

    const bars = drawdowns.map((dd, i) => ({
      height: (dd / maxDrawdown) * 100,
    }));

    return { areaD, pathD, bars };
  };

  const equityCurveData = latestResult ? computeEquityCurve(latestResult.trades) : null;

  const footerContent = (
    <>
      <span>引擎状态: 就绪</span>
      <span>数据集: {datasetsData?.datasets.length ?? 0} 个</span>
      {runBacktestMutation.isPending && <span>执行中...</span>}
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
            <button
              className="proto-button proto-button--ghost"
              type="button"
              onClick={() => console.log("Export clicked")}
            >
              导出报告
            </button>
            <button
              className="proto-button proto-button--primary"
              type="button"
              onClick={() => runBacktestMutation.mutate()}
              disabled={!selectedDatasetId || runBacktestMutation.isPending}
            >
              {runBacktestMutation.isPending ? "执行中..." : "执行回测"}
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
                  <span>数据集选择</span>
                  {datasetsLoading ? (
                    <select disabled>
                      <option>正在加载数据集...</option>
                    </select>
                  ) : datasetsError ? (
                    <select disabled>
                      <option>加载失败</option>
                    </select>
                  ) : !datasetsData?.datasets.length ? (
                    <select disabled>
                      <option>暂无可用数据集</option>
                    </select>
                  ) : (
                    <select
                      value={selectedDatasetId}
                      onChange={(e) => setSelectedDatasetId(e.target.value)}
                    >
                      <option value="">请选择数据集</option>
                      {datasetsData.datasets.map((ds) => (
                        <option key={ds.dataset_id} value={ds.dataset_id}>
                          {ds.title}
                        </option>
                      ))}
                    </select>
                  )}
                </label>
                {selectedDataset && (
                  <div className="proto-kv-list">
                    <div>
                      <span>数据来源</span>
                      <strong>{selectedDataset.source}</strong>
                    </div>
                    <div>
                      <span>周期数量</span>
                      <strong>{selectedDataset.period_count}</strong>
                    </div>
                    {selectedDataset.observed_from && selectedDataset.observed_to && (
                      <div>
                        <span>时间范围</span>
                        <strong>
                          {selectedDataset.observed_from} 至 {selectedDataset.observed_to}
                        </strong>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </article>

            <article className="proto-panel">
              <p className="proto-panel__eyebrow">Parameter Matrix</p>
              <h3>参数矩阵</h3>
              <div className="proto-form-stack">
                <label className="proto-field">
                  <span>收益阈值 (Alpha)</span>
                  <input
                    type="number"
                    step="0.1"
                    value={backtestConfig.min_score}
                    onChange={(e) =>
                      setBacktestConfig({ ...backtestConfig, min_score: parseFloat(e.target.value) || 0 })
                    }
                  />
                </label>
                <div className="proto-chip-row">
                  {TOP_K_OPTIONS.map((value) => (
                    <span
                      className={`proto-chip${topK === value ? " proto-chip--active" : ""}`}
                      key={value}
                      onClick={() => setBacktestConfig({ ...backtestConfig, top_k: value })}
                      style={{ cursor: "pointer" }}
                    >
                      {value}
                    </span>
                  ))}
                </div>
                <label className="proto-field">
                  <span>风控阈值 (Net Edge bps)</span>
                  <input
                    type="number"
                    step="1"
                    value={backtestConfig.min_net_edge_bps}
                    onChange={(e) =>
                      setBacktestConfig({
                        ...backtestConfig,
                        min_net_edge_bps: parseFloat(e.target.value) || 0,
                      })
                    }
                  />
                </label>
                <label className="proto-field">
                  <span>时间范围 (最近周期数)</span>
                  <input
                    type="number"
                    step="1"
                    min="1"
                    placeholder="全部"
                    value={limitRecentPeriods ?? ""}
                    onChange={(e) =>
                      setLimitRecentPeriods(e.target.value ? parseInt(e.target.value, 10) : null)
                    }
                  />
                </label>
              </div>
            </article>
          </div>

          <div className="proto-wide-stack">
            <section className="proto-stat-grid">
              <article className="proto-stat-card">
                <p>预估总盈亏</p>
                <strong className={`proto-text--${latestResult?.estimated_total_pnl >= 0 ? "accent" : "danger"}`}>
                  {latestResult ? formatPnL(latestResult.estimated_total_pnl) : "--"}
                </strong>
              </article>
              <article className="proto-stat-card">
                <p>候选机会</p>
                <strong>{latestResult?.candidates_seen ?? "--"}</strong>
              </article>
              <article className="proto-stat-card">
                <p>平均评分</p>
                <strong>{latestResult ? latestResult.average_score.toFixed(2) : "--"}</strong>
              </article>
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
              {equityCurveData ? (
                <svg className="proto-chart" preserveAspectRatio="none" viewBox="0 0 800 240">
                  <defs>
                    <linearGradient id="backtest-curve" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0%" stopColor="#6bd8cb" stopOpacity="0.35" />
                      <stop offset="100%" stopColor="#6bd8cb" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path d={equityCurveData.areaD} fill="url(#backtest-curve)" />
                  <path
                    d={equityCurveData.pathD}
                    fill="none"
                    stroke="#6bd8cb"
                    strokeLinecap="round"
                    strokeWidth="3"
                  />
                </svg>
              ) : (
                <div className="proto-chart" style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "240px", color: "#666" }}>
                  暂无数据
                </div>
              )}
            </article>

            <div className="proto-dual-grid">
              <article className="proto-panel">
                <p className="proto-panel__eyebrow">Drawdown</p>
                <h3>回测回撤 (Drawdown Depth)</h3>
                {equityCurveData ? (
                  <div className="proto-drawdown">
                    {equityCurveData.bars.slice(0, 20).map((bar, index) => (
                      <div
                        className="proto-drawdown__bar"
                        key={`dd-${index}`}
                        style={{ height: `${bar.height}%` }}
                      />
                    ))}
                  </div>
                ) : (
                  <div style={{ color: "#666", padding: "1rem" }}>暂无数据</div>
                )}
              </article>
              <article className="proto-panel">
                <p className="proto-panel__eyebrow">Sensitivity</p>
                <h3>参数敏感度热力图</h3>
                <div className="proto-heatmap">
                  {Array.from({ length: 36 }, (_, index) => (
                    <span
                      className={`proto-heatmap__cell proto-heatmap__cell--${(index % 6) + 1}`}
                      key={index}
                    />
                  ))}
                </div>
              </article>
            </div>
          </div>

          <div className="proto-side-stack">
            <article className="proto-panel">
              <p className="proto-panel__eyebrow">Summary</p>
              <h3>交易统计摘要</h3>
              {latestResult ? (
                <div className="proto-kv-list">
                  <div>
                    <span>处理周期数</span>
                    <strong>{latestResult.periods_processed}</strong>
                  </div>
                  <div>
                    <span>选中交易数</span>
                    <strong>{latestResult.selected_trades}</strong>
                  </div>
                  <div>
                    <span>平均净边缘</span>
                    <strong>{latestResult.average_net_edge_bps.toFixed(2)} bps</strong>
                  </div>
                  <div>
                    <span>平均评分</span>
                    <strong>{latestResult.average_score.toFixed(2)}</strong>
                  </div>
                  <div>
                    <span>平均预估边缘</span>
                    <strong>{latestResult.average_projected_edge_bps.toFixed(2)} bps</strong>
                  </div>
                </div>
              ) : (
                <div className="proto-kv-list">
                  <div>
                    <span>处理周期数</span>
                    <strong>--</strong>
                  </div>
                  <div>
                    <span>选中交易数</span>
                    <strong>--</strong>
                  </div>
                  <div>
                    <span>平均净边缘</span>
                    <strong>-- bps</strong>
                  </div>
                  <div>
                    <span>平均评分</span>
                    <strong>--</strong>
                  </div>
                  <div>
                    <span>平均预估边缘</span>
                    <strong>-- bps</strong>
                  </div>
                </div>
              )}
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
              <span>数据集</span>
              <span>预估盈亏</span>
              <span>候选机会</span>
              <span>选中交易</span>
              <span>平均评分</span>
              <span>状态</span>
            </div>
            {history.length === 0 ? (
              <div className="proto-table-row proto-table-row--history">
                <span style={{ color: "#666", gridColumn: "1 / -1", textAlign: "center", padding: "1rem" }}>
                  暂无历史回测记录
                </span>
              </div>
            ) : (
              history.map((entry) => (
                <div className="proto-table-row proto-table-row--history" key={entry.id}>
                  <span>{entry.id}</span>
                  <strong>{entry.datasetTitle}</strong>
                  <span className={entry.estimated_total_pnl >= 0 ? "proto-text--accent" : "proto-text--danger"}>
                    {formatPnL(entry.estimated_total_pnl)}
                  </span>
                  <span>{entry.candidates_seen}</span>
                  <span>{entry.selected_trades}</span>
                  <span>{entry.average_score.toFixed(2)}</span>
                  <span className="proto-pill">SUCCESS</span>
                </div>
              ))
            )}
          </div>
        </article>
      </section>
    </TerminalLayout>
  );
}
