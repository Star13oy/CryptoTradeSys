import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "../../shared/api/client";
import type { TokenResponse } from "../../shared/contracts/console";

export function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const loginMutation = useMutation({
    mutationFn: () => apiClient.login<TokenResponse>({ username, password }),
    onSuccess: (data) => {
      localStorage.setItem("auth_token", data.access_token);
      localStorage.setItem("auth_user", JSON.stringify(data));
      window.location.href = "/";
    },
    onError: () => {
      setError("用户名或密码错误");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    loginMutation.mutate();
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh", background: "#0a0a0f", color: "#e0e0e0", fontFamily: "monospace" }}>
      <form onSubmit={handleSubmit} style={{ width: 360, padding: 32, border: "1px solid #2a2a3a", borderRadius: 8, background: "#111118" }}>
        <h2 style={{ textAlign: "center", marginBottom: 8, color: "#6bd8cb" }}>Funding Command</h2>
        <p style={{ textAlign: "center", marginBottom: 24, color: "#888", fontSize: 14 }}>虚拟币资金费率套利系统</p>
        {error && <div style={{ color: "#ff4444", textAlign: "center", marginBottom: 16, fontSize: 14 }}>{error}</div>}
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: "block", marginBottom: 6, fontSize: 13, color: "#aaa" }}>用户名</label>
          <input
            type="text" value={username} onChange={(e) => setUsername(e.target.value)}
            style={{ width: "100%", padding: "10px 12px", background: "#1a1a24", border: "1px solid #333", borderRadius: 4, color: "#e0e0e0", fontSize: 14, boxSizing: "border-box" }}
            autoFocus
          />
        </div>
        <div style={{ marginBottom: 24 }}>
          <label style={{ display: "block", marginBottom: 6, fontSize: 13, color: "#aaa" }}>密码</label>
          <input
            type="password" value={password} onChange={(e) => setPassword(e.target.value)}
            style={{ width: "100%", padding: "10px 12px", background: "#1a1a24", border: "1px solid #333", borderRadius: 4, color: "#e0e0e0", fontSize: 14, boxSizing: "border-box" }}
          />
        </div>
        <button
          type="submit" disabled={loginMutation.isPending || !username || !password}
          style={{ width: "100%", padding: "10px", background: loginMutation.isPending ? "#444" : "#6bd8cb", color: loginMutation.isPending ? "#888" : "#0a0a0f", border: "none", borderRadius: 4, fontSize: 14, fontWeight: "bold", cursor: loginMutation.isPending ? "not-allowed" : "pointer" }}
        >
          {loginMutation.isPending ? "登录中..." : "登录"}
        </button>
        <p style={{ textAlign: "center", marginTop: 16, fontSize: 12, color: "#666" }}>默认账户: admin / admin</p>
      </form>
    </div>
  );
}
