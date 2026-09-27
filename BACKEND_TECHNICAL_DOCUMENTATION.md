# 退火炉全流程温度预测与报警系统 - 技术文档

## 目录

1. [项目概述](#1-项目概述)
2. [系统架构](#2-系统架构)
3. [目录结构](#3-目录结构)
4. [核心模块详解](#4-核心模块详解)
5. [物理模型与数据模拟](#5-物理模型与数据模拟)
6. [机器学习模型](#6-机器学习模型)
7. [API 接口文档](#7-api-接口文档)
8. [配置管理](#8-配置管理)
9. [数据流程](#9-数据流程)
10. [部署与运维](#10-部署与运维)

---

## 1. 项目概述

### 1.1 项目简介

本项目是一个**退火炉全流程温度预测与过热报警系统**，采用物理仿真 + 机器学习双轮驱动的方案，实现：

- 基于传感器数据的实时温度监测
- 升温/保温/降温三阶段的 Bi-LSTM 神经网络温度预测（未来 10 分钟）
- 基于预测结果的智能报警与控制建议
- 实时数据写入外部实时数据库

### 1.2 技术栈

| 层级 | 技术选型 |
|------|---------|
| **Web 框架** | FastAPI + Uvicorn |
| **数据库** | PostgreSQL + SQLAlchemy (async) |
| **机器学习** | PyTorch + Scikit-learn + Joblib |
| **数据处理** | Pandas + NumPy |
| **日志** | Loguru |
| **配置** | Pydantic Settings + YAML |
| **打包** | PyInstaller |

### 1.3 关键特性

- ✅ 三阶段独立建模，按工艺周期切换预测模型
- ✅ 物理仿真生成训练数据，支持故障场景注入
- ✅ 实时预测未来 10 分钟温度
- ✅ 多级报警阈值，带控制建议
- ✅ 异步 API，高性能
- ✅ 可打包为独立二进制部署

---

## 2. 系统架构

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────┐
│                      前端 / 客户端                        │
│              (浏览器 / 第三方系统)                        │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP REST API
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI 应用层                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │ Health API  │  │ Furnace API │  │  (更多...)  │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              FurnaceService (业务核心)                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │  1. 模型加载 (3个 Bi-LSTM)                        │  │
│  │  2. 数据模拟 (闭环物理模型)                        │  │
│  │  3. 阶段预测 (按分钟切换模型)                       │  │
│  │  4. 报警检测 (阈值比对 + 控制建议)                  │  │
│  │  5. 后台线程 (每4秒更新数据 + 写入实时库)           │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
         │                            │
         ▼                            ▼
┌──────────────────┐      ┌──────────────────────────┐
│  PostgreSQL DB   │      │  外部实时数据库 (RTDB)   │
│  (历史数据存储)  │      │  (实时数据写入)          │
└──────────────────┘      └──────────────────────────┘
```

### 2.2 工艺阶段划分

系统按退火工艺分为四个阶段：

| 阶段名 | 时间（分钟/天） | 说明 |
|--------|----------------|------|
| **heating** | 0-200 | 升温阶段，从室温~790°C |
| **holding** | 200-600 | 保温阶段，790°C 恒温 |
| **cooling** | 600-1200 | 降温阶段，790°C → 200°C |
| **unload** | 1200-1440 | 卸装料阶段，自然冷却 |

**注**：unload 阶段不做预测，仅做数据展示。

---

## 3. 目录结构

```
furnace_backend/
├── main.py                             # 应用入口
├── requirements.txt                    # 运行依赖
├── requirements-build.txt              # 构建依赖（含 PyInstaller）
├── build-ubuntu.sh                     # Ubuntu 一键构建脚本
├── furnace_backend.spec                # PyInstaller spec 文件
├── config/
│   └── config.yaml                     # 配置文件
├── app/
│   ├── __init__.py
│   ├── core/                           # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py                   # 配置管理
│   │   ├── database.py                 # 数据库连接
│   │   ├── logging.py                  # 日志配置
│   │   └── response.py                 # 统一响应格式
│   ├── api/                            # API 路由
│   │   ├── __init__.py
│   │   ├── health.py                   # 健康检查接口
│   │   └── furnace.py                  # 退火炉业务接口
│   ├── services/                       # 业务服务
│   │   ├── __init__.py
│   │   └── furnace_service.py          # 核心业务逻辑
│   ├── models/                         # 数据库模型（预留）
│   │   └── __init__.py
│   └── schemas/                        # Pydantic 模型（预留）
│       └── __init__.py
├── simulation.py                       # 物理仿真脚本
├── heating.py                          # 升温模型训练脚本
├── holding.py                          # 保温模型训练脚本
├── cooling.py                          # 降温模型训练脚本
├── heating_bilstm.pth                  # 升温模型权重
├── heating_feat_scaler.pkl             # 升温特征标准化器
├── heating_target_scaler.pkl           # 升温目标标准化器
├── cooling_bilstm.pth                  # 降温模型权重
├── cooling_feat_scaler.pkl             # 降温特征标准化器
├── cooling_target_scaler.pkl           # 降温目标标准化器
├── holding_bilstm.pth                  # 保温模型权重
├── holding_feat_scaler.pkl             # 保温特征标准化器
├── holding_target_scaler.pkl           # 保温目标标准化器
├── logs/                               # 日志目录（运行时生成）
│   └── app.log
├── BUILD_UBUNTU.md                     # Ubuntu 打包文档
└── TECHNICAL_DOCUMENTATION.md          # 本文档
```

---

## 4. 核心模块详解

### 4.1 main.py - 应用入口

**文件位置**：`furnace_backend/main.py`

**功能说明**：

- 创建 FastAPI 应用
- 配置 CORS（允许所有来源）
- 注册路由
- 启动生命周期管理

**核心代码**：

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core import settings, setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting furnace backend service...")
    yield
    logger.info("Shutting down furnace backend service...")

app = FastAPI(
    title="退火炉温度预测系统 API",
    description="退火炉全流程温度预测与过热报警系统",
    version="1.0.0",
    lifespan=lifespan
)
```

**运行方式**：

```bash
# 开发模式
python main.py

# 或使用 Uvicorn
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

### 4.2 app/core/config.py - 配置管理

**文件位置**：`furnace_backend/app/core/config.py`

**功能说明**：

- 统一管理所有配置项
- 支持 YAML 配置文件 + 环境变量
- 自动检测是否在 PyInstaller 打包环境中运行

**核心配置项**：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `HOST` | str | "0.0.0.0" | 服务监听地址 |
| `PORT` | int | 8080 | 服务监听端口 |
| `DEBUG` | bool | True | 调试模式 |
| `DATABASE_URL` | str | ... | PostgreSQL 连接 URL |
| `HEATING_MODEL_PATH` | str | "heating_bilstm.pth" | 升温模型路径 |
| `COOLING_MODEL_PATH` | str | "cooling_bilstm.pth" | 降温模型路径 |
| `HOLDING_MODEL_PATH` | str | "holding_bilstm.pth" | 保温模型路径 |
| `CORE_TEMP_THRESHOLD` | float | 810.0 | 核心温度报警阈值 |
| `LOG_LEVEL` | str | "INFO" | 日志级别 |
| `LOG_FILE_PATH` | str | "logs/app.log" | 日志文件路径 |

**关键实现 - 路径处理**：

```python
def get_base_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent  # 打包后取 exe 同级目录
    return Path(__file__).parent.parent.parent  # 开发模式取项目根目录

class Settings(BaseSettings):
    BASE_DIR: Path = get_base_dir()
    CONFIG_PATH: Path = BASE_DIR / "config" / "config.yaml"
```

这样确保无论是开发环境还是打包后，配置文件、模型文件都能正确加载。

### 4.3 app/core/logging.py - 日志配置

**文件位置**：`furnace_backend/app/core/logging.py`

**功能说明**：

- 使用 Loguru 作为日志库
- 同时输出到控制台和文件
- 支持日志轮转（按大小/时间）
- 支持 ZIP 压缩旧日志

**配置项**（来自 config.yaml）：

```yaml
logging:
  level: "INFO"
  file_path: "logs/app.log"
  rotation: "10 MB"
  retention: "7 days"
```

### 4.4 app/core/response.py - 统一响应格式

**文件位置**：`furnace_backend/app/core/response.py`

**响应结构**：

```json
{
  "data": ...,      // 任意类型数据
  "code": 0,        // 0 表示成功，非 0 表示失败
  "message": ""     // 响应消息
}
```

**使用示例**：

```python
from app.core import success_response, error_response

# 成功响应
return success_response(data=result, message="操作成功")

# 失败响应
return error_response(code=-1, message="参数错误")
```

### 4.5 app/core/database.py - 数据库连接

**文件位置**：`furnace_backend/app/core/database.py`

**功能说明**：

- 使用 SQLAlchemy 2.0 + asyncpg 异步连接
- 连接池配置
- 提供 `get_db()` 依赖注入函数供路由使用

**配置项**（来自 config.yaml）：

```yaml
database:
  url: "postgresql+asyncpg://user:pass@host:5432/db"
  echo: false
  pool_size: 10
  max_overflow: 20
```

### 4.6 app/api/furnace.py - 业务 API 路由

**文件位置**：`furnace_backend/app/api/furnace.py`

**功能说明**：

定义所有退火炉业务相关的 HTTP 接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/furnace/current` | 获取当前传感器数据 |
| GET | `/api/furnace/history` | 获取历史数据（过去 60 分钟） |
| GET | `/api/furnace/prediction` | 获取预测数据与报警状态 |
| GET | `/api/furnace/phases` | 获取阶段时间边界信息 |
| GET | `/api/furnace/alarms` | 获取报警记录 |
| PUT | `/api/furnace/alarms/{id}/acknowledge` | 确认单条报警 |
| PUT | `/api/furnace/alarms/acknowledge-all` | 确认所有报警 |

详细接口文档见 [第 7 章 API 接口文档](#7-api-接口文档)。

---

## 5. 物理模型与数据模拟

### 5.1 概述

本系统采用**物理仿真**生成训练数据，而不是完全依赖历史数据。这样做的好处：

- 可以精确控制参数
- 可以注入各种故障场景
- 不需要现场停工就能获得数据

物理仿真代码位于：`simulation.py`

### 5.2 核心物理公式

#### 5.2.1 能量平衡方程

工件核心温度变化由能量平衡决定：

```
m * Cp * dT/dt = Q_conv + Q_rad
```

- `m`: 工件质量（kg）
- `Cp`: 比热容（J/(kg·K)），温度相关
- `Q_conv`: 对流换热量（W）
- `Q_rad`: 辐射换热量（W）

#### 5.2.2 比热容模型

```python
def cp(T):
    """T 单位: °C，返回: J/(kg·K)"""
    return 460.0 + 0.2 * T
```

假设比热容随温度线性增长，符合一般金属特性。

#### 5.2.3 对流换热

```
Q_conv = h * A * (T_gas - T_core)
```

- `h`: 对流换热系数，与空气流量正相关
- `A`: 换热面积
- `T_gas`: 炉气温度（用壁温均值近似）

对流换热系数模型：

```python
def heat_transfer_coeff(air_flow):
    max_air = RATED_FUEL_FLOW * AIR_FUEL_RATIO * 1.2
    ratio = np.clip(air_flow / max_air, 0, 1)
    return 20.0 + 60.0 * ratio  # W/(m²·K)
```

#### 5.2.4 辐射换热（Stefan-Boltzmann 定律）

```
Q_rad = ε * σ * A * (T_wall⁴ - T_core⁴)
```

- `ε`: 发射率（0.85）
- `σ`: 斯特藩-玻尔兹曼常数（5.67e-8 W/(m²·K⁴)）
- `T_wall`: 炉壁温度（三区平均）
- `T_core`: 工件核心温度

**注意**：温度需要转换为开尔文（+273.15）。

### 5.3 数值求解方法（RK4）

系统使用**四阶龙格-库塔法（RK4）**对微分方程进行数值积分，时间步长 60 秒（1 分钟）。

RK4 步骤：

```python
def rk4_step(t_core, t_gas, t_wall, air_flow, mass, area, dt):
    def dTdt(T):
        h = heat_transfer_coeff(air_flow)
        Q_conv = h * area * (t_gas - T)
        T_core_K = T + 273.15
        T_wall_K = t_wall + 273.15
        Q_rad = SIGMA * EMISSIVITY * area * (T_wall_K**4 - T_core_K**4)
        return (Q_conv + Q_rad) / (mass * cp(T))

    k1 = dTdt(t_core)
    k2 = dTdt(t_core + 0.5 * dt * k1)
    k3 = dTdt(t_core + 0.5 * dt * k2)
    k4 = dTdt(t_core + dt * k3)

    return t_core + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)
```

相比欧拉法，RK4 精度更高。

### 5.4 物理常数

| 常数 | 值 | 单位 | 说明 |
|------|-----|------|------|
| `MASS` | 5000.0 | kg | 工件质量 |
| `AREA` | 15.0 | m² | 有效换热面积 |
| `EMISSIVITY` | 0.85 | - | 综合发射率 |
| `RATED_GAS_DAY` | 2500.0 | m³/day | 额定日气耗 |
| `AIR_FUEL_RATIO` | 10.8 | - | 空燃比 |
| `THERMAL_EFFICIENCY` | 0.30 | - | 热效率 |
| `T_AMBIENT` | 25.0 | °C | 环境温度 |

### 5.5 目标温度曲线生成

系统生成 7 天（10080 分钟）的目标温度曲线，每天的工艺如下：

| 阶段 | 时间（分钟/天） | 温度曲线 |
|------|----------------|---------|
| 升温 | 0-200 | T_ambient → 790°C，幂函数曲线 |
| 保温 | 200-600 | 790°C 恒定，±2°C 波动 |
| 慢冷 | 600-950 | 790°C → 700°C，线性 |
| 快冷 | 950-1200 | 700°C → 200°C，幂函数曲线 |
| 卸装料 | 1200-1440 | 25°C，环境温度 |

### 5.6 控制逻辑（燃料流量）

燃料流量按工艺阶段设定：

| 阶段 | 燃料流量（额定值倍数） |
|------|---------------------|
| heating | 0.20 ~ 0.50（随温度递增） |
| holding | 0.15 |
| slow cooling | 0.04 |
| fast cooling | 0.01 |
| unload | 0.0 |

空气流量 = 燃料流量 × 10.8 + 0.3

### 5.7 壁温模型

三区炉壁温度（热气上升，上壁 > 中壁 > 下壁）：

```python
wall_upper[i] = target[i] + 15 + noise
wall_mid[i] = target[i] + 8 + noise
wall_lower[i] = target[i] + 2 + noise
```

### 5.8 传感器噪声

为了更接近真实，所有传感器数据都添加高斯白噪声：

| 传感器 | 噪声标准差 |
|--------|----------|
| core_temp | 1.5 °C |
| fuel_flow | 0.02 m³/min |
| air_flow | 0.03 m³/min |
| air_temp | 0.8 °C |
| furnace_pressure | 2.0 Pa |

### 5.9 输出数据格式

仿真输出为 DataFrame，包含以下列：

| 列名 | 类型 | 单位 | 说明 |
|------|------|------|------|
| `time_stamp` | datetime | - | 时间戳 |
| `fuel_flow` | float | m³/min | 燃料流量 |
| `air_flow` | float | m³/min | 空气流量 |
| `air_temp` | float | °C | 进风温度 |
| `furnace_pressure` | float | Pa | 炉膛压力 |
| `wall_temp_upper` | float | °C | 上区壁温 |
| `wall_temp_mid` | float | °C | 中区壁温 |
| `wall_temp_lower` | float | °C | 下区壁温 |
| `target_temp` | float | °C | 目标温度 |
| `core_temp` | float | °C | 核心温度 |

---

## 6. 机器学习模型

### 6.1 模型选型与架构

系统采用**双向 LSTM（Bi-LSTM）**作为预测模型，原因：

- LSTM 适合时间序列预测
- 双向可以利用过去和未来的上下文（预测时只用过去）
- 参数量适中，推理速度快

**模型架构**：

```
Input (window=60, features=8)
   │
   ▼
Bi-LSTM (hidden=48, layers=2, dropout=0.1)
   │
   ├─ forward  ─┐
   │            ├─ concat → (batch, 96)
   └─ backward ─┘
   │
   ▼
Dense (32, ReLU) + Dropout (0.1)
   │
   ▼
Dense (10, Linear)
   │
   ▼
Output (predict horizon=10)
```

**超参数**：

| 参数 | 值 |
|------|---|
| `INPUT_WINDOW` | 60 分钟 |
| `PREDICT_HORIZON` | 10 分钟 |
| `HIDDEN_SIZE` | 48 |
| `NUM_LAYERS` | 2 |
| `DROPOUT` | 0.1 |
| `BATCH_SIZE` | 16 |
| `LEARNING_RATE` | 8e-4 |
| `EPOCHS` | 200-300（早停） |

### 6.2 特征工程

**输入特征**（8 维）：

| 特征 | 说明 |
|------|------|
| fuel_flow | 燃料流量 |
| air_flow | 空气流量 |
| air_temp | 进风温度 |
| furnace_pressure | 炉膛压力 |
| wall_temp_upper | 上区壁温 |
| wall_temp_mid | 中区壁温 |
| wall_temp_lower | 下区壁温 |
| target_temp | 目标温度 |

**输出**：未来 10 分钟的核心温度。

### 6.3 数据标准化

使用 `StandardScaler` 对特征和目标分别做标准化：

```
z = (x - μ) / σ
```

训练时保存 scaler：

```python
feat_scaler = StandardScaler()
target_scaler = StandardScaler()
features_scaled = feat_scaler.fit_transform(features)
targets_scaled = target_scaler.fit_transform(targets.reshape(-1, 1)).flatten()
joblib.dump(feat_scaler, "feat_scaler.pkl")
joblib.dump(target_scaler, "target_scaler.pkl")
```

推理时逆向转换回实际温度值。

### 6.4 三个阶段独立模型

为每个工艺阶段训练一个独立的模型：

| 模型 | 训练数据范围 | 故障注入 |
|------|-------------|--------|
| `heating_bilstm.pth` | 每天 0-210 分钟 | 目标温度设高（810-860°C），燃料偏高 20-50% |
| `holding_bilstm.pth` | 每天 200-600 分钟 | 过温、欠温、温度振荡 |
| `cooling_bilstm.pth` | 每天 600-1200 分钟 | 燃料未降、降温过慢、异常回温 |

### 6.5 训练策略

#### 6.5.1 损失函数

使用 **Huber Loss**（smooth L1），比 MSE 对异常值更鲁棒：

```
Lδ(y, ŷ) = {
    0.5 * (y - ŷ)²          if |y - ŷ| ≤ δ
    δ * (|y - ŷ| - 0.5 * δ)  otherwise
}
```

```python
criterion = nn.HuberLoss(delta=1.0)
```

#### 6.5.2 优化器

使用 **AdamW**（带权重衰减的 Adam）：

```python
optimizer = torch.optim.AdamW(
    model.parameters(),
    lr=LEARNING_RATE,
    weight_decay=1e-4
)
```

#### 6.5.3 学习率调度

使用 **Cosine Annealing with Warm Restarts**：

```python
scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
    optimizer,
    T_0=40,      # 40 epoch 后第一次重启
    T_mult=2,    # 每次重启，周期加倍
    eta_min=1e-5 # 最小学习率
)
```

#### 6.5.4 早停（Early Stopping）

- 耐心值：35 epoch
- 最小改进：1e-7
- 保存验证集 loss 最低的模型

### 6.6 数据集划分

按周期划分（避免数据泄露）：

- 训练集：正常周期 0~N-3 + 全部故障周期
- 验证集：正常周期 N-2
- 测试集：正常周期 N-1

### 6.7 故障增强数据

通过物理模型注入故障，数据量扩充：

| 阶段 | 正常数据 | 故障数据（×3） | 总数据 |
|------|---------|--------------|--------|
| heating | ~1470 条/7天 | ~3780 条 | ~5250 条 |
| holding | ~2800 条/7天 | ~7200 条 | ~10000 条 |
| cooling | ~4200 条/7天 | ~14400 条 | ~18600 条 |

故障配置示例（heating 阶段）：

```python
fault_configs = [
    (810, 1.20),  # 目标 810°C，燃料 ×1.20
    (820, 1.30),  # 目标 820°C，燃料 ×1.30
    (830, 1.35),  # ...
    (840, 1.40),
    (850, 1.45),
    (860, 1.50),  # 目标 860°C，燃料 ×1.50
]
```

### 6.8 模型评估指标

在测试集上评估：

| 指标 | 公式 | 说明 |
|------|------|------|
| **MAE** | Σ\|y - ŷ\| / n | 平均绝对误差（°C） |
| **RMSE** | √(Σ(y - ŷ)² / n) | 均方根误差（°C） |
| **R²** | 1 - Σ(y - ŷ)² / Σ(y - ȳ)² | 决定系数（越接近 1 越好） |

### 6.9 推理流程

运行时的预测步骤：

1. 根据当前 `minute_of_day` 判断阶段
2. 选择对应阶段的模型
3. 从当前数据滑窗取过去 60 分钟
4. 用 `feat_scaler` 标准化特征
5. 模型前向传播
6. 用 `target_scaler` 反标准化预测值
7. 返回未来 10 分钟的温度

---

## 7. API 接口文档

### 7.1 通用响应格式

所有接口返回统一格式：

```json
{
  "data": T,         // 数据（可为 null）
  "code": 0,         // 0 表示成功
  "message": ""      // 消息
}
```

---

### 7.2 健康检查

#### GET /api/health

**功能**：检查服务健康状态

**响应示例**：

```json
{
  "data": {
    "status": "ok",
    "service": "furnace_backend"
  },
  "code": 0,
  "message": "Service is healthy"
}
```

---

### 7.3 获取当前数据

#### GET /api/furnace/current

**功能**：获取最新的传感器数据

**响应示例**：

```json
{
  "data": {
    "time": "2026-05-01T03:20:00",
    "minute_of_day": 200,
    "phase": "holding",
    "phase_label": "保温阶段",
    "core_temp": 789.5,
    "target_temp": 790.0,
    "fuel_flow": 0.043,
    "air_flow": 0.764,
    "air_temp": 32.5,
    "furnace_pressure": 28.7,
    "wall_temp_upper": 805.2,
    "wall_temp_mid": 798.1,
    "wall_temp_lower": 792.3
  },
  "code": 0,
  "message": ""
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| time | str | ISO 时间戳 |
| minute_of_day | int | 当天分钟数（0-1439） |
| phase | str | 阶段名（heating/holding/cooling/unload） |
| phase_label | str | 阶段中文名 |
| core_temp | float | 核心温度（°C） |
| target_temp | float | 目标温度（°C） |
| fuel_flow | float | 燃料流量（m³/min） |
| air_flow | float | 空气流量（m³/min） |
| air_temp | float | 进风温度（°C） |
| furnace_pressure | float | 炉膛压力（Pa） |
| wall_temp_upper/mid/lower | float | 三区壁温（°C） |

---

### 7.4 获取历史数据

#### GET /api/furnace/history

**功能**：获取过去 60 分钟的历史数据（用于画曲线）

**响应示例**：

```json
{
  "data": {
    "timestamps": ["2026-05-01T02:20:00", ..., "2026-05-01T03:20:00"],
    "core_temp": [785.1, 786.2, ..., 789.5],
    "target_temp": [790.0, 790.0, ..., 790.0],
    "fuel_flow": [0.042, 0.043, ..., 0.043],
    "air_flow": [0.762, 0.763, ..., 0.764],
    "air_temp": [32.1, 32.3, ..., 32.5],
    "furnace_pressure": [28.2, 28.4, ..., 28.7],
    "wall_temp_upper": [804.8, 804.9, ..., 805.2],
    "wall_temp_mid": [797.8, 797.9, ..., 798.1],
    "wall_temp_lower": [792.1, 792.2, ..., 792.3],
    "minute_of_day": [140, 141, ..., 200]
  },
  "code": 0,
  "message": ""
}
```

---

### 7.5 获取预测与报警

#### GET /api/furnace/prediction

**功能**：获取未来 10 分钟的温度预测 + 报警状态 + 控制建议

**响应示例（正常情况）**：

```json
{
  "data": {
    "timestamps": ["2026-05-01T03:21:00", ..., "2026-05-01T03:30:00"],
    "predictions": [789.6, 789.7, ..., 790.1],
    "phase": "holding",
    "phase_label": "保温阶段",
    "alarm": {
      "alarmed": false,
      "max_temp": 790.1,
      "min_temp": 789.5,
      "upper_limit": 805.0,
      "lower_limit": 775.0,
      "message": "[正常] 保温阶段，预测温度 789.5-790.1°C (上限:805.0°C, 下限:775.0°C)",
      "current_fuel": 0.043,
      "current_air": 0.764,
      "suggested_fuel": null,
      "suggested_air": null
    }
  },
  "code": 0,
  "message": ""
}
```

**响应示例（报警情况）**：

```json
{
  "data": {
    "timestamps": ["2026-05-01T01:30:00", ..., "2026-05-01T01:40:00"],
    "predictions": [795.0, 802.0, 812.0, ..., 825.0],
    "phase": "heating",
    "phase_label": "升温阶段",
    "alarm": {
      "alarmed": true,
      "max_temp": 825.0,
      "min_temp": 795.0,
      "upper_limit": 810.0,
      "lower_limit": null,
      "max_at_minute": 10,
      "overshoot": 15.0,
      "direction": "上限",
      "message": "预测 t+10 分钟温度 825.0°C，超出上限 15.0°C (限:810.0°C)",
      "current_fuel": 0.26,
      "current_air": 3.11,
      "suggested_fuel": 0.18,
      "fuel_adjust": -0.08,
      "suggested_air": 2.24,
      "air_adjust": -0.87
    }
  },
  "code": 0,
  "message": ""
}
```

**alarm 字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| alarmed | bool | 是否报警 |
| max_temp | float | 预测最高温度 |
| min_temp | float | 预测最低温度 |
| upper_limit | float\|null | 报警上限 |
| lower_limit | float\|null | 报警下限 |
| max_at_minute | int | 最高温度出现在第几分钟（仅报警时） |
| overshoot | float | 超出阈值量（仅报警时） |
| direction | str | "上限"/"下限"/"双限"/"回温"（仅报警时） |
| message | str | 报警/正常消息 |
| current_fuel/air | float | 当前燃料/空气流量 |
| suggested_fuel/air | float\|null | 建议燃料/空气流量（仅报警时） |
| fuel_adjust/air_adjust | float\|null | 调整量（仅报警时） |

---

### 7.6 获取阶段信息

#### GET /api/furnace/phases

**功能**：获取各阶段的时间边界

**响应示例**：

```json
{
  "data": {
    "phases": [
      { "key": "heating", "label": "升温阶段", "start": 0, "end": 200 },
      { "key": "holding", "label": "保温阶段", "start": 200, "end": 600 },
      { "key": "cooling", "label": "降温阶段", "start": 600, "end": 1200 },
      { "key": "unload", "label": "卸装料阶段", "start": 1200, "end": 1440 }
    ]
  },
  "code": 0,
  "message": ""
}
```

---

### 7.7 获取报警记录

#### GET /api/furnace/alarms

**功能**：获取历史报警记录，支持筛选

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| phase | str | 否 | 按阶段筛选（heating/holding/cooling/unload） |
| acknowledged | bool | 否 | 按确认状态筛选（true/false） |

**响应示例**：

```json
{
  "data": {
    "total": 5,
    "unacknowledged": 2,
    "records": [
      {
        "id": 1,
        "time": "2026-05-01T01:40:00",
        "minute_of_day": 100,
        "phase": "heating",
        "phase_label": "升温阶段",
        "direction": "上限",
        "max_temp": 825.0,
        "min_temp": 795.0,
        "upper_limit": 810.0,
        "lower_limit": null,
        "overshoot": 15.0,
        "max_at_minute": 10,
        "current_temp": 789.0,
        "target_temp": 790.0,
        "current_fuel": 0.26,
        "current_air": 3.11,
        "suggested_fuel": 0.18,
        "suggested_air": 2.24,
        "message": "预测 t+10 分钟温度 825.0°C，超出上限 15.0°C",
        "acknowledged": false
      },
      ...
    ]
  },
  "code": 0,
  "message": ""
}
```

---

### 7.8 确认单条报警

#### PUT /api/furnace/alarms/{id}/acknowledge

**功能**：确认单条报警（acknowledged 设为 true）

**路径参数**：

| 参数 | 类型 | 说明 |
|------|------|------|
| id | int | 报警 ID |

**响应示例**：

```json
{
  "data": null,
  "code": 0,
  "message": "已确认"
}
```

---

### 7.9 确认所有报警

#### PUT /api/furnace/alarms/acknowledge-all

**功能**：确认所有未确认报警

**响应示例**：

```json
{
  "data": { "count": 5 },
  "code": 0,
  "message": "已确认 5 条报警"
}
```

---

## 8. 报警检测逻辑

### 8.1 报警阈值配置

各阶段的报警阈值（`furnace_service.py`）：

| 阶段 | 上限 | 下限 |
|------|------|------|
| heating | 810.0 °C | 无 |
| holding | target_temp + 15.0 °C | target_temp - 15.0 °C |
| cooling | current_temp + 10.0 °C（回温报警） | 无 |
| unload | 无 | 无 |

### 8.2 报警检测步骤

```
1. 取预测窗口 [t+1, t+10] 的温度
2. 计算 max_pred = max(预测值)，min_pred = min(预测值)
3. 根据阶段确定 upper_limit / lower_limit
4. 检测：
   - 若 max_pred > upper_limit → 上限报警
   - 若 min_pred < lower_limit → 下限报警
5. 若报警：
   - 计算超出量 overshoot
   - 生成控制建议
   - 记录报警
```

### 8.3 控制建议生成

#### 8.3.1 升温阶段

如果预测超温，建议降低燃料：

```python
overshoot = max_pred - upper_limit
fuel_reduction = min(current_fuel, overshoot / 100 * 0.3 + 0.05)
suggested_fuel = current_fuel - fuel_reduction
suggested_air = current_air - fuel_reduction * AIR_FUEL_RATIO
```

#### 8.3.2 保温阶段

- 若超温 → 建议燃料 -3% 额定值
- 若欠温 → 建议燃料 +3% 额定值

#### 8.3.3 降温阶段

若发生异常回温，建议燃料减半：

```python
suggested_fuel = current_fuel * 0.5
```

---

## 9. 后台线程与实时数据写入

### 9.1 后台数据更新线程

服务启动后会启动一个后台线程，每 4 秒执行一次：

```python
def _update_data_loop(self):
    while self.running:
        with self.data_lock:
            # 1. 滑动窗口更新数据（模拟时间流逝）
            current_index += 1
            if current_index >= len(full_data):
                current_index = INPUT_WINDOW  # 循环

            # 2. 用当前窗口做预测
            preds, phase = _predict_with_phase(...)

            # 3. 检查报警
            alarm = _check_alarm(...)
            if alarm['alarmed'] and not recently:
                alarm_records.append(...)

            # 4. 更新缓存供 API 使用
            current_data = ...
            self.predictions = preds
            self.alarm_result = alarm

        # 5. 写入外部实时数据库（RTDB）
        _write_rtdata(latest_data)

        time.sleep(4.0)  # 每 4 秒更新
```

### 9.2 外部实时数据库写入

系统会将实时数据写入外部 RTDB（实时数据库），地址配置：

```python
RTDATA_SERVER = "http://10.0.2.30:6811"
```

写入的点位：

| 点位 | 说明 | 倍率 |
|------|------|------|
| 100:EQ_001.AI_001.PV | fuel_flow | 1000 |
| 101:EQ_001.AI_001.PV | air_flow | 1000 |
| 102:EQ_001.AI_001.PV | air_temp | 1 |
| 103:EQ_001.AI_001.PV | wall_temp_upper | 1 |
| 104:EQ_001.AI_001.PV | wall_temp_mid | 1 |
| 111:EQ_001.AI_001.PV | wall_temp_lower | 1 |
| 107:EQ_001.AO_001.PV | core_temp | 1 |

写入接口：`POST /v1/rtdata/node/write`

---

## 10. 配置文件完整说明

### config/config.yaml

```yaml
server:
  host: "0.0.0.0"
  port: 8080
  debug: true

database:
  url: "postgresql+asyncpg://postgres:050811@127.0.0.1:5432/furnace"
  echo: false
  pool_size: 10
  max_overflow: 20

external_services:
  realtime:
    base_url: "http://localhost:8000"
    timeout: 30.0
  history:
    base_url: "http://localhost:8001"
    timeout: 30.0

model:
  heating_model_path: "heating_bilstm.pth"
  heating_feat_scaler_path: "heating_feat_scaler.pkl"
  heating_target_scaler_path: "heating_target_scaler.pkl"
  cooling_model_path: "cooling_bilstm.pth"
  cooling_feat_scaler_path: "cooling_feat_scaler.pkl"
  cooling_target_scaler_path: "cooling_target_scaler.pkl"
  holding_model_path: "holding_bilstm.pth"
  holding_feat_scaler_path: "holding_feat_scaler.pkl"
  holding_target_scaler_path: "holding_target_scaler.pkl"

alarm:
  core_temp_threshold: 810.0

logging:
  level: "INFO"
  file_path: "logs/app.log"
  rotation: "10 MB"
  retention: "7 days"
```

---

## 11. 数据流程总览

### 11.1 训练数据流（离线）

```
1. simulation.py 生成 7 天仿真数据
   ↓
2. 存入 PostgreSQL (sensor_data 表)
   ↓
3. heating.py / holding.py / cooling.py 分别训练
   ├─ 从 DB 读取对应阶段数据
   ├─ 注入故障增强数据
   ├─ 训练 Bi-LSTM 模型
   └─ 保存 *.pth + *.pkl
```

### 11.2 运行时数据流（在线）

```
服务启动
   ↓
加载 3 个模型 + scaler
   ↓
生成完整仿真周期数据（full_data）
   ↓
启动后台线程
   ├─ 每 4 秒滑动窗口
   ├─ 选择阶段模型预测
   ├─ 检测报警
   ├─ 更新缓存
   └─ 写入 RTDB
   ↓
API 访问
   └─ 从缓存读取数据返回
```

---

## 12. 部署与运维

### 12.1 Ubuntu 打包部署

见 `BUILD_UBUNTU.md` 文档。

**部署目录结构建议**：

```
/opt/furnace-backend/
├── furnace_backend              # 二进制可执行文件
├── config/
│   └── config.yaml              # 生产配置
├── heating_bilstm.pth           # 模型文件
├── heating_feat_scaler.pkl
├── heating_target_scaler.pkl
├── cooling_bilstm.pth
├── ...
├── logs/                        # 日志目录
│   └── app.log
└── data/                        # 数据目录（可选）
```

### 12.2 Systemd 服务配置

创建 `/etc/systemd/system/furnace-backend.service`：

```ini
[Unit]
Description=Furnace Backend Service
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/furnace-backend
ExecStart=/opt/furnace-backend/furnace_backend
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

**操作命令**：

```bash
# 重载配置
sudo systemctl daemon-reload

# 启用开机自启
sudo systemctl enable furnace-backend

# 启动服务
sudo systemctl start furnace-backend

# 查看状态
sudo systemctl status furnace-backend

# 查看日志
sudo journalctl -u furnace-backend -f
```

### 12.3 日志管理

- 日志文件位置：`logs/app.log`
- 轮转：10 MB 或每天
- 保留：7 天
- 压缩：ZIP

### 12.4 监控建议

- **进程监控**：systemd auto-restart
- **端口监控**：8080 可访问
- **日志监控**：ERROR 级别告警
- **业务监控**：
  - API 响应时间
  - 报警频率
  - RTDB 写入失败率

---

## 13. 扩展开发指南

### 13.1 添加新的 API 接口

1. 在 `app/api/` 下新建路由文件（或在 `furnace.py` 追加）
2. 在 `app/api/__init__.py` 中注册到 `api_router`
3. 在 `app/core/response.py` 定义响应模型（如需）
4. 在 `app/services/` 实现业务逻辑

### 13.2 接入真实传感器数据

当前使用的是仿真数据。要接入真实数据：

1. 实现从 PLC/DCS 读取传感器的函数
2. 替换 `FurnaceService._generate_initial_data()`
3. 替换 `_update_data_loop()` 中的滑动逻辑，改为从实时数据源读取
4. 保留预测和报警逻辑不变

### 13.3 调整报警阈值

在 `furnace_service.py` 中修改 `ALARM_LIMITS`：

```python
ALARM_LIMITS = {
    'heating': {'upper': 810.0, 'lower': None},
    'holding': {
        'upper': lambda target: target + 15.0,
        'lower': lambda target: target - 15.0
    },
    'cooling': {'upper': lambda current: current + 10.0, ...},
    ...
}
```

---

## 14. 常见问题（FAQ）

### Q1: 打包后找不到配置文件/模型文件？

A: 确保所有文件都在二进制同级目录，配置中的路径是相对于二进制的相对路径。

### Q2: PyTorch 太大，打包后几百 MB？

A: 安装 CPU 版本的 PyTorch，不要安装 CUDA 版本：

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### Q3: RTDB 写入失败？

A: 检查网络连通性，确认 `RTDATA_SERVER` 地址配置正确。

### Q4: 如何接入真实历史数据而不是仿真？

A: 修改 `heating.py` / `cooling.py` / `holding.py` 的数据加载部分，从你的历史数据源读取。

### Q5: 报警太频繁/不灵敏？

A: 调整 `ALARM_LIMITS` 中的阈值，或调整预测窗口/horizon。

---

## 附录

### A. 符号对照表

| 符号 | 含义 | 单位 |
|------|------|------|
| m | 工件质量 | kg |
| Cp | 比热容 | J/(kg·K) |
| A | 换热面积 | m² |
| h | 对流换热系数 | W/(m²·K) |
| ε | 发射率 | - |
| σ | Stefan-Boltzmann 常数 | 5.67e-8 W/(m²·K⁴) |
| T_gas | 炉气温度 | °C |
| T_wall | 壁温 | °C |
| T_core | 核心温度 | °C |
| Q_conv | 对流换热量 | W |
| Q_rad | 辐射换热量 | W |

### B. 参考资料

- FastAPI 文档：https://fastapi.tiangolo.com/
- PyTorch LSTM：https://pytorch.org/docs/stable/generated/torch.nn.LSTM.html
- SQLAlchemy 2.0：https://docs.sqlalchemy.org/en/20/
- 传热学基本原理

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2026-06-01 | 初始版本 |

---

**文档结束**
