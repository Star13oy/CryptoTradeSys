import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "../../shared/api/client";
import { TerminalLayout } from "../../shared/ui/terminal-layout";
import type { SymbolInfo, OrderPreview, OrderResult, ManualOrderRequest, HedgeOverviewItem } from "../../shared/contracts/console";

export function TradingPage() {
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [side, setSide] = useState<"long" | "short">("long");
  const [notional, setNotional] = useState(1000);
  const [mode, setMode] = useState<"paper" | "live">("paper");
  const [preview, setPreview] = useState<OrderPreview | null>(null);
  const [result, setResult] = useState<OrderResult | null>(null);

  const symbolsQuery = useQuery<SymbolInfo[]>({
    queryKey: ["trading-symbols"],
    queryFn: () => apiClient.getTradingSymbols<SymbolInfo[]>(),
  });

  const positionsQuery = useQuery<{ items: HedgeOverviewItem[] }>({
    queryKey: ["hedge-overview", 50],
    queryFn: () => apiClient.getHedgeOverview<{ items: HedgeOverviewItem[] }>({ exposure_limit_bps: 50 }),
    staleTime: 10_000,
  });

  const previewMutation = useMutation({
    mutationFn: (params: ManualOrderRequest) => apiClient.previewOrder<OrderPreview>(params),
    onSuccess: (data) => {
      setPreview(data);
      setResult(null);
    },
  });

  const executeMutation = useMutation({
    mutationFn: (params: ManualOrderRequest) => apiClient.executeOrder<OrderResult>(params),
    onSuccess: (data) => {
      setResult(data);
      setPreview(null);
      positionsQuery.refetch();
    },
  });

  const closeMutation = useMutation({
    mutationFn: (tradeId: string) => apiClient.panicSell({ trade_id: tradeId }),
    onSuccess: () => positionsQuery.refetch(),
  });

  const handlePreview = () => {
    setPreview(null);
    setResult(null);
    previewMutation.mutate({ symbol, side, notional, mode });
  };

  const handleExecute = () => {
    if (!preview) return;
    executeMutation.mutate({ symbol, side, notional, mode });
  };

  const selectedSymbol = symbolsQuery.data?.find((s) => s.symbol === symbol);

  return (
    <TerminalLayout activePath="/trade">
      <section className="proto-page">
        <header className="proto-header">
          <div>
            <h2 className="proto-page__title">交易下单</h2>
            <p className="proto-page__subtitle">手动交易面板</p>
          </div>
        </header>

        <div className="proto-main-grid">
          <div className="proto-side-stack">
            <div className="proto-panel">
              <div className="proto-panel__header">
                <div>
                  <p className="proto-panel__eyebrow">下单</p>
                  <h3>订单参数</h3>
                </div>
              </div>

              <div className="proto-form-stack">
                <div className="proto-field">
                  <span>交易对</span>
                  <select value={symbol} onChange={(e) => setSymbol(e.target.value)} disabled={symbolsQuery.isPending}>
                    {symbolsQuery.data?.map((s) => (
                      <option key={s.symbol} value={s.symbol}>
                        {s.symbol}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="proto-field">
                  <span>方向</span>
                  <div className="proto-action-grid">
                    <button
                      className={`proto-button ${side === "long" ? "proto-button--primary" : "proto-button--ghost"}`}
                      type="button"
                      onClick={() => setSide("long")}
                    >
                      做多 (Long)
                    </button>
                    <button
                      className={`proto-button ${side === "short" ? "proto-button--primary" : "proto-button--ghost"}`}
                      type="button"
                      onClick={() => setSide("short")}
                    >
                      做空 (Short)
                    </button>
                  </div>
                </div>

                <div className="proto-field">
                  <span>名义金额 (USDT)</span>
                  <input type="number" value={notional} onChange={(e) => setNotional(Number(e.target.value))} min={100} step={100} />
                </div>

                <div className="proto-field">
                  <span>模式</span>
                  <div className="proto-action-grid">
                    <button
                      className={`proto-button ${mode === "paper" ? "proto-button--primary" : "proto-button--ghost"}`}
                      type="button"
                      onClick={() => setMode("paper")}
                    >
                      Paper
                    </button>
                    <button
                      className={`proto-button ${mode === "live" ? "proto-button--primary" : "proto-button--ghost"}`}
                      type="button"
                      onClick={() => setMode("live")}
                    >
                      Live
                    </button>
                  </div>
                </div>

                <button
                  className="proto-button proto-button--primary"
                  type="button"
                  disabled={previewMutation.isPending}
                  onClick={handlePreview}
                >
                  {previewMutation.isPending ? "预览中..." : "预览下单"}
                </button>

                {preview && (
                  <div className="proto-alert proto-alert--accent">
                    <div className="proto-alert__topline">
                      <span>订单预览</span>
                    </div>
                    <div className="proto-kv-list">
                      <div>
                        <span>现货价格</span>
                        <strong>${preview.spot_price.toFixed(2)}</strong>
                      </div>
                      <div>
                        <span>永续价格</span>
                        <strong>${preview.perp_price.toFixed(2)}</strong>
                      </div>
                      <div>
                        <span>资金费率</span>
                        <strong>{(preview.funding_rate * 100).toFixed(4)}%</strong>
                      </div>
                      <div>
                        <span>预估费用</span>
                        <strong>${preview.estimated_fees_usd.toFixed(2)}</strong>
                      </div>
                      <div>
                        <span>净边际</span>
                        <strong className="proto-text--accent">{preview.estimated_net_edge_bps.toFixed(2)} bps</strong>
                      </div>
                      <div>
                        <span>风险决策</span>
                        <strong className={preview.risk_decision === "allow" ? "proto-text--accent" : "proto-text--danger"}>
                          {preview.risk_decision}
                        </strong>
                      </div>
                    </div>
                    <button
                      className="proto-button proto-button--primary"
                      type="button"
                      style={{ marginTop: 12 }}
                      disabled={executeMutation.isPending}
                      onClick={handleExecute}
                    >
                      {executeMutation.isPending ? "执行中..." : "确认下单"}
                    </button>
                  </div>
                )}

                {result && (
                  <div className="proto-alert proto-alert--accent">
                    <div className="proto-alert__topline">
                      <span>执行结果</span>
                    </div>
                    <div className="proto-kv-list">
                      <div>
                        <span>交易 ID</span>
                        <strong>{result.trade_id}</strong>
                      </div>
                      <div>
                        <span>状态</span>
                        <strong className="proto-text--accent">{result.status}</strong>
                      </div>
                      <div>
                        <span>现货成交</span>
                        <strong>${result.spot_filled.toFixed(2)}</strong>
                      </div>
                      <div>
                        <span>永续成交</span>
                        <strong>${result.perp_filled.toFixed(2)}</strong>
                      </div>
                      <div>
                        <span>执行时间</span>
                        <strong>{new Date(result.executed_at).toLocaleString("zh-CN")}</strong>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {selectedSymbol && (
              <div className="proto-panel">
                <div className="proto-panel__header">
                  <div>
                    <p className="proto-panel__eyebrow">市场数据</p>
                    <h3>{symbol}</h3>
                  </div>
                </div>
                <div className="proto-kv-list">
                  <div>
                    <span>标记价格</span>
                    <strong>${selectedSymbol.mark_price.toFixed(2)}</strong>
                  </div>
                  <div>
                    <span>资金费率</span>
                    <strong>{(selectedSymbol.funding_rate * 100).toFixed(4)}%</strong>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="proto-panel proto-panel--wide">
            <div className="proto-panel__header">
              <div>
                <p className="proto-panel__eyebrow">持仓</p>
                <h3>活跃仓位</h3>
              </div>
            </div>

            {positionsQuery.isPending ? (
              <p className="proto-meta">加载中...</p>
            ) : positionsQuery.isError ? (
              <p className="proto-text--danger">加载失败</p>
            ) : positionsQuery.data?.items && positionsQuery.data.items.length > 0 ? (
              <div className="proto-table-shell">
                <div className="proto-table-row proto-table-row--head">
                  <span>交易对</span>
                  <span>状态</span>
                  <span>健康度</span>
                  <span>净敞口</span>
                  <span>敞口 bps</span>
                  <span>操作</span>
                </div>
                {positionsQuery.data.items.map((pos) => (
                  <div key={pos.trade_id} className="proto-table-row">
                    <span>
                      <strong>{pos.symbol}</strong>
                      <span className="proto-meta">{pos.mode}</span>
                    </span>
                    <span>
                      <span
                        className={`proto-chip ${
                          pos.health === "healthy"
                            ? "proto-chip--active"
                            : pos.health === "monitoring"
                              ? "proto-tag-live"
                              : "proto-chip"
                        }`}
                      >
                        {pos.status}
                      </span>
                    </span>
                    <span>
                      <span
                        className={`proto-chip ${
                          pos.health === "healthy"
                            ? "proto-chip--active"
                            : pos.health === "monitoring"
                              ? "proto-tag-live"
                              : "proto-chip"
                        }`}
                      >
                        {pos.health}
                      </span>
                    </span>
                    <span>
                      <strong className={Math.abs(pos.net_exposure) > 50 ? "proto-text--warning" : ""}>
                        ${pos.net_exposure.toFixed(2)}
                      </strong>
                    </span>
                    <span>
                      <strong className={Math.abs(pos.exposure_bps) > 50 ? "proto-text--warning" : ""}>
                        {pos.exposure_bps.toFixed(1)} bps
                      </strong>
                    </span>
                    <span>
                      <button
                        className="proto-button proto-button--danger"
                        type="button"
                        style={{ fontSize: 12, padding: "6px 12px" }}
                        disabled={closeMutation.isPending}
                        onClick={() => {
                          if (window.confirm(`确认平仓 ${pos.symbol}？`)) {
                            closeMutation.mutate(pos.trade_id);
                          }
                        }}
                      >
                        平仓
                      </button>
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="proto-meta">暂无活跃仓位</p>
            )}
          </div>
        </div>
      </section>
    </TerminalLayout>
  );
}
