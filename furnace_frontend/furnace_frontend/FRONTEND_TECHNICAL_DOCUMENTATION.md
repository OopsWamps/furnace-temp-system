# 退火炉全流程温度预测系统 — 前端技术文档

## 1. 项目概述

### 1.1 项目定位

本项目是**退火炉全流程温度预测系统**的前端单页应用（SPA）。系统面向工业退火炉的实时监控场景，提供传感器数据可视化、AI 温度预测、异常报警、历史数据查询等功能。

### 1.2 系统名称

| 属性 | 值 |
|---|---|
| 项目名称 | furnace_frontend |
| 中文名称 | 退火炉全流程温度预测系统 |
| 版本 | 1.0.0 |
| 语言 | 简体中文（默认）、繁體中文、日本語、English |
| 模块类型 | ES Module (`"type": "module"`) |

### 1.3 技术栈

| 层级 | 技术 | 版本 | 用途 |
|---|---|---|---|
| 框架 | Vue 3 | ^3.5.13 | Composition API + `<script setup>` |
| 语言 | TypeScript | ^5.7.2 | 全量类型约束 |
| 构建工具 | Vite | ^6.0.3 | 开发服务器 + 生产构建 |
| 路由 | vue-router | ^4.5.0 | Hash History SPA 路由 |
| 状态管理 | Pinia | ^2.3.0 | 全局状态（国际化语言偏好） |
| HTTP 客户端 | Axios | ^1.7.9 | 封装请求/响应拦截器 |
| UI 组件库 | Element Plus | ^2.9.1 | 布局、卡片、表格、标签等 |
| 图表库 | ECharts | ^5.6.0 | 温度曲线、传感器趋势折线图 |
| 图标库 | @element-plus/icons-vue | ^2.3.1 | 侧边栏、操作按钮图标 |
| 开发工具 | vue-tsc | ^2.2.2 | 模板类型检查 |

---

## 2. 项目目录结构

```
furnace_frontend/
├── index.html                          # SPA 入口 HTML
├── package.json                        # 依赖与脚本定义
├── tsconfig.json                       # TypeScript 编译配置
├── tsconfig.node.json                  # Vite/Node 端 TS 配置
├── vite.config.ts                      # Vite 构建配置
├── .gitignore
├── kangc.npm-cache/                    # npm 缓存目录
├── node_modules/                       # 安装依赖
├── public/
│   ├── vite.svg                        # Favicon
│   └── images/
│       └── furnace_model.png           # 退火炉设备示意图
├── dist/                               # 生产构建产物
└── src/
    ├── main.ts                         # 应用入口：挂载 Vue + 插件注册
    ├── App.vue                         # 根组件（仅含 <router-view>）
    ├── vite-env.d.ts                   # Vite 类型声明
    ├── api/
    │   ├── request.ts                  # Axios 封装（拦截器 + 统一错误处理）
    │   └── furnace.ts                  # 退火炉 API 接口定义 + 类型
    ├── assets/
    │   └── styles/
    │       └── main.css                # 全局样式重置
    ├── components/
    │   └── Layout/
    │       └── index.vue               # 主布局（侧边栏 + 顶栏 + 内容区）
    ├── router/
    │   └── index.ts                    # 路由配置（3 个页面路由）
    ├── stores/
    │   ├── index.ts                    # Pinia Store 聚合入口（预留）
    │   └── locale.ts                   # 国际化 Store（语言切换 + localStorage 持久化）
    ├── utils/
    │   ├── index.ts                    # 工具函数聚合入口（预留）
    │   └── i18n.ts                     # 国际化词典（4 语言 × 400+ 词条）
    └── views/
        ├── Dashboard/
        │   └── index.vue               # 监控面板（主页）
        ├── Sensors/
        │   └── index.vue               # 传感器视图（9 宫格卡片 + 迷你图表）
        ├── Alarms/
        │   └── index.vue               # 异常记录（统计卡片 + 筛选 + 确认操作）
        ├── Alarm/
        │   └── index.vue               # 告警管理页（静态演示页，未接入路由）
        ├── History/
        │   └── index.vue               # 历史数据页（演示页，未接入路由）
        └── Temperature/
            └── index.vue               # 温度监控页（演示页，未接入路由）
```

> **注意**：`Alarm/`、`History/`、`Temperature/` 三个视图为静态演示页面，当前未在 `router/index.ts` 中注册路由，无法通过导航访问。实际使用的路由页面为 `Dashboard/`、`Sensors/`、`Alarms/`。

---

## 3. 应用启动流程

```
index.html
  └── <script type="module" src="/src/main.ts">
        │
        ├── 1. createApp(App)                          # 创建 Vue 应用实例
        ├── 2. 注册所有 Element Plus 图标组件           # 全局可用，无需单独导入
        ├── 3. createPinia() → app.use(pinia)          # 注册 Pinia
        ├── 4. app.use(router)                         # 注册路由
        ├── 5. app.use(ElementPlus)                    # 注册 Element Plus
        ├── 6. import 'element-plus/dist/index.css'    # 加载 Element Plus 样式
        ├── 7. import './assets/styles/main.css'       # 加载全局样式
        └── 8. app.mount('#app')                       # 挂载到 DOM
```

### 3.1 全局注册的 Element Plus 图标

`main.ts:12-14` 通过 `Object.entries` 遍历 `@element-plus/icons-vue` 的导出，将所有图标以 `app.component(key, component)` 全局注册。此后任何 `.vue` 组件可直接使用图标组件名而无需导入。

---

## 4. 路由设计

### 4.1 路由表

| 路径 | 名称 | 组件 | 元信息 |
|---|---|---|---|
| `/` | — | Layout | 重定向到 `/dashboard` |
| `/dashboard` | Dashboard | `views/Dashboard/index.vue` (懒加载) | `{ title: '监控面板' }` |
| `/sensors` | Sensors | `views/Sensors/index.vue` (懒加载) | `{ title: '传感器视图' }` |
| `/alarms` | Alarms | `views/Alarms/index.vue` (懒加载) | `{ title: '异常记录' }` |

### 4.2 路由架构

- **路由模式**：`createWebHistory()` — HTML5 History 模式，URL 无 `#` 号
- **根路径 `/`** 加载 `Layout` 组件，通过 `<router-view>` 渲染子路由
- **重定向**：访问 `/` 自动跳转到 `/dashboard`
- **懒加载**：所有页面组件使用动态 `import()`，按需分割 chunk

### 4.3 导航菜单

侧边栏菜单使用 Element Plus 的 `<el-menu>` 组件，`router` 属性开启路由模式，点击菜单项自动导航：

| 菜单项 | 路由 | 图标 |
|---|---|---|
| 监控面板 | `/dashboard` | `<Odometer />` |
| 传感器视图 | `/sensors` | `<DataBoard />` |
| 异常记录 | `/alarms` | `<Bell />` |

---

## 5. 布局系统

### 5.1 整体结构

```
┌──────────────────────────────────────────────────┐
│ ┌──────────┐ ┌──────────────────────────────────┐ │
│ │          │ │  Header (60px)                   │ │
│ │  Logo    │ │  ┌────────┬──────────┬─────────┐ │ │
│ │          │ │  │折叠按钮 │  系统标题  │ 语言切换 │ │ │
│ │  Sidebar │ │  └────────┴──────────┴─────────┘ │ │
│ │  220px   │ ├──────────────────────────────────┤ │
│ │          │ │                                  │ │
│ │  导航菜单  │ │  Main Content                    │ │
│ │          │ │  (router-view)                   │ │
│ │          │ │                                  │ │
│ │          │ │                                  │ │
│ └──────────┘ └──────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### 5.2 侧边栏

- **宽度**：展开 220px / 折叠 64px
- **颜色**：深色主题，背景 `#001529`，文字 `#bfcbd9`，高亮 `#1890ff`
- **Logo 区域**：高度 60px，背景 `#002140`，展开时显示"退火炉系统"，折叠时显示"F"
- **折叠切换**：通过 Header 左侧的折叠/展开图标按钮触发，响应式切换 `isCollapse` 状态

### 5.3 顶栏 (Header)

- **高度**：60px，白色背景，底部阴影
- **左侧**：折叠/展开侧边栏的图标按钮（`<Fold>` / `<Expand>`）
- **中间**：应用全称标题
- **右侧**：语言切换下拉菜单，显示当前语言名称 + 地球图标

### 5.4 内容区

- 背景色 `#f0f2f5`
- 无内边距（由各页面自行控制 padding）
- 垂直方向可滚动

---

## 6. 国际化 (i18n)

### 6.1 架构

国际化系统由以下两部分组成：

1. **词典文件** `src/utils/i18n.ts` — 包含所有语言的翻译词条
2. **状态管理** `src/stores/locale.ts` — 管理当前语言选择，持久化到 `localStorage`

### 6.2 支持的语言

| 语言代码 | 显示名称 | 对应浏览器的 `toLocaleTimeString` 映射 |
|---|---|---|
| `zh-hans` | 简体中文 | `zh-Hans-CN` |
| `zh-hant` | 繁體中文 | `zh-Hant-TW` |
| `ja-jp` | 日本語 | `ja-JP` |
| `en-us` | English | `en-US` |

### 6.3 语言切换流程

```
用户点击下拉菜单
  → handleLocaleChange(langKey)
  → localeStore.setLocale(langKey)
    → 更新 locale ref
    → localStorage.setItem('furnace_locale', langKey)
    → document.documentElement.lang = langKey
    → Vue 响应式系统触发所有使用 t() 的组件重新渲染
      → ECharts 图表重新 setOption（通过 watch locale）
      → Element Plus 组件文本更新
```

### 6.4 翻译词条覆盖范围

- 应用标题与 Logo（`app.*`）
- 导航菜单项（`menu.*`）
- 监控面板（`dashboard.*`）
- 传感器标签与统计（`sensor.*`）
- 报警相关信息（`alarms.*`）
- 历史数据页（`history.*`）
- 温度监控页（`temperature.*`）

### 6.5 `t()` 函数使用模式

每个组件内部通过 `useLocaleStore()` 获取 `t` 函数，并以 `void localeStore.locale` 触发响应式依赖追踪：

```typescript
const localeStore = useLocaleStore()
function t(key: string): string {
  void localeStore.locale   // 建立响应式依赖
  return localeStore.t(key)
}
```

---

## 7. HTTP 请求层

### 7.1 Axios 封装 (`src/api/request.ts`)

封装了一个 `Request` 类，导出单例 `request` 实例：

| 配置项 | 值 |
|---|---|
| `baseURL` | `/api` |
| `timeout` | 30000ms (30s) |

#### 响应拦截器逻辑

```
HTTP Response
  → 解构出 { data }
  → 判断 data.code === 0 ?
    ├── YES → 返回 data.data（业务数据）
    └── NO  → ElMessage.error(data.message) + reject
```

统一的 API 响应格式约定：
```typescript
interface ApiResponse<T> {
  data: T
  code: number     // 0 = 成功，非 0 = 业务错误
  message: string  // 错误信息
}
```

#### 暴露的 HTTP 方法

| 方法 | 签名 | 用途 |
|---|---|---|
| `get<T>(url, config?)` | `Promise<T>` | GET 请求 |
| `post<T>(url, data?, config?)` | `Promise<T>` | POST 请求 |
| `put<T>(url, data?, config?)` | `Promise<T>` | PUT 请求 |
| `delete<T>(url, config?)` | `Promise<T>` | DELETE 请求 |

### 7.2 API 接口定义 (`src/api/furnace.ts`)

#### TypeScript 类型定义

**`SensorData`** — 实时传感器数据：
```typescript
interface SensorData {
  time: string              // 时间戳
  minute_of_day: number     // 一天中的分钟数 (0-1439)
  phase: string             // 当前阶段标识 (heating/holding/cooling/unload)
  phase_label: string       // 阶段中文标签
  core_temp: number         // 核心温度 (°C)
  target_temp: number       // 目标温度 (°C)
  fuel_flow: number         // 燃料流量 (Nm³/min)
  air_flow: number          // 进风流量 (Nm³/min)
  air_temp: number          // 进风温度 (°C)
  furnace_pressure: number  // 炉膛压力 (Pa)
  wall_temp_upper: number   // 上部壁温 (°C)
  wall_temp_mid: number     // 中部壁温 (°C)
  wall_temp_lower: number   // 下部壁温 (°C)
}
```

**`HistoryData`** — 历史时序数据（数组形式）：
```typescript
interface HistoryData {
  timestamps: string[]       // 时间戳数组
  core_temp: number[]
  target_temp: number[]
  fuel_flow: number[]
  air_flow: number[]
  air_temp: number[]
  furnace_pressure: number[]
  wall_temp_upper: number[]
  wall_temp_mid: number[]
  wall_temp_lower: number[]
  minute_of_day: number[]
}
```

**`AlarmInfo`** — 报警信息：
```typescript
interface AlarmInfo {
  alarmed: boolean           // 是否处于报警状态
  max_temp: number           // 预测温度最大值
  min_temp: number           // 预测温度最小值
  upper_limit: number | null // 报警上限
  lower_limit: number | null // 报警下限
  message: string            // 报警描述信息
  current_fuel: number       // 当前燃料流量
  current_air: number        // 当前进风流量
  suggested_fuel: number | null  // 建议燃料流量
  suggested_air: number | null   // 建议进风流量
  overshoot?: number         // 超调量
  direction?: string         // 报警方向 (上限/下限/双限/回温)
  max_at_minute?: number     // 最高温度所在分钟
}
```

**`PredictionData`** — 预测数据（含报警）：
```typescript
interface PredictionData {
  timestamps: string[]    // 预测时间点
  predictions: number[]   // 预测温度序列
  phase: string           // 当前阶段
  phase_label: string     // 阶段标签
  alarm: AlarmInfo        // 嵌套的报警信息
}
```

#### API 接口列表

| 函数 | 方法 | 路径 | 返回值 | 说明 |
|---|---|---|---|---|
| `getCurrent()` | GET | `/api/furnace/current` | `Promise<SensorData>` | 获取实时传感器数据 |
| `getHistory()` | GET | `/api/furnace/history` | `Promise<HistoryData>` | 获取历史时序数据 |
| `getPrediction()` | GET | `/api/furnace/prediction` | `Promise<PredictionData>` | 获取 AI 温度预测与报警 |
| `getPhases()` | GET | `/api/furnace/phases` | `Promise<any>` | 获取退火阶段信息 |

> **注意**：`Dashboard/` 和 `Sensors/` 视图中**并未使用** `request.ts` 封装的 Axios 实例，而是直接使用原生 `fetch()` API 调用接口。`Alarms/` 视图同样使用原生 `fetch()`。封装好的 `request.ts` 和 `furnace.ts` 中定义的接口函数（`getCurrent` 等）在当前代码中未被实际调用，处于备用状态。

---

## 8. Vite 构建配置

### 8.1 配置文件 (`vite.config.ts`)

```typescript
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')  // 路径别名
    }
  },
  server: {
    port: 3000,       // 开发服务器端口
    proxy: {
      '/api': {
        target: 'http://localhost:8080',  // 后端 API 地址
        changeOrigin: true
      }
    }
  }
})
```

### 8.2 路径别名

`@/` 映射到 `<project>/src/`，可在任意 `.ts` / `.vue` 文件中使用：

```typescript
import Layout from '@/components/Layout/index.vue'
import { useLocaleStore } from '@/stores/locale'
```

### 8.3 开发代理

开发环境下，所有 `/api/*` 请求被代理到 `http://localhost:8080`，解决前后端分离的跨域问题。

### 8.4 NPM Scripts

| 命令 | 执行内容 | 用途 |
|---|---|---|
| `npm run dev` | `vite` | 启动开发服务器 (端口 3000) |
| `npm run build` | `vue-tsc && vite build` | 先类型检查，再生产构建 |
| `npm run preview` | `vite preview` | 本地预览生产构建结果 |

---

## 9. TypeScript 配置

### 9.1 `tsconfig.json`

| 关键配置 | 值 | 说明 |
|---|---|---|
| `target` | `ES2020` | 目标 JS 版本 |
| `module` | `ESNext` | 模块系统 |
| `moduleResolution` | `bundler` | 模块解析策略 |
| `strict` | `true` | 启用所有严格检查 |
| `noUnusedLocals` | `true` | 禁止未使用的局部变量 |
| `noUnusedParameters` | `true` | 禁止未使用的函数参数 |
| `jsx` | `preserve` | 保留 JSX，由 Vue 编译器处理 |
| `baseUrl` | `.` | 基础路径 |
| `paths` | `{ "@/*": ["src/*"] }` | 路径映射与 Vite alias 保持一致 |

### 9.2 `tsconfig.node.json`

独立配置 Vite 配置文件本身的 TypeScript 编译选项，引用自主 `tsconfig.json` 的 `references` 字段。

---

## 10. 页面功能详解

### 10.1 监控面板 (`Dashboard`)

**路由**：`/dashboard`
**数据来源**：`GET /api/furnace/current` + `GET /api/furnace/history` + `GET /api/furnace/prediction`
**刷新频率**：每 2 秒轮询 (`setInterval(fetchData, 2000)`)

#### 10.1.1 阶段时间线 (Phase Bar)

- 顶部彩色进度条显示退火全流程的 4 个阶段：
  - **升温**（橙红色）：13.89% (约 3h20min) — 0:00 ~ 3:20
  - **保温**（黄色）：27.78% (约 6h40min) — 3:20 ~ 10:00
  - **降温**（青色）：41.67% (约 10h) — 10:00 ~ 20:00
  - **卸装料**（灰色）：16.67% (约 4h) — 20:00 ~ 24:00
- 绿色三角形标记当前进度位置（根据 `minute_of_day / 1440` 计算百分比）
- 时间轴刻度：00:00 / 03:20 / 10:00 / 20:00 / 24:00
- 阶段信息行：当前时间、周期进度百分比、当前阶段标签（颜色随阶段变化）、系统状态（正常/报警）

#### 10.1.2 核心温度曲线 (主图表)

- **图表类型**：ECharts 多系列折线图，Y 轴范围 0-1000°C
- **图例**（5 条线）：
  1. 历史核心温度（蓝色实线 + 蓝色渐变填充）
  2. 目标温度（橙色虚线）
  3. 预测温度（绿色粗实线 + 绿色渐变填充）— 拼接在历史数据之后
  4. 报警上限（红色点线）— 仅当 `upper_limit` 不为 null 时显示
  5. 报警下限（橙色点线）— 仅当 `lower_limit` 不为 null 时显示
- 点击图表卡片弹出大图对话框（80% 宽度），下方附带 21 列温度预测明细表格：
  - t-10 ~ t-1（历史值）、当前、t+1 ~ t+10（预测值）
  - 超出报警上限的单元格标红，低于下限的标黄

#### 10.1.3 交互式退火炉模型

- 显示退火炉设备示意图 (`/images/furnace_model.png`)
- 9 个**传感器热点**叠加在图片上（绝对定位，按百分比坐标放置）
- 每个热点显示实时数值，颜色区分不同类型
- **核心温度热点**放大显示，报警时变为红色闪烁
- 点击热点弹出传感器历史趋势对话框
- 点击卡片弹出全屏大图（95% 宽度），传感器热点等比例缩放

#### 10.1.4 状态与建议

- **左半部分**：系统状态框
  - 正常状态：绿色渐变背景 + 边框
  - 报警状态：红色渐变背景 + 红色边框 + 脉冲动画
  - 显示阶段、预测温度范围、报警上下限
- **右半部分**：调整建议框
  - 报警时：显示当前 vs 建议的燃料流量和进风流量，划线旧值，高亮新值
  - 正常时：显示"当前运行正常，无需调整" + 当前流量值

#### 10.1.5 底部状态栏

- 左：最后更新时间
- 右：Bi-LSTM Model 标识（蓝色圆点）+ Real-time 标识（绿色圆点）

#### 10.1.6 图表自适应

- 窗口 `resize` 事件触发所有 ECharts 实例的 `resize()`
- 语言切换时重新渲染所有图表（`watch locale`）

### 10.2 传感器视图 (`Sensors`)

**路由**：`/sensors`
**数据来源**：`GET /api/furnace/current` + `GET /api/furnace/history`
**刷新频率**：每 2 秒轮询

#### 10.2.1 传感器卡片网格

- 3 列网格布局（`grid-template-columns: repeat(3, 1fr)`），共 9 张卡片
- 每张卡片显示：
  - **头部**：图标 + 传感器名称 + LIVE 标签（绿色脉冲动画）
  - **当前值**：大号等宽字体显示，颜色跟随传感器类型
  - **迷你趋势图**：60px 高的 ECharts 折线图，无坐标轴/无提示，纯可视化
  - **底部统计**：最小值 / 平均值 / 最大值（实时计算）

#### 10.2.2 9 个传感器

| ID | 名称 | 单位 | 颜色 |
|---|---|---|---|
| `core_temp` | 核心温度 | °C | `#409eff` (蓝) |
| `target_temp` | 目标温度 | °C | `#e6a23c` (橙) |
| `fuel_flow` | 燃料流量 | Nm³/min | `#f56c6c` (红) |
| `air_flow` | 进风流量 | Nm³/min | `#3498db` (蓝) |
| `air_temp` | 进风温度 | °C | `#e67e22` (橙) |
| `furnace_pressure` | 炉膛压力 | Pa | `#9b59b6` (紫) |
| `wall_temp_upper` | 上部壁温 | °C | `#e74c3c` (红) |
| `wall_temp_mid` | 中部壁温 | °C | `#2ecc71` (绿) |
| `wall_temp_lower` | 下部壁温 | °C | `#1abc9c` (青) |

#### 10.2.3 传感器详情弹窗

- 点击任意传感器卡片弹出 ECharts 大图（70% 宽度，400px 高度）
- 显示该传感器完整历史趋势折线图，带颜色渐变填充

### 10.3 异常记录 (`Alarms`)

**路由**：`/alarms`
**数据来源**：`GET /api/furnace/alarms` + `PUT /api/furnace/alarms/:id/acknowledge` + `PUT /api/furnace/alarms/acknowledge-all`
**刷新频率**：每 5 秒轮询

#### 10.3.1 统计卡片

3 张卡片展示报警概况：

| 卡片 | 图标 | 颜色 |
|---|---|---|
| 报警总数 | `<Warning>` | 红色 `#f56c6c` |
| 未确认 | `<Bell>` | 橙色 `#e6a23c` |
| 已确认 | `<CircleCheck>` | 绿色 `#67c23a` |

已确认数 = 总数 - 未确认数

#### 10.3.2 筛选栏

- **阶段筛选**：下拉选择 `heating` / `holding` / `cooling`，支持清空
- **状态筛选**：下拉选择 未确认 (`false`) / 已确认 (`true`)，支持清空
- **全部确认按钮**：批量确认所有未处理报警
- 筛选条件变化时自动重新请求数据（`watch([filterPhase, filterAck])`）

#### 10.3.3 报警列表表格

| 列 | 宽度 | 说明 |
|---|---|---|
| 状态 | 80px | 未确认（红色标签）/ 已确认（灰色标签） |
| 时间 | 180px | `YYYY-MM-DD HH:mm:ss` 格式 |
| 阶段 | 100px | 升温/保温/降温 彩色标签 |
| 方向 | 80px | 上升/下降/上限/下限/双限/回温 |
| 预测最高温度 | 130px | 红色高亮显示 |
| 超调量 | 100px | +X.X°C，无超调则显示 `--` |
| 报警限 | 130px | 上限/下限的具体温度值 |
| 当前温度 | 110px | 当前实际温度 |
| 建议燃料 | 110px | 当前值（划线）→ 建议值（绿色） |
| 描述 | min 200px | 动态翻译的报警描述文字 |
| 操作 | 100px (fixed) | 未确认时显示"确认"按钮；已确认显示 `--` |

#### 10.3.4 逐条确认与批量确认

- **逐条确认**：`PUT /api/furnace/alarms/{id}/acknowledge`
- **全部确认**：`PUT /api/furnace/alarms/acknowledge-all`（返回 `{ count }` 确认数量）
- 操作完成后刷新列表，显示成功/失败提示

#### 10.3.5 报警消息动态翻译

`alarmMsg()` 函数对后端返回的中文报警消息做正则替换，将中文关键词替换为当前语言的对应词条，实现报警描述的国际化。

---

## 11. 状态管理 (Pinia)

### 11.1 `useLocaleStore` (`src/stores/locale.ts`)

```typescript
// Setup Store 语法
export const useLocaleStore = defineStore('locale', () => {
  const locale = ref<Locale>(getSavedLocale())

  function t(key: string): string { ... }
  function setLocale(l: Locale) { ... }

  return { locale, t, setLocale }
})
```

**状态**：
- `locale` — 当前语言代码，默认从 `localStorage` 读取，回退到 `zh-hans`

**方法**：
- `t(key)` — 从 `messages[locale][key]` 取值，key 不存在时返回 key 本身
- `setLocale(l)` — 切换语言并同步到 `localStorage` 和 `document.documentElement.lang`

### 11.2 `stores/index.ts`

预留的聚合入口，当前为空文件，仅含一行注释。

---

## 12. 数据流与组件通信

```
后端 API (localhost:8080)
    │
    ▼
各页面组件独立 fetch()
    │
    ├── 定时轮询更新
    │     Dashboard: 2s 间隔
    │     Sensors:   2s 间隔
    │     Alarms:    5s 间隔
    │
    ├── 本地 ref / reactive 存储
    │     currentData   → SensorData
    │     historyData   → HistoryData
    │     prediction    → PredictionData
    │     alarmData     → { total, unacknowledged, records[] }
    │
    └── ECharts setOption() 驱动图表更新
          │
          ├── updateTempChart()      # Dashboard 主图表
          ├── updateMiniCharts()     # Sensors 迷你图表
          ├── initSensorChart()      # 传感器弹窗图表
          └── initTempFullChart()    # 温度全屏图表
```

**组件通信模式**：
- **无跨组件状态共享**：各页面的数据获取是独立且重复的（每个页面各自 `fetch` 自己的数据）
- **全局状态仅用于国际化**：`useLocaleStore` 是唯一的 Pinia Store
- **无 props/emits 跨层级传递**：组件树浅，Layout → router-view → 各页面，无需深层通信

---

## 13. 样式体系

### 13.1 全局样式 (`main.css`)

- 全局 `*` 选择器重置 margin/padding/box-sizing
- `html, body, #app` 设置 100% 宽度和高度
- 统一字体栈：`-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`

### 13.2 组件样式

- 所有组件使用 Vue 的 `<style scoped>` 实现样式隔离
- Element Plus 组件样式通过 `:deep()` 穿透 Scoped CSS
- 主题色使用 Element Plus 默认色板，未自定义主题变量
- 动画使用 CSS `@keyframes`：
  - `pulse` — LIVE 标签和传感器圆点的脉冲效果
  - `alarmPulse` — 报警状态下的红色闪烁
  - `sensorPulse` — 传感器热点发光脉冲

### 13.3 响应式设计

当前项目**未做移动端适配**，面向桌面端工业监控大屏场景设计。布局为固定宽度侧边栏 + 弹性内容区。

---

## 14. 后端 API 契约

### 14.1 代理配置

开发环境下 Vite 将 `/api/*` 代理到 `http://localhost:8080`。

### 14.2 API 清单

| 方法 | 路径 | 说明 | 调用方 |
|---|---|---|---|
| GET | `/api/furnace/current` | 获取当前传感器实时数据 | Dashboard, Sensors |
| GET | `/api/furnace/history` | 获取历史时序数据 | Dashboard, Sensors |
| GET | `/api/furnace/prediction` | 获取 AI 温度预测 + 报警 | Dashboard |
| GET | `/api/furnace/phases` | 获取退火阶段信息 | (未使用) |
| GET | `/api/furnace/alarms` | 获取报警记录列表（支持 `?phase=&acknowledged=`） | Alarms |
| PUT | `/api/furnace/alarms/:id/acknowledge` | 确认单条报警 | Alarms |
| PUT | `/api/furnace/alarms/acknowledge-all` | 批量确认所有报警 | Alarms |

### 14.3 统一响应格式

```json
{
  "code": 0,
  "data": { ... },
  "message": "success"
}
```

`code === 0` 表示成功，非 0 表示业务异常。

---

## 15. 技术要点与设计决策

### 15.1 直接使用 fetch 而非封装的 Axios

Dashboard、Sensors、Alarms 三个核心页面直接使用浏览器原生 `fetch()` API 调用后端，而非通过 `src/api/request.ts` 封装的 Axios 实例。这意味着：
- 不经过统一的响应拦截器（不检查 `code === 0`）
- 不经过统一的错误提示（需自行 `catch` 并 `console.error`）
- 代码中存在冗余：`request.ts` 和 `furnace.ts` 的封装未被使用

### 15.2 ECharts 实例管理

- 每个图表使用独立的 `echarts.init()` 实例
- 窗口 resize 时调用 `resize()` 防止图表变形
- 对话框关闭时 `dispose()` 销毁图表实例，防止内存泄漏
- 语言切换时重新 `setOption()` 更新图例、轴标签等文本

### 15.3 AI 模型标识

Dashboard 底部标注 `Bi-LSTM Model`，表明后端使用的温度预测模型为**双向长短期记忆网络**（Bidirectional Long Short-Term Memory），这是时序预测领域常用的深度学习架构。

### 15.4 退火工艺背景

系统模拟的退火炉工艺流程为 24 小时周期：

| 阶段 | 时间范围 | 时长 | 特点 |
|---|---|---|---|
| 升温 (heating) | 00:00 ~ 03:20 | 3h20min | 核心温度快速上升至目标 |
| 保温 (holding) | 03:20 ~ 10:00 | 6h40min | 维持高温，使材料均匀受热 |
| 降温 (cooling) | 10:00 ~ 20:00 | 10h | 控制降温速率，避免材料应力 |
| 卸装料 (unload) | 20:00 ~ 24:00 | 4h | 出炉与下一批次装料 |

### 15.5 页面兼容性

- 目标浏览器：支持 ES2020 的现代浏览器（Chrome 90+, Edge 90+, Firefox 90+, Safari 15+）
- HTML `lang` 属性设为 `zh-CN`
- 使用等宽字体 (`monospace`) 显示数值，确保数字对齐

---

## 16. 开发指南

### 16.1 环境要求

- Node.js >= 18
- npm >= 9

### 16.2 本地启动

```bash
npm install
npm run dev
# 访问 http://localhost:3000
```

### 16.3 生产构建

```bash
npm run build
# 产物输出到 dist/
npm run preview   # 本地预览
```

### 16.4 添加新页面

1. 在 `src/views/` 下创建新目录和 `index.vue`
2. 在 `src/router/index.ts` 的 `children` 数组中添加路由配置
3. 在 `src/components/Layout/index.vue` 的 `<el-menu>` 中添加导航菜单项
4. 在 `src/utils/i18n.ts` 的 4 个语言对象中添加翻译词条

### 16.5 添加新 API 接口

在 `src/api/furnace.ts` 中：
1. 定义 TypeScript 接口类型
2. 使用 `request.get/post/put/delete` 封装调用函数

---

## 17. 已知问题与改进方向

### 17.1 当前问题

1. **API 封装未使用**：`src/api/request.ts` 和 `src/api/furnace.ts` 与视图层代码脱节，视图层直接使用 `fetch()`
2. **重复代码**：Dashboard 和 Sensors 中的 `sensorConfig`、`formatValue`、`formatTime` 等定义重复
3. **未使用的视图**：`Alarm/`、`History/`、`Temperature/` 三个页面为静态演示页，未接入路由和真实数据
4. **无错误处理 UI**：数据加载失败时仅在控制台输出，用户界面无反馈（无 loading 骨架屏、无错误提示组件）
5. **无 TypeScript 类型标注**：Dashboard 和 Sensors 中大量使用 `any` 类型（`ref<any>(null)`）
6. **轮询未处理页面隐藏**：当浏览器标签页不可见时，轮询仍在执行，浪费资源
7. **ECharts 全量引入**：`import * as echarts from 'echarts'` 引入整个库，未按需加载

### 17.2 建议改进

1. 统一使用 `src/api/furnace.ts` 的封装函数，消除 `fetch` 的直接调用
2. 提取公共的传感器配置、格式化函数、ECharts 工具函数到 `src/utils/`
3. 对历史数据、温度监控等页面接入真实 API 并注册路由
4. 添加 `Suspense` + loading/error 状态处理
5. 使用 `usePageVisibility` 控制轮询的启停
6. 按需引入 ECharts 组件，减少打包体积
7. 添加 `useSensorData` 等 Composition API hooks，减少组件内的重复逻辑
