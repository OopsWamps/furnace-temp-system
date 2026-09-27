# Ubuntu 环境打包为二进制可执行文件 - 详细步骤

## 目录

1. [准备工作](#准备工作)
2. [方法一：自动构建脚本（推荐）](#方法一自动构建脚本推荐)
3. [方法二：手动构建](#方法二手动构建)
4. [运行二进制文件](#运行二进制文件)
5. [部署到其他 Ubuntu 机器](#部署到其他-ubuntu-机器)
6. [常见问题排查](#常见问题排查)

---

## 准备工作

### 1. 系统要求

- **Ubuntu 版本**: 20.04 LTS 或更高版本
- **Python 版本**: 3.10 至 3.12
- **内存**: 至少 4GB（推荐 8GB）
- **磁盘空间**: 至少 5GB 可用空间

### 2. 检查系统环境

```bash
# 检查 Ubuntu 版本
lsb_release -a

# 检查 Python 版本
python3 --version

# 检查可用磁盘空间
df -h
```

### 3. 安装系统依赖

```bash
# 更新包列表
sudo apt update

# 安装必要的系统库
sudo apt install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    build-essential \
    libssl-dev \
    libffi-dev \
    git \
    curl \
    wget
```

### 4. 将项目文件传输到 Ubuntu

如果你当前在 Windows，有以下几种方式：

**方式 A: 使用 scp（推荐）**
```bash
# 在 Windows 的 PowerShell 或 Git Bash 中执行
scp -r /c/Users/timo/Desktop/furnace_backend user@ubuntu-server:/home/user/
```

**方式 B: 使用 U 盘/共享文件夹**
```bash
# 直接复制项目文件夹到 Ubuntu 系统中
```

**方式 C: 使用 Git（如果有仓库）**
```bash
git clone <your-repo-url> furnace_backend
cd furnace_backend
```

---

## 方法一：自动构建脚本（推荐）

### 步骤 1：进入项目目录

```bash
cd /path/to/furnace_backend
ls -la
```

确认以下文件存在：
- `main.py`
- `requirements.txt`
- `requirements-build.txt`
- `furnace_backend.spec`
- `build-ubuntu.sh`
- `config/config.yaml`
- `*.pth` 和 `*.pkl` 模型文件

### 步骤 2：给脚本添加执行权限

```bash
chmod +x build-ubuntu.sh
```

### 步骤 3：运行构建脚本

```bash
./build-ubuntu.sh
```

脚本会自动执行以下操作：
1. 检测可用的 Python 版本
2. 创建虚拟环境 `venv/`
3. 安装项目依赖
4. 安装 PyInstaller
5. 清理旧的构建文件
6. 执行打包
7. 输出构建结果

### 步骤 4：等待构建完成

构建过程可能需要 **5-15 分钟**，取决于你的网络和机器性能。

看到以下信息表示构建成功：

```
=====================================
  构建完成!
=====================================
二进制文件位置: dist/furnace_backend
```

---

## 方法二：手动构建

如果你想完全控制构建过程，可以按以下步骤操作。

### 步骤 1：进入项目目录

```bash
cd /path/to/furnace_backend
```

### 步骤 2：创建虚拟环境

```bash
# 检查 Python 版本
python3 --version

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

激活成功后，命令行提示符前会出现 `(venv)`。

### 步骤 3：升级 pip

```bash
pip install --upgrade pip
```

### 步骤 4：安装依赖

```bash
# 安装项目依赖 + PyInstaller
pip install -r requirements-build.txt
```

或者分开安装：

```bash
# 安装项目依赖
pip install -r requirements.txt

# 安装 PyInstaller
pip install pyinstaller
```

### 步骤 5：验证依赖安装

```bash
pip list
```

确保看到以下关键包：
- `fastapi`
- `uvicorn`
- `torch`
- `pandas`
- `numpy`
- `pyinstaller`

### 步骤 6：清理旧的构建文件

```bash
rm -rf build dist __pycache__
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

### 步骤 7：执行打包

```bash
pyinstaller --clean furnace_backend.spec
```

参数说明：
- `--clean`: 清理临时文件和缓存
- `furnace_backend.spec`: 使用我们配置好的 spec 文件

### 步骤 8：检查构建产物

```bash
ls -lh dist/
```

应该看到一个名为 `furnace_backend` 的二进制文件。

---

## 运行二进制文件

### 1. 测试运行

```bash
cd dist

# 查看文件大小
ls -lh furnace_backend

# 直接运行
./furnace_backend
```

### 2. 预期输出

```
INFO     | Loaded configuration from ...
INFO     | Starting furnace backend service...
INFO     | Service will run on 0.0.0.0:8080
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

### 3. 验证服务

打开浏览器或使用 curl 访问：

```bash
# 检查健康检查端点
curl http://localhost:8080/api/health

# 查看 API 文档
# 在浏览器中打开: http://localhost:8080/docs
```

### 4. 后台运行（生产环境）

```bash
cd dist

# 使用 nohup 后台运行
nohup ./furnace_backend > app.log 2>&1 &

# 或者使用 systemd 服务（见下文）
```

---

## 部署到其他 Ubuntu 机器

### 1. 打包部署文件

```bash
cd dist

# 创建部署包目录
mkdir -p furnace_deploy
cd furnace_deploy

# 复制二进制文件
cp ../furnace_backend .

# 复制配置文件
mkdir -p config
cp ../../config/config.yaml config/

# 复制模型文件
cp ../../*.pth .
cp ../../*.pkl .

# 创建日志目录
mkdir -p logs

# 返回上级并打包
cd ..
tar -czf furnace_backend_v1.0.tar.gz furnace_deploy/
```

### 2. 传输到目标机器

```bash
# 使用 scp 传输
scp furnace_backend_v1.0.tar.gz user@target-server:/home/user/
```

### 3. 在目标机器上解压运行

```bash
# 登录目标机器
ssh user@target-server

# 解压
cd /home/user
tar -xzf furnace_backend_v1.0.tar.gz
cd furnace_deploy

# 赋予执行权限
chmod +x furnace_backend

# 编辑配置文件（按需修改数据库连接等）
nano config/config.yaml

# 运行
./furnace_backend
```

### 4. 使用 systemd 管理服务（推荐）

创建服务文件：

```bash
sudo nano /etc/systemd/system/furnace-backend.service
```

写入以下内容（根据实际路径修改）：

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

# 环境变量
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

安装并启动服务：

```bash
# 创建应用目录
sudo mkdir -p /opt/furnace-backend
sudo cp -r furnace_deploy/* /opt/furnace-backend/
sudo chown -R www-data:www-data /opt/furnace-backend/

# 重新加载 systemd
sudo systemctl daemon-reload

# 启用并启动服务
sudo systemctl enable furnace-backend
sudo systemctl start furnace-backend

# 查看状态
sudo systemctl status furnace-backend

# 查看日志
sudo journalctl -u furnace-backend -f
```

---

## 常见问题排查

### 问题 1: PyTorch 安装失败

**症状**: pip install torch 超时或失败

**解决方案**:
```bash
# 使用国内镜像
pip install torch -i https://pypi.tuna.tsinghua.edu.cn/simple

# 或者指定 CPU 版本
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

### 问题 2: 构建后体积太大

**原因**: PyTorch 包含了 CUDA 库

**解决方案**: 确保安装的是 CPU 版本的 PyTorch

```bash
# 卸载当前 torch
pip uninstall torch torchvision torchaudio

# 安装 CPU-only 版本
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 问题 3: 运行时找不到模型文件

**症状**: FileNotFoundError 相关 .pth 或 .pkl 文件

**解决方案**:
```bash
# 检查文件结构
cd dist
ls -la

# 确保以下文件在同一目录:
# - furnace_backend
# - config/config.yaml
# - heating_bilstm.pth
# - heating_feat_scaler.pkl
# - heating_target_scaler.pkl
# - cooling_bilstm.pth
# - cooling_feat_scaler.pkl
# - cooling_target_scaler.pkl
# - holding_bilstm.pth
# - holding_feat_scaler.pkl
# - holding_target_scaler.pkl
```

### 问题 4: 数据库连接失败

**症状**: psycopg2 或 asyncpg 连接错误

**解决方案**:
```bash
# 编辑 config.yaml，确认数据库连接信息正确
nano dist/config/config.yaml

# 确保 PostgreSQL 服务正在运行
sudo systemctl status postgresql

# 如果需要安装 PostgreSQL
sudo apt install postgresql
```

### 问题 5: 端口被占用

**症状**: "Address already in use"

**解决方案**:
```bash
# 查找占用端口的进程
sudo lsof -i :8080
# 或
sudo netstat -tlnp | grep 8080

# 修改 config.yaml 中的端口号
nano dist/config/config.yaml
```

### 问题 6: 无法从外部访问

**症状**: 本地可以访问，但其他机器访问不了

**解决方案**:
```bash
# 检查防火墙
sudo ufw status

# 开放 8080 端口
sudo ufw allow 8080/tcp

# 确认 config.yaml 中 host 是 0.0.0.0
nano dist/config/config.yaml
```

### 问题 7: glibc 版本不兼容

**症状**: "version `GLIBC_2.32' not found"

**原因**: 在高版本 Ubuntu 上构建，在低版本上运行

**解决方案**: 在目标部署机器上重新构建，或者使用与目标机器相同版本的 Ubuntu 进行构建。

---

## 补充提示

### 1. 减小二进制体积

可以在 `furnace_backend.spec` 中排除不需要的模块：

```python
excludes=[
    'tkinter',
    'matplotlib',
    'IPython',
    'notebook',
    'pytest',
    'unittest',
]
```

### 2. 使用 UPX 压缩

在 `furnace_backend.spec` 中启用 UPX（需要先安装 UPX）：

```bash
sudo apt install upx
```

### 3. 日志轮转

确保 logs 目录有足够空间，定期清理旧日志。

---

## 获取帮助

如果遇到问题：

1. 查看本文档的"常见问题排查"部分
2. 检查日志文件：`tail -f logs/app.log`
3. 确认所有依赖都已正确安装
4. 验证配置文件格式正确（YAML 格式敏感）
