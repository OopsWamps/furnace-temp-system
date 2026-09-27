"""
加热阶段Bi-LSTM模型训练 (优化版)
仅使用每天0-210分钟的升温数据
改进: 时间特征 + 目标温度特征 + 按周期分集 + 减小模型
"""
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sqlalchemy import create_engine
from datetime import datetime, timedelta
import joblib

DB_URL = "postgresql+psycopg2://postgres:050811@127.0.0.1:5432/furnace"

INPUT_WINDOW = 60
PREDICT_HORIZON = 10
BATCH_SIZE = 16
HIDDEN_SIZE = 48
NUM_LAYERS = 2
DROPOUT = 0.1
LEARNING_RATE = 8e-4
EPOCHS = 300
DEVICE = torch.device('cpu')


SENSOR_COLS = [
    'fuel_flow', 'air_flow', 'air_temp',
    'furnace_pressure',
    'wall_temp_upper', 'wall_temp_mid', 'wall_temp_lower'
]
TARGET_COL = 'core_temp'

MODEL_PATH = 'heating_bilstm.pth'
SCALER_PATH = 'heating_feat_scaler.pkl'
TARGET_SCALER_PATH = 'heating_target_scaler.pkl'


class FurnaceDataset(Dataset):
    def __init__(self, features, targets, input_window, predict_horizon):
        self.features = features
        self.targets = targets
        self.input_window = input_window
        self.predict_horizon = predict_horizon
        self.n_samples = len(features) - input_window - predict_horizon + 1

    def __len__(self):
        return max(0, self.n_samples)

    def __getitem__(self, idx):
        x = self.features[idx: idx + self.input_window]
        y = self.targets[idx + self.input_window:
                         idx + self.input_window + self.predict_horizon]
        return torch.FloatTensor(x), torch.FloatTensor(y)


class BiLSTMPredictor(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size, dropout):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size, hidden_size=hidden_size,
            num_layers=num_layers, batch_first=True, bidirectional=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_size * 2, 32),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(32, output_size)
        )

    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        last_hidden = lstm_out[:, -1, :]
        return self.fc(last_hidden)


from simulation import (
    MASS, AREA, EMISSIVITY, SIGMA,
    RATED_FUEL_FLOW, AIR_FUEL_RATIO, T_AMBIENT, DT,
    cp, heat_transfer_coeff, rk4_step
)


def generate_fault_heating_cycle(rng, n_minutes=210, fault_target=860, fuel_mult=1.50):
    """用物理模型生成一个故障加热周期：高目标温度 + 高燃料"""

    t_core = np.zeros(n_minutes)
    t_core[0] = T_AMBIENT + rng.uniform(-2, 2)
    fuel_arr = np.zeros(n_minutes)
    air_arr = np.zeros(n_minutes)
    air_t_arr = np.zeros(n_minutes)
    press_arr = np.zeros(n_minutes)
    wall_u = np.zeros(n_minutes)
    wall_m = np.zeros(n_minutes)
    wall_l = np.zeros(n_minutes)
    target = np.zeros(n_minutes)

    for i in range(n_minutes):
        frac = (i + 1) / 200 if i < 200 else 1.0
        target[i] = T_AMBIENT + (fault_target - T_AMBIENT) * (frac ** 0.8)
        if i >= 200:
            target[i] = fault_target + rng.uniform(-2, 2)

        t_frac = np.clip((t_core[i] - T_AMBIENT) / (fault_target - T_AMBIENT), 0, 1)
        fuel = RATED_FUEL_FLOW * (0.20 + 0.30 * t_frac) * fuel_mult
        fuel_arr[i] = max(0.0, fuel)
        air_arr[i] = max(0.1, fuel_arr[i] * AIR_FUEL_RATIO + 0.3 + rng.normal(0, 0.03))
        air_t_arr[i] = T_AMBIENT + 5.0 * (fuel_arr[i] / RATED_FUEL_FLOW) + rng.normal(0, 0.3)
        press_arr[i] = 12.0 + 25.0 * (fuel_arr[i] / RATED_FUEL_FLOW) + rng.normal(0, 1.0)
        wall_u[i] = target[i] + 15 + rng.normal(0, 1.5)
        wall_m[i] = target[i] + 8 + rng.normal(0, 1.2)
        wall_l[i] = target[i] + 2 + rng.normal(0, 1.2)

        if i < n_minutes - 1:
            t_gas = (wall_u[i] + wall_m[i] + wall_l[i]) / 3.0
            t_core[i + 1] = rk4_step(
                t_core=t_core[i], t_gas=t_gas, t_wall=t_gas,
                air_flow=air_arr[i], mass=MASS, area=AREA, dt=DT
            )

    t_core += rng.normal(0, 0.8, n_minutes)
    fuel_arr = np.maximum(fuel_arr + rng.normal(0, 0.008, n_minutes), 0)

    start_time = datetime(2026, 5, 1, 0, 0, 0)
    timestamps = [start_time + timedelta(minutes=i) for i in range(n_minutes)]

    return pd.DataFrame({
        'time_stamp': timestamps,
        'fuel_flow': np.round(fuel_arr, 4),
        'air_flow': np.round(air_arr, 4),
        'air_temp': np.round(air_t_arr, 2),
        'furnace_pressure': np.round(press_arr, 2),
        'wall_temp_upper': np.round(wall_u, 2),
        'wall_temp_mid': np.round(wall_m, 2),
        'wall_temp_lower': np.round(wall_l, 2),
        'target_temp': np.round(target, 2),
        'core_temp': np.round(t_core, 2),
    })


def load_heating_data():
    print("从数据库加载数据，筛选加热阶段（每天0-210分钟）...")
    engine = create_engine(DB_URL)
    df = pd.read_sql(f"SELECT * FROM sensor_data ORDER BY time_stamp", engine)
    df['time_stamp'] = pd.to_datetime(df['time_stamp'])
    df['minute_of_day'] = df['time_stamp'].dt.hour * 60 + df['time_stamp'].dt.minute
    df['cycle'] = df.index // 1440

    mask = df['minute_of_day'] <= 210
    df_heat = df[mask].copy()

    # 生成6组故障场景混入训练（多样化目标温度+燃料倍数）
    print("生成故障增强数据（目标810-860°C，燃料偏高20-50%）...")
    fault_configs = [
        (810, 1.20), (820, 1.30), (830, 1.35),
        (840, 1.40), (850, 1.45), (860, 1.50),
    ]
    fault_cycles = []
    for i, (ft, fm) in enumerate(fault_configs):
        rng = np.random.RandomState(200 + i)
        fc = generate_fault_heating_cycle(rng, n_minutes=210, fault_target=ft, fuel_mult=fm)
        fc['cycle'] = 100 + i
        fault_cycles.append(fc)
        print(f"  故障周期{i}: 目标={ft}°C, 燃料={fm:.2f}x, "
              f"T_core {fc['core_temp'].min():.0f}~{fc['core_temp'].max():.0f}°C")

    # 故障数据重复3倍以平衡正常/故障比例
    fault_oversampled = pd.concat(fault_cycles * 3, ignore_index=True)
    df_heat = pd.concat([df_heat] + [fault_oversampled], ignore_index=True)
    n_normal = len(df_heat) - len(fault_oversampled)
    print(f"加热阶段总计: {len(df_heat)} 条 (正常:{n_normal}, 故障x3:{len(fault_oversampled)}), "
          f"核心温度 {df_heat['core_temp'].min():.0f}~{df_heat['core_temp'].max():.0f}°C")
    return df_heat


def prepare_data(df):
    feature_cols = SENSOR_COLS + ['target_temp']
    print(f"特征列: {feature_cols}")
    print(f"(不使用时间特征，以保证故障场景泛化)")

    features = df[feature_cols].values.astype(np.float32)
    targets = df[TARGET_COL].values.astype(np.float32)

    feat_scaler = StandardScaler()
    target_scaler = StandardScaler()

    features_scaled = feat_scaler.fit_transform(features)
    targets_scaled = target_scaler.fit_transform(targets.reshape(-1, 1)).flatten()

    joblib.dump(feat_scaler, SCALER_PATH)
    joblib.dump(target_scaler, TARGET_SCALER_PATH)
    print(f"特征维度: {features_scaled.shape[1]}")
    print(f"目标范围: {targets.min():.1f} ~ {targets.max():.1f} °C")
    return features_scaled, targets_scaled, feat_scaler, target_scaler, len(feature_cols)


def create_dataloaders(df, features, targets):
    """按周期分集: 正常0-4+故障周期训练, 正常5验证, 正常6测试"""
    cycles = df['cycle'].values
    # 故障周期(>=100)全部进训练集
    train_mask = (cycles < 5) | (cycles >= 100)
    val_mask = cycles == 5
    test_mask = cycles == 6

    train_idx = np.where(train_mask)[0]
    val_idx = np.where(val_mask)[0]
    test_idx = np.where(test_mask)[0]

    def make_loader(idx_array, shuffle):
        # 提取该子集在特征数组中的连续区间
        if len(idx_array) == 0:
            return None
        start, end = idx_array[0], idx_array[-1] + 1
        ds = FurnaceDataset(features[start:end], targets[start:end],
                            INPUT_WINDOW, PREDICT_HORIZON)
        return DataLoader(ds, batch_size=BATCH_SIZE, shuffle=shuffle, drop_last=True)

    train_loader = make_loader(train_idx, True)
    val_loader = make_loader(val_idx, False)
    test_loader = make_loader(test_idx, False)

    n_train = train_loader.dataset.n_samples if train_loader else 0
    n_val = val_loader.dataset.n_samples if val_loader else 0
    n_test = test_loader.dataset.n_samples if test_loader else 0
    print(f"样本 (按周期): 训练={n_train}, 验证={n_val}, 测试={n_test}")
    return train_loader, val_loader, test_loader


def train_epoch(model, loader, criterion, optimizer):
    model.train()
    total_loss, n = 0, 0
    for x, y in loader:
        x, y = x.to(DEVICE), y.to(DEVICE)
        optimizer.zero_grad()
        loss = criterion(model(x), y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        total_loss += loss.item()
        n += 1
    return total_loss / max(n, 1)


def evaluate(model, loader, criterion):
    model.eval()
    total_loss, n = 0, 0
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(DEVICE), y.to(DEVICE)
            total_loss += criterion(model(x), y).item()
            n += 1
    return total_loss / max(n, 1)


def train():
    print("=" * 55)
    print("加热阶段 Bi-LSTM 模型训练 (优化版)")
    print(f"设备: {DEVICE} | 窗口: {INPUT_WINDOW}min | 预测: {PREDICT_HORIZON}min")
    print("=" * 55)

    df = load_heating_data()
    features, targets, feat_scaler, target_scaler, n_features = prepare_data(df)
    train_loader, val_loader, test_loader = create_dataloaders(df, features, targets)

    model = BiLSTMPredictor(
        input_size=n_features, hidden_size=HIDDEN_SIZE,
        num_layers=NUM_LAYERS, output_size=PREDICT_HORIZON, dropout=DROPOUT
    ).to(DEVICE)
    print(f"参数量: {sum(p.numel() for p in model.parameters()):,}")

    criterion = nn.HuberLoss(delta=1.0)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
        optimizer, T_0=40, T_mult=2, eta_min=1e-5)

    best_val_loss = float('inf')
    patience_counter = 0
    early_stop_patience = 35

    print(f"\n开始训练 (max {EPOCHS} epochs)...")
    for epoch in range(1, EPOCHS + 1):
        train_loss = train_epoch(model, train_loader, criterion, optimizer)
        val_loss = evaluate(model, val_loader, criterion)
        scheduler.step(epoch)

        if val_loss < best_val_loss - 1e-7:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), MODEL_PATH)
        else:
            patience_counter += 1

        if epoch % 20 == 0 or epoch <= 5:
            lr = optimizer.param_groups[0]['lr']
            print(f"  Epoch {epoch:3d} | Train: {train_loss:.6f} | "
                  f"Val: {val_loss:.6f} | LR: {lr:.2e} | patience: {patience_counter}")

        if patience_counter >= early_stop_patience:
            print(f"  早停 @ epoch {epoch}")
            break

    # 测试
    print("\n加载最佳模型测试...")
    model.load_state_dict(torch.load(MODEL_PATH, weights_only=True))
    test_loss = evaluate(model, test_loader, criterion)

    model.eval()
    all_preds, all_targets = [], []
    with torch.no_grad():
        for x, y in test_loader:
            x = x.to(DEVICE)
            all_preds.append(model(x).cpu().numpy())
            all_targets.append(y.numpy())

    preds = np.concatenate(all_preds, axis=0)
    targets_np = np.concatenate(all_targets, axis=0)
    preds_real = target_scaler.inverse_transform(preds)
    targets_real = target_scaler.inverse_transform(targets_np)

    mae = np.mean(np.abs(preds_real - targets_real))
    rmse = np.sqrt(np.mean((preds_real - targets_real)**2))
    r2 = 1 - np.sum((targets_real - preds_real)**2) / np.sum((targets_real - targets_real.mean())**2)

    print(f"\n=== 测试集结果 ===")
    print(f"Huber Loss (归一化): {test_loss:.6f}")
    print(f"MAE:  {mae:.2f} °C")
    print(f"RMSE: {rmse:.2f} °C")
    print(f"R2:   {r2:.4f}")

    print(f"\n各预测步 MAE / RMSE:")
    for i in range(PREDICT_HORIZON):
        step_mae = np.mean(np.abs(preds_real[:, i] - targets_real[:, i]))
        step_rmse = np.sqrt(np.mean((preds_real[:, i] - targets_real[:, i])**2))
        print(f"  t+{i+1:2d} min: MAE={step_mae:.2f}°C  RMSE={step_rmse:.2f}°C")

    print(f"\n模型: {MODEL_PATH}  |  scaler: {SCALER_PATH}")
    return model, feat_scaler, target_scaler


if __name__ == '__main__':
    train()
