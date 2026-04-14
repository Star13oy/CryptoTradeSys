import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { apiClient } from "../../shared/api/client";
import { TerminalLayout } from "../../shared/ui/terminal-layout";
import type { ApiKeySummary } from "../../shared/contracts/console";

export function SettingsPage() {
  const [newLabel, setNewLabel] = useState("");
  const [newApiKey, setNewApiKey] = useState("");
  const [newApiSecret, setNewApiSecret] = useState("");

  const keysQuery = useQuery<ApiKeySummary[]>({
    queryKey: ["credentials"],
    queryFn: () => apiClient.listCredentials<ApiKeySummary[]>(),
  });

  const addMutation = useMutation({
    mutationFn: () =>
      apiClient.addCredential<ApiKeySummary>({
        label: newLabel,
        exchange: "binance",
        api_key: newApiKey,
        api_secret: newApiSecret,
      }),
    onSuccess: () => {
      keysQuery.refetch();
      setNewLabel("");
      setNewApiKey("");
      setNewApiSecret("");
    },
  });

  const activateMutation = useMutation({
    mutationFn: (keyId: string) => apiClient.activateCredential<ApiKeySummary>(keyId),
    onSuccess: () => keysQuery.refetch(),
  });

  const deleteMutation = useMutation({
    mutationFn: (keyId: string) => apiClient.deleteCredential<ApiKeySummary>(keyId),
    onSuccess: () => keysQuery.refetch(),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newLabel || !newApiKey || !newApiSecret) return;
    addMutation.mutate();
  };

  return (
    <TerminalLayout activePath="/settings">
      <section className="proto-page">
        <header className="proto-header">
          <div>
            <h2 className="proto-page__title">系统设置</h2>
            <p className="proto-page__subtitle">API 密钥管理与系统配置</p>
          </div>
        </header>

        <div className="proto-panel">
          <div className="proto-panel__header">
            <div>
              <p className="proto-panel__eyebrow">API 密钥</p>
              <h3>已保存的凭证</h3>
            </div>
          </div>

          {keysQuery.isPending ? (
            <p className="proto-meta">加载中...</p>
          ) : keysQuery.isError ? (
            <p className="proto-text--danger">加载失败</p>
          ) : keysQuery.data && keysQuery.data.length > 0 ? (
            <div className="proto-form-stack">
              {keysQuery.data.map((key) => (
                <div key={key.id} className="proto-stack-card">
                  <div className="proto-panel__header">
                    <div>
                      <strong>{key.label}</strong>
                      <span className="proto-meta">{key.exchange}</span>
                    </div>
                    <div className="proto-chip-row">
                      {key.is_active ? (
                        <span className="proto-chip proto-chip--active">活跃</span>
                      ) : (
                        <span className="proto-chip">未激活</span>
                      )}
                    </div>
                  </div>
                  <div className="proto-kv-list">
                    <div>
                      <span>API Key</span>
                      <strong>{key.api_key_preview}</strong>
                    </div>
                    <div>
                      <span>创建时间</span>
                      <strong>{new Date(key.created_at).toLocaleString("zh-CN")}</strong>
                    </div>
                  </div>
                  <div className="proto-action-grid" style={{ marginTop: 12 }}>
                    {!key.is_active && (
                      <button
                        className="proto-button proto-button--primary"
                        type="button"
                        disabled={activateMutation.isPending}
                        onClick={() => activateMutation.mutate(key.id)}
                      >
                        {activateMutation.isPending ? "激活中..." : "激活"}
                      </button>
                    )}
                    <button
                      className="proto-button proto-button--danger"
                      type="button"
                      disabled={deleteMutation.isPending}
                      onClick={() => {
                        if (window.confirm(`确认删除 ${key.label}？`)) {
                          deleteMutation.mutate(key.id);
                        }
                      }}
                    >
                      删除
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="proto-meta">暂无 API 密钥</p>
          )}
        </div>

        <div className="proto-panel">
          <div className="proto-panel__header">
            <div>
              <p className="proto-panel__eyebrow">添加新凭证</p>
              <h3>添加 API 密钥</h3>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="proto-form-stack">
            <div className="proto-field">
              <span>标签</span>
              <input
                type="text"
                placeholder="Binance 主账户"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                required
              />
            </div>

            <div className="proto-field">
              <span>API Key</span>
              <input
                type="text"
                placeholder="输入 API Key"
                value={newApiKey}
                onChange={(e) => setNewApiKey(e.target.value)}
                required
              />
            </div>

            <div className="proto-field">
              <span>API Secret</span>
              <input
                type="password"
                placeholder="输入 API Secret"
                value={newApiSecret}
                onChange={(e) => setNewApiSecret(e.target.value)}
                required
              />
            </div>

            <button
              className="proto-button proto-button--primary"
              type="submit"
              disabled={addMutation.isPending || !newLabel || !newApiKey || !newApiSecret}
            >
              {addMutation.isPending ? "添加中..." : "添加密钥"}
            </button>
          </form>
        </div>
      </section>
    </TerminalLayout>
  );
}
