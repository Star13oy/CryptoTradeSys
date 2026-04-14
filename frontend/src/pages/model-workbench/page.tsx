import { useQuery, useMutation } from "@tanstack/react-query";

import { apiClient } from "../../shared/api/client";
import type {
  TuningState,
  AdaptationRecommendationResponse,
  LearningSampleListResponse,
  LearningSampleImportResponse,
  TuningPackage,
  ScoreConfigSnapshot,
  RiskConfigSnapshot,
  AdaptationMetrics,
  LearningTradeSample,
} from "../../shared/contracts/console";
import { TerminalLayout } from "../../shared/ui/terminal-layout";

const timeFormatter = new Intl.DateTimeFormat("zh-CN", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

function formatScoreValue(value: number, digits = 2) {
  return value.toFixed(digits);
}

function normalizeScoreToPercentage(score: number, minScore = 0, maxScore = 100): number {
  const normalized = ((score - minScore) / (maxScore - minScore)) * 100;
  return Math.max(0, Math.min(100, normalized));
}

function formatWeightAsPercentage(weight: number, maxWeight = 1.0): number {
  return Math.max(0, Math.min(100, (weight / maxWeight) * 100));
}

export function ModelWorkbenchPage() {
  const stateQuery = useQuery<TuningState>({
    queryKey: ["adaptation-state"],
    queryFn: () => apiClient.getAdaptationState<TuningState>(),
  });

  const recommendQuery = useQuery<AdaptationRecommendationResponse>({
    queryKey: ["adaptation-recommendation"],
    queryFn: () => apiClient.recommendAdaptation<AdaptationRecommendationResponse>(),
  });

  const samplesQuery = useQuery<LearningSampleListResponse>({
    queryKey: ["adaptation-samples"],
    queryFn: () => apiClient.getAdaptationSamples<LearningSampleListResponse>(),
  });

  const applyMutation = useMutation<TuningState, Error, { package: TuningPackage; confirmed: boolean }>({
    mutationFn: ({ package: pkg, confirmed }) =>
      apiClient.applyAdaptation<TuningState>({ package: pkg, confirmed }),
    onSuccess: () => {
      stateQuery.refetch();
      recommendQuery.refetch();
    },
  });

  const extractSamplesMutation = useMutation<LearningSampleImportResponse, Error, { mode: "append" | "replace" }>({
    mutationFn: (body) => apiClient.extractSamplesFromJournal<LearningSampleImportResponse>(body),
    onSuccess: () => {
      samplesQuery.refetch();
    },
  });

  const state = stateQuery.data;
  const packages = recommendQuery.data?.packages ?? [];
  const recommendedPackage = packages.find((pkg) => pkg.recommended);
  const samples = samplesQuery.data?.samples ?? [];
  const latestSample = samples[0];
  const metrics = recommendQuery.data?.metrics;

  // Model library data from packages
  const modelLibrary = packages.map((pkg) => ({
    name: pkg.title,
    status: pkg.recommended ? "推荐" : pkg.package_id === state?.active_package_id ? "已部署" : "空闲",
    version: pkg.package_id.slice(0, 12),
    sharpe: metrics ? formatScoreValue(metrics.win_rate * 100, 1) : "--",
    active: pkg.recommended || pkg.package_id === state?.active_package_id,
  }));

  // Checklist derived from state
  const isCurrentRecommended = state?.active_package_id === recommendedPackage?.package_id;
  const checklist = [
    ["推荐方案与当前一致", isCurrentRecommended ? "当前已是推荐配置" : "存在待应用更新", isCurrentRecommended],
    ["学习样本数量", `已导入 ${samples.length} 个样本`, samples.length > 0],
    ["指标分析完成", metrics ? "基于最新样本计算" : "等待样本数据", !!metrics],
    ["参数已确认", "需手动确认部署", false],
  ] as const;

  // Version diff between current and recommended
  const diffRows = (() => {
    if (!state || !recommendedPackage || isCurrentRecommended) {
      return [];
    }

    const currentScore = state.config.score;
    const recommendedScore = recommendedPackage.config.score;
    const currentRisk = state.config.risk;
    const recommendedRisk = recommendedPackage.config.risk;

    const rows: [string, string, string][] = [];

    if (currentScore.carry_weight !== recommendedScore.carry_weight) {
      rows.push(["carry_weight", formatScoreValue(currentScore.carry_weight), formatScoreValue(recommendedScore.carry_weight)]);
    }
    if (currentScore.basis_penalty_weight !== recommendedScore.basis_penalty_weight) {
      rows.push([
        "basis_penalty_weight",
        formatScoreValue(currentScore.basis_penalty_weight),
        formatScoreValue(recommendedScore.basis_penalty_weight),
      ]);
    }
    if (currentRisk.min_allow_score !== recommendedRisk.min_allow_score) {
      rows.push([
        "min_allow_score",
        formatScoreValue(currentRisk.min_allow_score),
        formatScoreValue(recommendedRisk.min_allow_score),
      ]);
    }

    return rows.length > 0
      ? rows
      : [["--", "当前已为推荐配置", "当前已为推荐配置"]];
  })();

  // SHAP-like analysis from reason_codes
  const shapItems = recommendedPackage?.reason_codes.map((code, index) => {
    const magnitude = metrics
      ? Object.values(metrics).filter((v) => typeof v === "number")[0] ?? 0.3
      : 0.3;
    const adjustedMagnitude = Math.max(0.1, magnitude - index * 0.05);
    const value = adjustedMagnitude > 0 ? `+${adjustedMagnitude.toFixed(2)}` : adjustedMagnitude.toFixed(2);
    const width = `${Math.round(adjustedMagnitude * 100)}%`;

    return [code, value, width] as const;
  }) ?? [];

  // Scoring heatbar heights from recent samples
  const heatbarHeights = samples
    .slice(0, 6)
    .map((sample) => normalizeScoreToPercentage(sample.score, 50, 100));

  const handleApply = () => {
    if (recommendedPackage) {
      applyMutation.mutate({ package: recommendedPackage, confirmed: true });
    }
  };

  const handleExtractSamples = () => {
    extractSamplesMutation.mutate({ mode: "append" });
  };

  return (
    <TerminalLayout activePath="/models">
      <section className="proto-page">
        <header className="proto-header">
          <div>
            <h2 className="proto-page__title">模型工作台</h2>
            <p className="proto-page__subtitle">集成化的量化策略研发与部署环境</p>
          </div>
          <div className="proto-header__actions">
            <button
              className="proto-button proto-button--ghost"
              type="button"
              onClick={handleExtractSamples}
              disabled={extractSamplesMutation.isPending}
            >
              {extractSamplesMutation.isPending ? "提取中..." : "导出分析报告"}
            </button>
            <button
              className="proto-button proto-button--primary"
              type="button"
              onClick={handleApply}
              disabled={applyMutation.isPending || !recommendedPackage || isCurrentRecommended}
            >
              {applyMutation.isPending ? "部署中..." : "一键部署实盘"}
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
                {stateQuery.isPending ? (
                  <p className="panel-state">加载模型库中...</p>
                ) : stateQuery.isError ? (
                  <p className="panel-alert">模型库数据不可用</p>
                ) : modelLibrary.length === 0 ? (
                  <p className="panel-state">暂无可用模型</p>
                ) : (
                  modelLibrary.map((model) => (
                    <div
                      className={`proto-library-item${model.active ? " proto-library-item--active" : ""}`}
                      key={model.name}
                    >
                      <div className="proto-library-item__top">
                        <strong>{model.name}</strong>
                        <span className={`proto-chip${model.active ? " proto-chip--active" : ""}`}>
                          {model.status}
                        </span>
                      </div>
                      <span className="proto-meta">版本: {model.version}</span>
                      <span className="proto-meta">胜率: {model.sharpe}%</span>
                    </div>
                  ))
                )}
              </div>
            </article>

            <article className="proto-panel">
              <p className="proto-panel__eyebrow">Scoring</p>
              <h3>实时打分预览 (Scoring)</h3>
              <div className="proto-kv-list">
                {samplesQuery.isPending ? (
                  <p className="panel-state">加载样本数据中...</p>
                ) : samplesQuery.isError ? (
                  <p className="panel-alert">样本数据不可用</p>
                ) : !latestSample ? (
                  <p className="panel-state">暂无样本数据</p>
                ) : (
                  <div>
                    <span>{latestSample.symbol} 最新评分</span>
                    <strong>{formatScoreValue(latestSample.score)}</strong>
                  </div>
                )}
              </div>
              <div className="proto-heatbars proto-heatbars--short">
                {samplesQuery.isPending || samplesQuery.isError || heatbarHeights.length === 0
                  ? [40, 60, 50, 70, 55, 65].map((height, index) => (
                      <div className="proto-heatbars__bar" key={`placeholder-${index}`} style={{ height: `${height}%` }} />
                    ))
                  : heatbarHeights.map((height, index) => (
                      <div className="proto-heatbars__bar" key={`${height}-${index}`} style={{ height: `${height}%` }} />
                    ))}
              </div>
              <div className="proto-score-card">
                <span>多头置信度</span>
                <strong>
                  {metrics ? `${formatScoreValue(metrics.win_rate * 100, 1)}%` : "--"}
                </strong>
              </div>
            </article>
          </div>

          <div className="proto-wide-stack">
            <article className="proto-panel">
              <div className="proto-panel__header">
                <div>
                  <p className="proto-panel__eyebrow">Model Config</p>
                  <h3>
                    {state?.active_package_title ?? recommendedPackage?.title ?? "参数配置"}
                  </h3>
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
                    {stateQuery.isPending || recommendQuery.isPending ? (
                      <p className="panel-state">加载配置中...</p>
                    ) : stateQuery.isError || recommendQuery.isError ? (
                      <p className="panel-alert">配置数据不可用</p>
                    ) : !state?.config.score ? (
                      <p className="panel-state">暂无配置数据</p>
                    ) : (
                      <>
                        <div>
                          <span>carry_weight (carry 权重)</span>
                          <strong>
                            {state.config.score.carry_weight > 0 ? "启用" : "停用"}
                          </strong>
                        </div>
                        <div>
                          <span>annualized_weight (年化权重)</span>
                          <strong>
                            {state.config.score.annualized_weight > 0 ? "启用" : "停用"}
                          </strong>
                        </div>
                        <div>
                          <span>cost_penalty_weight (成本惩罚)</span>
                          <strong>
                            {state.config.score.cost_penalty_weight > 0 ? "启用" : "停用"}
                          </strong>
                        </div>
                        <div>
                          <span>basis_penalty_weight (基差惩罚)</span>
                          <strong>
                            {state.config.score.basis_penalty_weight > 0 ? "启用" : "停用"}
                          </strong>
                        </div>
                      </>
                    )}
                  </div>
                </div>
                <div className="proto-stack-card">
                  <p className="proto-panel__eyebrow">超参数 (Hyperparameters)</p>
                  {stateQuery.isPending || recommendQuery.isPending ? (
                    <p className="panel-state">加载超参数中...</p>
                  ) : stateQuery.isError || recommendQuery.isError ? (
                    <p className="panel-alert">超参数不可用</p>
                  ) : !state?.config.score ? (
                    <p className="panel-state">暂无超参数数据</p>
                  ) : (
                    <>
                      <div className="proto-threshold">
                        <div className="proto-threshold__top">
                          <span>carry_weight (carry 权重)</span>
                          <strong>{formatScoreValue(state.config.score.carry_weight, 3)}</strong>
                        </div>
                        <div className="proto-progress">
                          <div
                            className="proto-progress__fill"
                            style={{ width: `${formatWeightAsPercentage(state.config.score.carry_weight)}%` }}
                          />
                        </div>
                      </div>
                      <div className="proto-threshold">
                        <div className="proto-threshold__top">
                          <span>basis_penalty_weight (基差惩罚权重)</span>
                          <strong>{formatScoreValue(state.config.score.basis_penalty_weight, 3)}</strong>
                        </div>
                        <div className="proto-progress">
                          <div
                            className="proto-progress__fill"
                            style={{ width: `${formatWeightAsPercentage(state.config.score.basis_penalty_weight)}%` }}
                          />
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </article>

            <article className="proto-panel">
              <div className="proto-panel__header">
                <div>
                  <p className="proto-panel__eyebrow">Interpretability</p>
                  <h3>可解释性分析 (SHAP Analysis)</h3>
                </div>
                <span className="proto-meta">
                  基于最近 {metrics?.trade_count ?? 0} 个采样点
                </span>
              </div>
              {recommendQuery.isPending ? (
                <p className="panel-state">生成分析中...</p>
              ) : recommendQuery.isError ? (
                <p className="panel-alert">分析数据不可用</p>
              ) : shapItems.length === 0 ? (
                <p className="panel-state">暂无分析数据</p>
              ) : (
                <>
                  <div className="proto-shap-list">
                    {shapItems.map(([name, value, width]) => (
                      <div className="proto-shap-item" key={name}>
                        <div className="proto-threshold__top">
                          <span>{name}</span>
                          <strong className={value.startsWith("-") ? "proto-text--danger" : "proto-text--accent"}>
                            {value}
                          </strong>
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
                    <strong>分析结论：</strong>
                    {metrics
                      ? `当前模型基于 ${metrics.trade_count} 个交易样本训练，平均胜率 ${formatScoreValue(metrics.win_rate * 100, 1)}%，${metrics.avg_projection_shortfall_bps > 0 ? `预测偏差平均 ${formatScoreValue(metrics.avg_projection_shortfall_bps)} bps` : "预测偏差在正常范围"}。${metrics.slow_payback_rate > 0.1 ? `慢回撤率 ${formatScoreValue(metrics.slow_payback_rate * 100, 1)}% 偏高，建议关注。` : "回撤表现良好。"}`
                      : "等待指标分析完成。"}
                  </p>
                </>
              )}
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
                  <span>当前配置</span>
                  <span>推荐配置</span>
                </div>
                {stateQuery.isPending || recommendQuery.isPending ? (
                  <p className="panel-state">对比中...</p>
                ) : stateQuery.isError || recommendQuery.isError ? (
                  <p className="panel-alert">对比数据不可用</p>
                ) : diffRows.length === 0 ? (
                  <div className="proto-table-row proto-table-row--diff">
                    <span>--</span>
                    <span>--</span>
                    <strong className="proto-text--accent">--</strong>
                  </div>
                ) : (
                  diffRows.map((row) => (
                    <div className="proto-table-row proto-table-row--diff" key={row[0]}>
                      <span>{row[0]}</span>
                      <span>{row[1]}</span>
                      <strong className="proto-text--accent">{row[2]}</strong>
                    </div>
                  ))
                )}
              </div>
            </article>
          </div>
        </section>
      </section>
    </TerminalLayout>
  );
}
