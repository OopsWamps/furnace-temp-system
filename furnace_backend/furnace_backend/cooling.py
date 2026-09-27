"""
降温阶段Bi-LSTM模型训练
仅使用每天600-1200分钟的降温数据（慢冷600-950 + 快冷950-1200）
故障增强：燃料未及时降低 / 冷却过慢 / 异常回温
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

MODEL_PATH = 'cooling_bilstm.pth'
SCALER_PATH = 'cooling_feat_scaler.pkl'
TARGET_SCALER_PATH = 'cooling_target_scaler.pkl'

# 降温阶段时间范围（当天分钟数）
COOL_START = 600
COOL_END = 1200
COOL_DURATION = COOL_END - COOL_START  # 600分钟

# 慢冷/快冷分界
SLOW_COOL_END = 950


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


def generate_fault_cooling_cycle(rng, fault_type='high_fuel',
                                 n_minutes=COOL_DURATION, **kwargs):
    """
    用物理模型生成一个故障降温周期
    fault_type:
      - 'high_fuel': 慢冷阶段燃料未降低，保持保温水平
      - 'slow_cool': 快冷阶段燃料偏高，降温速率不足
      - 'reheat': 降温中途异常回温（炉门密封故障）
    """
    fuel_mult = kwargs.get('fuel_mult', 1.0)
    reheat_minute = kwargs.get('reheat_minute', None)
    reheat_fuel = kwargs.get('reheat_fuel', 0.15)

    t_core = np.zeros(n_minutes)
    t_core[0] = 780.0 + rng.uniform(-5, 5)  # 降温起始温度约780°C
    fuel_arr = np.zeros(n_minutes)
    air_arr = np.zeros(n_minutes)
    air_t_arr = np.zeros(n_minutes)
    press_arr = np.zeros(n_minutes)
    wall_u = np.zeros(n_minutes)
    wall_m = np.zeros(n_minutes)
    wall_l = np.zeros(n_minutes)
    target = np.zeros(n_minutes)

    for i in range(n_minutes):
        minute_of_day = COOL_START + i

        # 正常降温目标曲线
        if minute_of_day < SLOW_COOL_END:
            # 慢冷：780 → 700°C
            frac = (i + 1) / (SLOW_COOL_END - COOL_START)
            target[i] = 780.0 - (780.0 - 700.0) * frac
        else:
            # 快冷：700 → 200°C
            frac = (minute_of_day - SLOW_COOL_END + 1) / (COOL_END - SLOW_COOL_END)
            target[i] = 700.0 - (700.0 - 200.0) * (frac ** 1.5)

        # 正常控制
        if minute_of_day < SLOW_COOL_END:
            fuel = RATED_FUEL_FLOW * 0.04
        else:
            fuel = RATED_FUEL_FLOW * 0.01

        # 注入故障
        if fault_type == 'high_fuel' and minute_of_day < SLOW_COOL_END:
            fuel = RATED_FUEL_FLOW * (0.04 + (0.15 - 0.04) * fuel_mult)
        elif fault_type == 'slow_cool' and minute_of_day >= SLOW_COOL_END:
            fuel = RATED_FUEL_FLOW * (0.01 + (0.06 - 0.01) * fuel_mult)
        elif fault_type == 'reheat' and reheat_minute is not None:
            # 在指定时刻附近（±30分钟）异常升温
            if abs(i - reheat_minute) < 30:
                ramp = 1.0 - abs(i - reheat_minute) / 30.0
                fuel = RATED_FUEL_FLOW * reheat_fuel * ramp

        fuel = max(0.0, fuel)
        fuel_arr[i] = fuel

        air_arr[i] = max(0.1, fuel * AIR_FUEL_RATIO + 0.3 + rng.normal(0, 0.03))
        air_t_arr[i] = T_AMBIENT + 5.0 * (fuel / RATED_FUEL_FLOW) + rng.normal(0, 0.3)
        press_arr[i] = 12.0 + 25.0 * (fuel / RATED_FUEL_FLOW) + rng.normal(0, 1.0)
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

    start_time = datetime(2026, 5, 1, COOL_START // 60, COOL_START % 60, 0)
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


def load_cooling_data():
    print("从数据库加载数据，筛选降温阶段（每天600-1200分钟）...")
    engine = create_engine(DB_URL)
    df = pd.read_sql(f"SELECT * FROM sensor_data ORDER BY time_stamp", engine)
    df['time_stamp'] = pd.to_datetime(df['time_stamp'])
    df['minute_of_day'] = df['time_stamp'].dt.hour * 60 + df['time_stamp'].dt.minute
    df['cycle'] = df.index // 1440

    mask = (df['minute_of_day'] >= COOL_START) & (df['minute_of_day'] < COOL_END)
    df_cool = df[mask].copy()
    df_cool = df_cool.reset_index(drop=True)

    # 重新标记cycle（按降温阶段连续段分组）
    df_cool['cycle'] = df_cool['time_stamp'].dt.date.astype('category').cat.codes

    print(f"正常降温数据: {len(df_cool)} 条, "
          f"核心温度 {df_cool['core_temp'].min():.0f}~{df_cool['core_temp'].max():.0f}°C")

    # 生成故障增强数据
    fault_configs = [
        ('high_fuel', {'fuel_mult': 0.3}),    # 慢冷燃料略偏高
        ('high_fuel', {'fuel_mult': 0.6}),    # 慢冷燃料中等偏高
        ('high_fuel', {'fuel_mult': 1.0}),    # 慢冷燃料大幅偏高（接近保温水平）
        ('slow_cool', {'fuel_mult': 0.3}),    # 快冷燃料略偏高
        ('slow_cool', {'fuel_mult': 0.7}),    # 快冷燃料明显偏高
        ('slow_cool', {'fuel_mult': 1.0}),    # 快冷燃料大幅偏高
        ('reheat',   {'reheat_minute': 200, 'reheat_fuel': 0.12}),  # 慢冷中途回温
        ('reheat',   {'reheat_minute': 400, 'reheat_fuel': 0.15}),  # 快冷初期回温
    ]

    print(f"生成 {len(fault_configs)} 组故障增强数据...")
    fault_cycles = []
    for i, (ftype, fparams) in enumerate(fault_configs):
        rng = np.random.RandomState(300 + i)
        fc = generate_fault_cooling_cycle(rng, fault_type=ftype, **fparams)
        fc['cycle'] = 100 + i
        fault_cycles.append(fc)
        label = f"{ftype}({', '.join(f'{k}={v}' for k, v in fparams.items())})"
        print(f"  故障{i}: {label}, "
              f"T_core {fc['core_temp'].min():.0f}~{fc['core_temp'].max():.0f}°C")

    # 故障数据重复3倍
    fault_oversampled = pd.concat(fault_cycles * 3, ignore_index=True)
    df_cool = pd.concat([df_cool] + [fault_oversampled], ignore_index=True)
    n_normal = len(df_cool) - len(fault_oversampled)
    print(f"降温阶段总计: {len(df_cool)} 条 (正常:{n_normal}, 故障x3:{len(fault_oversampled)}), "
          f"核心温度 {df_cool['core_temp'].min():.0f}~{df_cool['core_temp'].max():.0f}°C")
    return df_cool


def prepare_data(df):
    feature_cols = SENSOR_COLS + ['target_temp']
    print(f"特征列: {feature_cols}")

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
    """按周期分集: 正常前几个+故障周期训练, 验证/测试取正常周期"""
    cycles = df['cycle'].values
    unique_normal = sorted(set(cycles[cycles < 100]))

    if len(unique_normal) < 3:
        print(f"警告: 正常周期仅 {len(unique_normal)} 个，分集可能不充分")

    # 训练: 正常0~N-3 + 全部故障
    train_cycles = set(unique_normal[:-2]) if len(unique_normal) >= 3 else set(unique_normal)
    train_mask = np.isin(cycles, list(train_cycles)) | (cycles >= 100)
    val_cycle = unique_normal[-2] if len(unique_normal) >= 2 else unique_normal[-1]
    test_cycle = unique_normal[-1]
    val_mask = cycles == val_cycle
    test_mask = cycles == test_cycle

    train_idx = np.where(train_mask)[0]
    val_idx = np.where(val_mask)[0]
    test_idx = np.where(test_mask)[0]

    def make_loader(idx_array, shuffle):
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
    print("降温阶段 Bi-LSTM 模型训练")
    print(f"设备: {DEVICE} | 窗口: {INPUT_WINDOW}min | 预测: {PREDICT_HORIZON}min")
    print(f"降温范围: 每天 {COOL_START}-{COOL_END} 分钟")
    print("=" * 55)

    df = load_cooling_data()
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

    print(f"\n模型: {MODEL_PATH}  |  scaler: {SCALER_PATH}, {TARGET_SCALER_PATH}")
    return model, feat_scaler, target_scaler


if __name__ == '__main__':
    train()
