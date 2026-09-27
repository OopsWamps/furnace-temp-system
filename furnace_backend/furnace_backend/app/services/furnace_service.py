"""
退火炉业务逻辑：模型加载、数据模拟、预测和报警
"""
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import joblib
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import requests
from app.core import settings

# 配置
INPUT_WINDOW = 60
PREDICT_HORIZON = 10
DEVICE = torch.device('cpu')

# 阶段时间边界（分钟/天）
PHASE_HEATING_END = 200
PHASE_HOLDING_END = 600
PHASE_COOLING_END = 1200
PHASE_UNLOAD_END = 1440

PHASE_LABELS = {
    'heating': '升温阶段',
    'holding': '保温阶段',
    'cooling': '降温阶段',
    'unload': '卸装料阶段',
}

# 各阶段报警上下限 (°C)
ALARM_LIMITS = {
    'heating': {'upper': 810.0, 'lower': None},
    'holding': {
        'upper': lambda target: target + 15.0,
        'lower': lambda target: target - 15.0
    },
    'cooling': {
        'upper': lambda current: current + 10.0,
        'lower': None
    },
    'unload': {'upper': None, 'lower': None}
}

SENSOR_COLS = [
    'fuel_flow', 'air_flow', 'air_temp',
    'furnace_pressure',
    'wall_temp_upper', 'wall_temp_mid', 'wall_temp_lower'
]

RTDATA_SERVER = "http://10.0.2.30:6811"
RTDATA_POINTS = [
    ("100:EQ_001.AI_001.PV", "fuel_flow", "燃料流量", 1000),
    ("101:EQ_001.AI_001.PV", "air_flow", "空气流量", 1000),
    ("102:EQ_001.AI_001.PV", "air_temp", "进风温度", 1),
    ("103:EQ_001.AI_001.PV", "wall_temp_upper", "上区炉壁温度", 1),
    ("104:EQ_001.AI_001.PV", "wall_temp_mid", "中区炉壁温度", 1),
    ("111:EQ_001.AI_001.PV", "wall_temp_lower", "下区炉壁温度", 1),
    ("107:EQ_001.AO_001.PV", "core_temp", "核心温度", 1),
]

# 物理常量（从 simulation.py 复制）
MASS = 10000.0
AREA = 50.0
EMISSIVITY = 0.85
SIGMA = 5.67e-8
RATED_FUEL_FLOW = 2.0
AIR_FUEL_RATIO = 10.8
T_AMBIENT = 25.0
DT = 60.0


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


def cp(temp):
    return 500.0 + 0.5 * temp


def heat_transfer_coeff(air_flow):
    return 10.0 + 5.0 * (air_flow / 10.0)


def rk4_step(t_core, t_gas, t_wall, air_flow, mass, area, dt):
    def dTdt(T):
        h_conv = heat_transfer_coeff(air_flow)
        q_conv = h_conv * area * (t_gas - T)
        q_rad = EMISSIVITY * SIGMA * area * ((t_wall + 273.15)**4 - (T + 273.15)**4)
        c_p = cp(T)
        return (q_conv + q_rad) / (mass * c_p) * dt

    k1 = dTdt(t_core)
    k2 = dTdt(t_core + 0.5 * k1)
    k3 = dTdt(t_core + 0.5 * k2)
    k4 = dTdt(t_core + k3)
    return t_core + (k1 + 2 * k2 + 2 * k3 + k4) / 6.0


class FurnaceService:
    def __init__(self):
        self.models = {}
        self.current_data = None
        self.predictions = None
        self.alarm_result = None
        self.current_phase = 'heating'
        self.full_data = None
        self.current_index = INPUT_WINDOW
        self.data_lock = threading.Lock()
        self.running = False
        self.alarm_records: list[dict] = []
        self._last_alarm_time: str | None = None

        # 加载模型
        self._load_models()
        # 生成初始数据
        self._generate_initial_data()
        # 启动后台线程
        self._start_background_thread()

    def _load_models(self):
        """加载三阶段预测模型"""
        logger.info("加载三阶段预测模型...")
        base_path = settings.BASE_DIR

        for phase in ['heating', 'holding', 'cooling']:
            try:
                if phase == 'heating':
                    model_path = base_path / settings.HEATING_MODEL_PATH
                    scaler_path = base_path / settings.HEATING_FEAT_SCALER_PATH
                    target_scaler_path = base_path / settings.HEATING_TARGET_SCALER_PATH
                elif phase == 'cooling':
                    model_path = base_path / settings.COOLING_MODEL_PATH
                    scaler_path = base_path / settings.COOLING_FEAT_SCALER_PATH
                    target_scaler_path = base_path / settings.COOLING_TARGET_SCALER_PATH
                else:  # holding
                    model_path = base_path / settings.HOLDING_MODEL_PATH
                    scaler_path = base_path / settings.HOLDING_FEAT_SCALER_PATH
                    target_scaler_path = base_path / settings.HOLDING_TARGET_SCALER_PATH

                feat_scaler = joblib.load(scaler_path)
                target_scaler = joblib.load(target_scaler_path)
                n_features = len(SENSOR_COLS) + 1
                model = BiLSTMPredictor(
                    input_size=n_features, hidden_size=48, num_layers=2,
                    output_size=PREDICT_HORIZON, dropout=0.1
                ).to(DEVICE)
                model.load_state_dict(torch.load(model_path, map_location=DEVICE, weights_only=True))
                model.eval()

                self.models[phase] = (model, feat_scaler, target_scaler)
                logger.info(f"  {phase} 模型加载成功")
            except Exception as e:
                logger.warning(f"  {phase} 模型加载失败: {e}")

    def _generate_initial_data(self):
        """生成完整退火周期（含故障场景）"""
        logger.info("生成模拟数据...")
        rng = np.random.RandomState(77)
        n_minutes = 1440
        t_core = np.zeros(n_minutes)
        t_core[0] = T_AMBIENT
        fuel_flow = np.zeros(n_minutes)
        air_flow = np.zeros(n_minutes)
        air_temp_arr = np.zeros(n_minutes)
        pressure_arr = np.zeros(n_minutes)
        wall_upper = np.zeros(n_minutes)
        wall_mid = np.zeros(n_minutes)
        wall_lower = np.zeros(n_minutes)
        target = np.zeros(n_minutes)

        # 目标曲线（升温段故障：目标设错为860°C）
        t_heat = 790.0
        t_fault_heat = 860.0
        t_cool1 = 700.0
        t_cool2 = 200.0

        for i in range(n_minutes):
            if i < PHASE_HEATING_END:
                frac = (i + 1) / PHASE_HEATING_END
                target[i] = T_AMBIENT + (t_fault_heat - T_AMBIENT) * (frac ** 0.8)
            elif i < PHASE_HOLDING_END:
                target[i] = t_heat + rng.uniform(-2, 2)
            elif i < PHASE_COOLING_END:
                frac = (i - PHASE_HOLDING_END + 1) / (PHASE_COOLING_END - PHASE_HOLDING_END)
                if i < 950:
                    target[i] = t_heat - (t_heat - t_cool1) * ((i - PHASE_HOLDING_END + 1) / (950 - PHASE_HOLDING_END))
                else:
                    target[i] = t_cool1 - (t_cool1 - t_cool2) * ((i - 950 + 1) / (PHASE_COOLING_END - 950)) ** 1.5
            else:
                target[i] = T_AMBIENT

        # 控制逻辑（升温段注入故障：目标设错860°C + 燃料偏高50%）
        for i in range(n_minutes):
            if i < PHASE_HEATING_END:
                t_frac = np.clip((t_core[i] - T_AMBIENT) / (860.0 - T_AMBIENT), 0, 1)
                fuel = RATED_FUEL_FLOW * (0.20 + 0.30 * t_frac) * 1.50
            elif i < PHASE_HOLDING_END:
                fuel = RATED_FUEL_FLOW * 0.15
            elif i < 950:
                fuel = RATED_FUEL_FLOW * 0.04
            elif i < PHASE_COOLING_END:
                fuel = RATED_FUEL_FLOW * 0.01
            else:
                fuel = 0.0

            fuel = max(0.0, fuel)
            fuel_flow[i] = fuel
            air_flow[i] = max(0.1, fuel * AIR_FUEL_RATIO + 0.3 + rng.normal(0, 0.03))
            air_temp_arr[i] = T_AMBIENT + 5.0 * (fuel / RATED_FUEL_FLOW) + rng.normal(0, 0.3)
            pressure_arr[i] = 12.0 + 25.0 * (fuel / RATED_FUEL_FLOW) + rng.normal(0, 1.0)
            wall_upper[i] = target[i] + 15 + rng.normal(0, 1.5)
            wall_mid[i] = target[i] + 8 + rng.normal(0, 1.2)
            wall_lower[i] = target[i] + 2 + rng.normal(0, 1.2)

            if i < n_minutes - 1:
                t_gas = (wall_upper[i] + wall_mid[i] + wall_lower[i]) / 3.0
                t_core[i + 1] = rk4_step(
                    t_core=t_core[i], t_gas=t_gas, t_wall=t_gas,
                    air_flow=air_flow[i], mass=MASS, area=AREA, dt=DT
                )

        t_core += rng.normal(0, 0.8, n_minutes)
        fuel_flow = np.maximum(fuel_flow + rng.normal(0, 0.008, n_minutes), 0)

        start_time = datetime(2026, 5, 6, 0, 0, 0)
        timestamps = [start_time + timedelta(minutes=i) for i in range(n_minutes)]

        self.full_data = pd.DataFrame({
            'time_stamp': timestamps,
            'fuel_flow': np.round(fuel_flow, 4),
            'air_flow': np.round(air_flow, 4),
            'air_temp': np.round(air_temp_arr, 2),
            'furnace_pressure': np.round(pressure_arr, 2),
            'wall_temp_upper': np.round(wall_upper, 2),
            'wall_temp_mid': np.round(wall_mid, 2),
            'wall_temp_lower': np.round(wall_lower, 2),
            'target_temp': np.round(target, 2),
            'core_temp': np.round(t_core, 2),
        })
        self.full_data['minute_of_day'] = np.arange(n_minutes) % 1440
        logger.info("模拟数据生成完成")

    def _get_phase(self, minute_of_day):
        """根据分钟数判定阶段"""
        if minute_of_day < PHASE_HEATING_END:
            return 'heating'
        elif minute_of_day < PHASE_HOLDING_END:
            return 'holding'
        elif minute_of_day < PHASE_COOLING_END:
            return 'cooling'
        else:
            return 'unload'

    def _write_rtdata(self, latest):
        url = f"{RTDATA_SERVER}/v1/rtdata/node/write"
        data = []
        for node_id, column, _, scale in RTDATA_POINTS:
            value = float(latest[column])
            write_value = int(round(value * scale)) if scale > 1 else round(value, 2)
            data.append({"nodeId": node_id, "value": write_value})

        try:
            result = requests.post(url, json={"data": data}, timeout=3).json()
            if result.get("code") != 0:
                logger.warning(f"实时库写入失败: {result}")
                return

            results = result.get("results", result.get("data", []))
            for (node_id, _, label, _), code in zip(RTDATA_POINTS, results):
                if code != 0:
                    logger.warning(f"实时库写入失败: {node_id} ({label}), code={code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"实时库写入异常: {e}")

    def _predict_with_phase(self, df_window, minute_of_day):
        """根据当前阶段选择对应模型预测"""
        phase = self._get_phase(minute_of_day)

        if phase == 'unload' or phase not in self.models:
            return np.full(PREDICT_HORIZON, df_window['core_temp'].iloc[-1]), phase

        model, feat_scaler, target_scaler = self.models[phase]
        feature_cols = SENSOR_COLS + ['target_temp']
        features = np.zeros((INPUT_WINDOW, len(feature_cols)), dtype=np.float32)
        for i, col in enumerate(feature_cols):
            features[:, i] = df_window[col].values[-INPUT_WINDOW:]

        features_scaled = feat_scaler.transform(features)
        x = torch.FloatTensor(features_scaled).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            pred_scaled = model(x).cpu().numpy()
        preds = target_scaler.inverse_transform(pred_scaled).flatten()
        return preds, phase

    def _check_alarm(self, preds, current_fuel, current_air, phase, current_temp, target_temp):
        """检查是否超限，返回报警信息和调整建议"""
        max_pred = np.max(preds)
        min_pred = np.min(preds)
        max_idx = np.argmax(preds)
        min_idx = np.argmin(preds)

        limits = ALARM_LIMITS[phase]
        upper_limit = None
        lower_limit = None

        if limits['upper'] is not None:
            if callable(limits['upper']):
                if phase == 'holding':
                    upper_limit = limits['upper'](target_temp)
                elif phase == 'cooling':
                    upper_limit = limits['upper'](current_temp)
            else:
                upper_limit = limits['upper']

        if limits['lower'] is not None:
            if callable(limits['lower']):
                if phase == 'holding':
                    lower_limit = limits['lower'](target_temp)
            else:
                lower_limit = limits['lower']

        upper_alarm = (upper_limit is not None) and (max_pred > upper_limit)
        lower_alarm = (lower_limit is not None) and (min_pred < lower_limit)
        alarmed = upper_alarm or lower_alarm

        if not alarmed:
            msg = f'[正常] {PHASE_LABELS[phase]}，预测温度 {min_pred:.1f}~{max_pred:.1f}°C'
            if upper_limit is not None:
                msg += f' (上限:{upper_limit:.1f}°C)'
            if lower_limit is not None:
                msg += f' (下限:{lower_limit:.1f}°C)'
            return {
                'alarmed': False, 'max_temp': float(max_pred), 'min_temp': float(min_pred),
                'upper_limit': float(upper_limit) if upper_limit else None,
                'lower_limit': float(lower_limit) if lower_limit else None,
                'message': msg,
                'current_fuel': float(current_fuel), 'current_air': float(current_air),
                'suggested_fuel': None, 'suggested_air': None
            }

        suggested_fuel = None
        suggested_air = None
        fuel_adj = 0.0
        air_adj = 0.0
        direction = ''
        alarm_msg = ''

        if phase == 'heating':
            overshoot = max_pred - upper_limit
            fuel_reduction = min(current_fuel, overshoot / 100 * 0.3 + 0.05)
            suggested_fuel = max(0.0, current_fuel - fuel_reduction)
            air_reduction = fuel_reduction * AIR_FUEL_RATIO
            suggested_air = max(0.1, current_air - air_reduction)
            direction = '上限'
            alarm_msg = f'预测 t+{max_idx+1} 分钟温度 {max_pred:.1f}°C，超出{direction} {overshoot:.1f}°C (限:{upper_limit:.1f}°C)'
            return {
                'alarmed': True, 'max_temp': float(max_pred), 'min_temp': float(min_pred),
                'upper_limit': float(upper_limit) if upper_limit else None,
                'lower_limit': float(lower_limit) if lower_limit else None,
                'max_at_minute': int(max_idx + 1), 'overshoot': float(overshoot),
                'direction': direction,
                'current_fuel': float(current_fuel), 'current_air': float(current_air),
                'suggested_fuel': float(suggested_fuel), 'fuel_adjust': float(-fuel_reduction),
                'suggested_air': float(suggested_air), 'air_adjust': float(-air_reduction),
                'message': alarm_msg
            }

        elif phase == 'holding':
            if upper_alarm and lower_alarm:
                deviation = max(max_pred - upper_limit, lower_limit - min_pred)
                direction = '双限'
            elif upper_alarm:
                deviation = max_pred - upper_limit
                direction = '上限'
            else:
                deviation = lower_limit - min_pred
                direction = '下限'

            if upper_alarm:
                fuel_adj = -RATED_FUEL_FLOW * 0.03
                alarm_msg = f'预测温度 {max_pred:.1f}°C 超出{direction} {deviation:.1f}°C (限:{upper_limit:.1f}°C)'
            else:
                fuel_adj = RATED_FUEL_FLOW * 0.03
                alarm_msg = f'预测温度 {min_pred:.1f}°C 低于{direction} {deviation:.1f}°C (限:{lower_limit:.1f}°C)'

            suggested_fuel = max(0.0, current_fuel + fuel_adj)
            air_adj = fuel_adj * AIR_FUEL_RATIO
            suggested_air = max(0.1, current_air + air_adj)

            return {
                'alarmed': True, 'max_temp': float(max_pred), 'min_temp': float(min_pred),
                'upper_limit': float(upper_limit) if upper_limit else None,
                'lower_limit': float(lower_limit) if lower_limit else None,
                'max_at_minute': int(max_idx + 1) if upper_alarm else int(min_idx + 1),
                'overshoot': float(deviation), 'direction': direction,
                'current_fuel': float(current_fuel), 'current_air': float(current_air),
                'suggested_fuel': float(suggested_fuel), 'fuel_adjust': float(fuel_adj),
                'suggested_air': float(suggested_air), 'air_adjust': float(air_adj),
                'message': alarm_msg
            }

        else:
            overshoot = max_pred - upper_limit
            fuel_reduction = min(current_fuel, current_fuel * 0.5)
            suggested_fuel = max(0.0, current_fuel - fuel_reduction)
            air_reduction = fuel_reduction * AIR_FUEL_RATIO
            suggested_air = max(0.1, current_air - air_reduction)
            return {
                'alarmed': True, 'max_temp': float(max_pred), 'min_temp': float(min_pred),
                'upper_limit': float(upper_limit) if upper_limit else None,
                'lower_limit': float(lower_limit) if lower_limit else None,
                'max_at_minute': int(max_idx + 1), 'overshoot': float(overshoot),
                'direction': '回温',
                'current_fuel': float(current_fuel), 'current_air': float(current_air),
                'suggested_fuel': float(suggested_fuel), 'fuel_adjust': float(-fuel_reduction),
                'suggested_air': float(suggested_air), 'air_adjust': float(-air_reduction),
                'message': f'降温异常回温！预测温度 {max_pred:.1f}°C，超上限 {overshoot:.1f}°C (限:{upper_limit:.1f}°C)'
            }

    def _update_data_loop(self):
        """后台数据更新循环"""
        while self.running:
            latest = None
            with self.data_lock:
                window_df = self.full_data.iloc[self.current_index - INPUT_WINDOW:self.current_index].copy()

                minute = window_df['minute_of_day'].iloc[-1]
                phase = self._get_phase(minute)
                self.current_phase = phase

                preds, _ = self._predict_with_phase(window_df, minute)

                current_fuel = window_df['fuel_flow'].iloc[-1]
                current_air = window_df['air_flow'].iloc[-1]
                current_temp = window_df['core_temp'].iloc[-1]
                target_temp = window_df['target_temp'].iloc[-1]

                alarm = self._check_alarm(preds, current_fuel, current_air, phase, current_temp, target_temp)

                # 记录报警
                if alarm['alarmed']:
                    current_time = window_df['time_stamp'].iloc[-1].isoformat()
                    if self._last_alarm_time != current_time:
                        self._last_alarm_time = current_time
                        self.alarm_records.append({
                            'id': len(self.alarm_records) + 1,
                            'time': current_time,
                            'minute_of_day': int(window_df['minute_of_day'].iloc[-1]),
                            'phase': phase,
                            'phase_label': PHASE_LABELS.get(phase, ''),
                            'direction': alarm.get('direction', ''),
                            'max_temp': alarm['max_temp'],
                            'min_temp': alarm['min_temp'],
                            'upper_limit': alarm.get('upper_limit'),
                            'lower_limit': alarm.get('lower_limit'),
                            'overshoot': alarm.get('overshoot'),
                            'max_at_minute': alarm.get('max_at_minute'),
                            'current_temp': float(current_temp),
                            'target_temp': float(target_temp),
                            'current_fuel': alarm['current_fuel'],
                            'current_air': alarm['current_air'],
                            'suggested_fuel': alarm.get('suggested_fuel'),
                            'suggested_air': alarm.get('suggested_air'),
                            'message': alarm['message'],
                            'acknowledged': False,
                        })
                else:
                    self._last_alarm_time = None

                self.current_data = window_df
                self.predictions = preds
                self.alarm_result = alarm
                latest = window_df.iloc[-1].copy()

                self.current_index += 1
                if self.current_index >= len(self.full_data) - PREDICT_HORIZON:
                    self.current_index = INPUT_WINDOW

            if latest is not None:
                self._write_rtdata(latest)

            time.sleep(4.0)

    def _start_background_thread(self):
        """启动后台线程"""
        self.running = True
        thread = threading.Thread(target=self._update_data_loop, daemon=True)
        thread.start()
        logger.info("后台数据更新线程已启动")

    def get_current(self):
        """获取当前传感器数据"""
        with self.data_lock:
            if self.current_data is None:
                return None
            latest = self.current_data.iloc[-1]
            return {
                'time': latest['time_stamp'].isoformat(),
                'minute_of_day': int(latest['minute_of_day']),
                'phase': self.current_phase,
                'phase_label': PHASE_LABELS.get(self.current_phase, ''),
                'core_temp': float(latest['core_temp']),
                'target_temp': float(latest['target_temp']),
                'fuel_flow': float(latest['fuel_flow']),
                'air_flow': float(latest['air_flow']),
                'air_temp': float(latest['air_temp']),
                'furnace_pressure': float(latest['furnace_pressure']),
                'wall_temp_upper': float(latest['wall_temp_upper']),
                'wall_temp_mid': float(latest['wall_temp_mid']),
                'wall_temp_lower': float(latest['wall_temp_lower'])
            }

    def get_history(self):
        """获取历史数据"""
        with self.data_lock:
            if self.current_data is None:
                return None
            return {
                'timestamps': [ts.isoformat() for ts in self.current_data['time_stamp'].tolist()],
                'core_temp': self.current_data['core_temp'].tolist(),
                'target_temp': self.current_data['target_temp'].tolist(),
                'fuel_flow': self.current_data['fuel_flow'].tolist(),
                'air_flow': self.current_data['air_flow'].tolist(),
                'air_temp': self.current_data['air_temp'].tolist(),
                'furnace_pressure': self.current_data['furnace_pressure'].tolist(),
                'wall_temp_upper': self.current_data['wall_temp_upper'].tolist(),
                'wall_temp_mid': self.current_data['wall_temp_mid'].tolist(),
                'wall_temp_lower': self.current_data['wall_temp_lower'].tolist(),
                'minute_of_day': self.current_data['minute_of_day'].tolist()
            }

    def get_prediction(self):
        """获取预测数据"""
        with self.data_lock:
            if self.current_data is None or self.predictions is None or self.alarm_result is None:
                return None
            last_time = self.current_data['time_stamp'].iloc[-1]
            pred_times = [(last_time + timedelta(minutes=i+1)).isoformat()
                          for i in range(PREDICT_HORIZON)]
            return {
                'timestamps': pred_times,
                'predictions': self.predictions.tolist(),
                'phase': self.current_phase,
                'phase_label': PHASE_LABELS.get(self.current_phase, ''),
                'alarm': self.alarm_result
            }

    def get_phases(self):
        """获取阶段信息"""
        return {
            'phases': [
                {'key': 'heating', 'label': '升温阶段', 'start': 0, 'end': PHASE_HEATING_END},
                {'key': 'holding', 'label': '保温阶段', 'start': PHASE_HEATING_END, 'end': PHASE_HOLDING_END},
                {'key': 'cooling', 'label': '降温阶段', 'start': PHASE_HOLDING_END, 'end': PHASE_COOLING_END},
                {'key': 'unload', 'label': '卸装料阶段', 'start': PHASE_COOLING_END, 'end': PHASE_UNLOAD_END},
            ]
        }

    def get_alarm_records(self, phase: str | None = None, acknowledged: bool | None = None):
        """获取报警记录"""
        with self.data_lock:
            records = self.alarm_records.copy()
        if phase:
            records = [r for r in records if r['phase'] == phase]
        if acknowledged is not None:
            records = [r for r in records if r['acknowledged'] == acknowledged]
        total = len(records)
        unacknowledged = sum(1 for r in records if not r['acknowledged'])
        return {
            'total': total,
            'unacknowledged': unacknowledged,
            'records': records
        }

    def acknowledge_alarm(self, alarm_id: int):
        """确认报警"""
        with self.data_lock:
            for r in self.alarm_records:
                if r['id'] == alarm_id:
                    r['acknowledged'] = True
                    return True
        return False

    def acknowledge_all_alarms(self):
        """确认全部报警"""
        with self.data_lock:
            count = 0
            for r in self.alarm_records:
                if not r['acknowledged']:
                    r['acknowledged'] = True
                    count += 1
            return count
