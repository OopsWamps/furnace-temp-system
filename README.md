# 退火炉全流程温度预测与报警系统

基于物理仿真 + 机器学习的退火炉温度监控系统：实时采集传感器数据，按升温 / 保温 / 降温三阶段分别用 Bi-LSTM 模型预测未来 10 分钟温度，超限前发出多级报警并给出控制建议。

## 功能特性

- 三阶段独立建模：按工艺周期自动切换升温 / 保温 / 降温三组 Bi-LSTM 预测模型
- 物理仿真生成训练数据，支持故障场景注入
- 实时预测未来 10 分钟温度曲线
- 多级报警阈值，附带控制建议
- 每 4 秒后台更新数据并写入外部实时数据库
- 后端可经 PyInstaller 打包为独立二进制部署

## 技术栈

| 层级 | 选型 |
|------|------|
| 后端框架 | FastAPI + Uvicorn |
| 前端 | Vue 3 |
| 数据库 | PostgreSQL + SQLAlchemy (async) |
| 机器学习 | PyTorch + Scikit-learn |
| 数据处理 | Pandas + NumPy |
| 配置 / 日志 | Pydantic Settings + YAML / Loguru |
| 打包 | PyInstaller |

## 目录结构

```
furnace_backend/     FastAPI 后端（API、服务层、三阶段模型 .pth 与 scaler）
furnace_frontend/    Vue 3 前端
BACKEND_TECHNICAL_DOCUMENTATION.md   后端技术文档（架构、模块、API、部署）
FRONTEND_TECHNICAL_DOCUMENTATION.md  前端技术文档
```

## 快速开始

后端：

```bash
cd furnace_backend/furnace_backend
pip install -r requirements.txt
python main.py
```

配置文件参考 `config/config.example.yaml`，复制为 `config.yaml` 后按环境修改数据库连接等参数。

前端：

```bash
cd furnace_frontend
npm install
npm run dev
```

## 文档

- [后端技术文档](BACKEND_TECHNICAL_DOCUMENTATION.md)：系统架构、核心模块、物理模型、API 接口、部署运维
- [前端技术文档](FRONTEND_TECHNICAL_DOCUMENTATION.md)
