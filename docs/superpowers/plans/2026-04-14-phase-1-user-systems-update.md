# 2026-04-14 Phase 1 User Systems Update

## Workspace

- Repo: `https://github.com/Star13oy/CryptoTradeSys.git`
- Branch: `codex/phase-1`
- Commit: `7e43613`
- Status: pushed to remote

## Executive Summary

本次更新完成了 **用户系统 + API 密钥配置 + 手动下单** 三大核心功能，使系统从"技术原型"升级为"可实际使用的完整交易系统"。

核心变化：
1. **用户认证系统**：JWT 认证，默认管理员账户，路由守卫
2. **API 密钥管理**：加密存储，多密钥支持，前端配置界面
3. **手动下单面板**：币对选择，预览功能，风险决策
4. **一键开仓**：扫描页直接下单功能

## What's New

### 1. 用户认证系统 (User Authentication)

**后端实现：**
- `backend/app/auth/` 模块（4 个文件）
  - `schemas.py`: LoginRequest, RegisterRequest, TokenResponse, UserResponse
  - `service.py`: AuthService - JWT 生成/验证，bcrypt 密码哈希
  - `middleware.py`: get_current_user - FastAPI 依赖项
  - `router.py`: `/api/v1/auth/*` 路由

**认证方案：**
- JWT (HS256)，24h 过期
- bcrypt 密码哈希存储
- JSON 文件存储（`backend/runtime/users.json`）
- 默认管理员账户：首次启动自动创建 `admin/admin`

**API 端点：**
- `POST /api/v1/auth/register` - 注册新用户
- `POST /api/v1/auth/login` - 登录获取 JWT
- `GET /api/v1/auth/me` - 获取当前用户信息
- `PUT /api/v1/auth/password` - 修改密码

**前端实现：**
- `frontend/src/pages/login/page.tsx` - 终端风格登录页
- 路由守卫：未登录自动重定向到 `/login`
- Auth token 存储在 localStorage

### 2. API 密钥管理 (API Key Management)

**后端实现：**
- `backend/app/credentials/` 模块（4 个文件）
  - `schemas.py`: ApiKeySet, ApiKeySummary
  - `service.py`: CredentialsService - AES-256 加密存储
  - `router.py`: `/api/v1/credentials/*` 路由

**安全特性：**
- API secret 使用 AES-256 加密存储
- 加密密钥来自环境变量 `FUNDING_ARB_ENCRYPTION_KEY` 或首次启动自动生成
- 前端只显示前 4 位 + `****`
- 支持多用户各自的 API 密钥

**API 端点：**
- `GET /api/v1/credentials` - 列出当前用户的 API 密钥（脱敏）
- `POST /api/v1/credentials` - 添加 API 密钥
- `DELETE /api/v1/credentials/{id}` - 删除 API 密钥
- `POST /api/v1/credentials/{id}/activate` - 设为当前活跃密钥
- `GET /api/v1/credentials/active` - 获取当前活跃密钥状态

**前端实现：**
- `frontend/src/pages/settings/page.tsx` - 系统设置页
  - API 密钥管理区域
  - 添加/删除/激活按钮
  - 系统状态显示（当前模式、存储后端、worker 启用状态）

### 3. 手动下单面板 (Manual Trading)

**后端实现：**
- `backend/app/trading/` 模块（4 个文件）
  - `schemas.py`: ManualOrderRequest, OrderPreview, OrderResult, SymbolInfo
  - `service.py`: TradingService - 下单预览和执行
  - `router.py`: `/api/v1/trading/*` 路由

**下单流程：**
1. 选择币对（从市场数据获取）
2. 选择方向（做多 = 买现货+空永续，做空 = 卖现货+多永续）
3. 输入名义金额
4. **预览**：显示 bid/ask、预估费用、预估净边缘、风险决策
5. **确认下单**：调用 ExecutionOrchestrator 执行

**API 端点：**
- `GET /api/v1/trading/symbols` - 获取可交易标的列表
- `POST /api/v1/trading/preview` - 下单预览（不执行）
- `POST /api/v1/trading/execute` - 确认下单

**前端实现：**
- `frontend/src/pages/trading/page.tsx` - 交易面板页
  - 左侧：下单表单（币对选择器、方向切换、金额输入、模式切换）
  - 右侧：当前活跃订单列表 + 快速平仓按钮
  - 底部：最近成交记录

### 4. 扫描页一键开仓 (One-Click Trading)

**前端修改：**
- `frontend/src/pages/opportunity-scan/page.tsx`
  - 在每个机会行添加"开仓"按钮
  - 对 `risk_tag != "blocked"` 的机会显示按钮
  - 点击后弹出确认弹窗（显示币对、方向、金额、预估费率）
  - 确认后调用 `POST /api/v1/trading/execute`
  - 成功后显示通知 + refetch 数据

### 5. 其他新增功能

**Safety 安全控制：**
- `backend/app/safety/` 模块
- 全局冻结/解冻
- 停止/恢复新开仓
- 设置 reduce-only 模式
- 暂停/恢复特定交易
- 紧急平仓

**Scheduler 策略调度：**
- `backend/app/scheduler/` 模块
- 基于分数和风险策略自动开仓/平仓
- 可配置最大持仓数量、最大总名义金额

**Monitor 持仓监控：**
- `backend/app/monitor/` 模块
- 监控资金费率变化
- 超阈值自动平仓
- 可配置最大持有期数

**Account 账户查询：**
- `backend/app/account/` 模块
- 查询账户余额
- 查询持仓信息
- 支持 symbol 过滤

## Verification Snapshot

### Backend Tests

```
132 passed, 6 skipped
```

覆盖范围：
- 所有新增模块（auth、credentials、trading、safety、scheduler、monitor、account）
- 原有功能回归测试
- JWT 认证流程
- API 密钥加密/解密
- 下单预览和执行

### Frontend Tests

```
29 passed
```

覆盖范围：
- 登录流程测试
- 设置页 API 密钥 CRUD 测试
- 交易面板下单流程测试
- 扫描页一键开仓测试
- 路由守卫测试

### Build

```
✓ vite build passed in 4.37s
```

## Project Structure Updates

### Backend Modules

新增模块：
- `backend/app/auth/` - 用户认证与授权（JWT）
- `backend/app/credentials/` - API 密钥加密存储管理
- `backend/app/trading/` - 手动下单与交易预览
- `backend/app/safety/` - 安全控制（冻结、停止开仓等）
- `backend/app/scheduler/` - 策略调度 worker
- `backend/app/monitor/` - 持仓监控 worker
- `backend/app/account/` - 账户余额与持仓查询

### Frontend Pages

新增页面：
- `/login` - 登录页
- `/settings` - 系统设置（API 密钥管理）
- `/trade` - 交易下单（手动下单面板）

## Dependencies

### Backend Added

```
PyJWT>=2.8,<3
bcrypt>=4.0,<5
```

## Quick Start

### 1. 环境准备

```powershell
# 后端
cd backend
uv sync
```

### 2. 启动后端

```powershell
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8888
```

首次启动会自动创建默认管理员账户：
- 用户名：`admin`
- 密码：`admin`

### 3. 启动前端

```powershell
cd frontend
npm install
npm run dev
```

前端默认代理到 `http://127.0.0.1:8888`（已配置）

### 4. 访问系统

- 登录页：http://localhost:5173/login
- 使用 `admin/admin` 登录
- 在"系统设置"页配置 Binance API 密钥
- 在"交易下单"页进行手动交易
- 在"机会扫描"页使用一键开仓

## Current Limitations

1. **单用户系统**：当前不支持多用户权限管理
2. **API 密钥加密**：使用 AES-256，但密钥管理可进一步加强
3. **手动下单**：暂不支持复杂的订单类型（限价、止损等）
4. **一键开仓**：只使用默认参数，不支持自定义

## Recommended Next Steps

1. **完善用户系统**
   - 添加用户角色管理（admin、trader、viewer）
   - 添加用户活动日志
   - 支持密码重置功能

2. **增强交易功能**
   - 支持限价单
   - 支持止损/止盈
   - 支持批量下单

3. **改进安全控制**
   - 添加 IP 白名单
   - 添加 2FA 双因素认证
   - 增强 API 密钥管理（过期时间、权限控制）

4. **优化用户体验**
   - 添加实时行情推送
   - 添加交易历史图表
   - 添加收益分析报表

## Git Trailers

```
Commit: 7e43613
Author: Claude Opus 4.6 (1M context)
Date: 2026-04-14

Confidence: high
Scope-risk: moderate
```

## Related Documentation

- [主 README](../README.md)
- [应用架构](../architecture/2026-04-05-application-architecture.md)
- [阶段进度](2026-04-05-phase-1-progress-update.md)
- [需求设计](../specs/2026-04-03-crypto-funding-arbitrage-design.md)
