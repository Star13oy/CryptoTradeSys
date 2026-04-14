import type { ReactNode } from "react";

type TerminalLayoutProps = {
  activePath: "/" | "/scan" | "/positions" | "/risk" | "/backtest" | "/models" | "/audit" | "/settings" | "/trade";
  children: ReactNode;
  footerContent?: ReactNode;
};

type NavigationItem = {
  label: string;
  href?: TerminalLayoutProps["activePath"];
  icon: string;
};

const navigationItems: NavigationItem[] = [
  { label: "总览面板", href: "/", icon: "DB" },
  { label: "机会扫描", href: "/scan", icon: "SC" },
  { label: "监控中心", href: "/positions", icon: "MN" },
  { label: "风险控制", href: "/risk", icon: "RK" },
  { label: "交易下单", href: "/trade", icon: "TD" },
  { label: "回测引擎", href: "/backtest", icon: "BT" },
  { label: "分析工作台", href: "/models", icon: "ML" },
  { label: "审计日志", href: "/audit", icon: "LG" },
];

function NavigationEntry({
  activePath,
  item,
}: {
  activePath: TerminalLayoutProps["activePath"];
  item: NavigationItem;
}) {
  const isActive = item.href === activePath;
  const className = `terminal-nav__item${isActive ? " terminal-nav__item--active" : ""}${
    item.href ? "" : " terminal-nav__item--disabled"
  }`;

  const content = (
    <>
      <span className="terminal-nav__icon" aria-hidden="true">
        {item.icon}
      </span>
      <span>{item.label}</span>
    </>
  );

  if (item.href) {
    return (
      <a className={className} href={item.href}>
        {content}
      </a>
    );
  }

  return (
    <span className={className} aria-disabled="true">
      {content}
    </span>
  );
}

export function TerminalLayout({ activePath, children, footerContent }: TerminalLayoutProps) {
  const timeLabel = new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date());

  const authUserJson = localStorage.getItem("auth_user");
  const authUser = authUserJson ? JSON.parse(authUserJson) as { username: string } : null;
  const username = authUser?.username || "QUANT_ADMIN";
  const brandNote = authUser ? `${username} | 高级交易员终端` : "高级交易员终端";

  return (
    <div className="terminal-app">
      <aside className="terminal-sidebar">
        <div className="terminal-sidebar__brand">
          <span className="terminal-sidebar__brand-mark">{username}</span>
          <p className="terminal-sidebar__brand-note">{brandNote}</p>
        </div>

        <nav className="terminal-nav" aria-label="主导航">
          {navigationItems.map((item) => (
            <NavigationEntry activePath={activePath} item={item} key={item.label} />
          ))}
        </nav>

        <div className="terminal-sidebar__footer">
          <button className="terminal-sidebar__action" type="button">
            新策略
          </button>

          <div className="terminal-sidebar__aux">
            <a href="/settings">系统设置</a>
            <a
              href="/login"
              onClick={(e) => {
                e.preventDefault();
                localStorage.removeItem("auth_token");
                localStorage.removeItem("auth_user");
                window.location.href = "/login";
              }}
            >
              退出登录
            </a>
          </div>
        </div>
      </aside>

      <div className="terminal-main">
        <header className="terminal-topbar">
          <div>
            <p className="terminal-topbar__eyebrow">AUTONOMOUS FUNDING ARBITRAGE CONSOLE</p>
            <h1>OBSIDIAN LEDGER</h1>
          </div>

          <div className="terminal-topbar__status-row">
            <span className="terminal-pill terminal-pill--active">实盘模式</span>
            <span className="terminal-pill">连接成功</span>
            <span className="terminal-pill">{timeLabel} UTC+8</span>
          </div>
        </header>

        <div className="terminal-content">{children}</div>

        <footer className="terminal-footer">
          {footerContent ?? (
            <>
              <span>© 2026 OBSIDIAN LEDGER LABS</span>
              <span>Autonomous Funding Desk / Phase 1</span>
            </>
          )}
        </footer>
      </div>
    </div>
  );
}
