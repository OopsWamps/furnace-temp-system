# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

退火炉全流程温度预测与报警系统 — 前端 (Vue 3) + 后端 (FastAPI)，使用 Bi-LSTM 机器学习模型对升温/保温/降温三阶段进行未来 10 分钟温度预测，并提供实时监控与过热报警。

## 目录结构

```
furnace_backend/furnace_backend/    # 后端 Python 项目
furnace_frontend/furnace_frontend/  # 前端 Vue/TS 项目 (工作目录)
```

## 后端开发命令

```bash
cd furnace_backend/furnace_backend

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器 (默认 0.0.0.0:8080, reload 开启)
python main.py

# Windows 打包
build.bat

# Ubuntu 打包
./build-ubuntu.sh
```

**依赖**: Python 3.10+, PostgreSQL (数据库 `furnace`)，配置文件 `config/config.yaml` 可覆盖默认值。

## 前端开发命令

```bash
cd furnace_frontend/furnace_frontend

# 开发服务器 (localhost:3000, API 代理到 localhost:8080)
npm run dev

# 生产构建 (先 vue-tsc 类型检查，再 vite build)
npm run build

# 预览构建产物
npm run preview
```

## 后端架构

```
furnace_backend/
├── main.py                  # FastAPI 入口，lifespan 管理
├── app/
│   ├── api/                 # 路由层
│   │   ├── __init__.py      # APIRouter(prefix="/api"), 聚合 health + furnace
│   │   ├── health.py        # GET /api/health
│   │   └── furnace.py       # /api/furnace/* (current, history, prediction, phases, alarms)
│   ├── core/
│   │   ├── config.py        # Pydantic Settings → YAML 加载，单例 settings
│   │   ├── database.py      # SQLAlchemy async engine + session (asyncpg)
│   │   ├── logging.py       # Loguru 初始化
│   │   └── response.py      # success_response / error_response 统一格式
│   ├── models/              # SQLAlchemy ORM (当前为空壳)
│   ├── schemas/             # Pydantic schemas (当前为空壳)
│   └── services/
│       └── furnace_service.py  # 核心业务：模型加载、数据模拟、预测、报警、实时库写入
├── config/config.yaml        # 运行时配置
├── *_bilstm.pth              # 3 个 PyTorch Bi-LSTM 模型 (heating/holding/cooling)
├── *_feat_scaler.pkl         # 特征标准化器
├── *_target_scaler.pkl       # 目标反标准化器
├── simulation.py             # 闭环物理模型仿真器
├── cooling.py / heating.py / holding.py  # 各阶段训练/测试脚本
└── furnace_backend.spec      # PyInstaller spec
```

- **FurnaceService** (`furnace_service.py`): 单例服务，启动时加载 3 个 Bi-LSTM 模型，后台线程每 4 秒更新物理仿真数据、用当前阶段对应模型预测未来 10 分钟温度、检测报警（多级阈值含控制建议），将实时数据写入外部 RTDB。
- **工艺周期**: heating(0-200分钟) → holding(200-600) → cooling(600-1200) → unload(1200-1440)。unload 阶段不做预测。
- API 响应格式 `{ code: 0, data: ..., message: "..." }`；错误用 `error_response(code=-1, message=...)`。

## 前端架构

```
src/
├── main.ts                  # 入口：createApp → Pinia → router → ElementPlus → mount
├── App.vue                  # 根组件，仅 <router-view>
├── api/
│   ├── request.ts           # Axios 封装类：baseURL=/api, 拦截器处理 code===0
│   └── furnace.ts           # API 函数 + 接口类型 (SensorData, PredictionData, AlarmInfo 等)
├── router/index.ts          # 3 个路由: /dashboard, /sensors, /alarms (Layout 子路由)
├── stores/locale.ts         # Pinia Store：4 语言切换 (zh-hans/zh-hant/ja/en), localStorage 持久化
├── utils/i18n.ts            # 400+ 词条词典
├── components/Layout/       # 主布局组件
└── views/
    ├── Dashboard/           # 监控面板（主页）
    ├── Sensors/             # 9 宫格传感器卡片 + 迷你图表
    ├── Alarms/              # 报警记录（统计卡片 + 筛选 + 确认操作）
    ├── Alarm/               # 静态演示页（未接入路由）
    ├── History/             # 静态演示页（未接入路由）
    └── Temperature/         # 静态演示页（未接入路由）
```

- **路由模式**: createWebHistory（Hash-less）
- **Element Plus**: 全局注册所有图标组件
- **Vite 代理**: `/api` → `http://localhost:8080`
- **路径别名**: `@` → `src/`（tsconfig paths + vite resolve alias）

## 技术栈

| 层 | 后端 | 前端 |
|---|---|---|
| 框架 | FastAPI + Uvicorn | Vue 3 (Composition API) |
| 语言 | Python 3.10+ | TypeScript (strict) |
| 数据库 | PostgreSQL + SQLAlchemy async | — |
| ML | PyTorch + scikit-learn | — |
| UI | — | Element Plus + ECharts |
| 状态管理 | — | Pinia |
| 打包 | PyInstaller | Vite |

## 注意事项

- 前端 `build` 脚本已在 `package.json` 中定义为 `vue-tsc && vite build`，类型检查失败会导致构建不通过。
- 后端数据库使用 asyncpg 驱动，需要 PostgreSQL 运行中。`config/config.yaml` 中的数据库连接字符串含密码，不要提交到公开仓库。
- 模型文件 (`.pth`, `.pkl`) 体积较大 (334KB each)，打包和部署时需确保文件与可执行文件同目录。
- `views/Alarm/`, `views/History/`, `views/Temperature/` 三个视图为静态演示页，路由中不可达，不是 bug。
