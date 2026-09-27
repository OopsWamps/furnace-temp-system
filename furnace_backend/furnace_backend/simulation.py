"""
退火炉物理模型与数据模拟
模拟7天（10080分钟）的球化退火工艺传感器数据
基于能量平衡方程，使用RK4求解工件核心温度
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# ============================================================
# 物理常数与炉体参数
# ============================================================
MASS = 5000.0              # 工件质量 kg
AREA = 15.0                # 有效换热面积 m²
EMISSIVITY = 0.85          # 综合发射率
SIGMA = 5.67e-8            # 斯特藩-玻尔兹曼常数 W/(m²·K⁴)
GAS_CALORIFIC = 35e6       # 天然气热值 J/Nm³
RATED_GAS_DAY = 2500.0     # 额定气耗 Nm³/day
FURNACE_VOLUME = 3.5 * 2.5 * 2.0  # 炉膛容积 m³
AIR_FUEL_RATIO = 10.8      # 空燃比
THERMAL_EFFICIENCY = 0.30  # 热效率

# 额定燃料流量 Nm³/min
RATED_FUEL_FLOW = RATED_GAS_DAY / (24 * 60)

# 时间参数
TOTAL_MINUTES = 7 * 24 * 60  # 7天 = 10080分钟
DT = 60.0                     # 时间步长 秒

# 噪声标准差
NOISE_TEMP = 1.5       # 温度噪声 °C
NOISE_FLOW = 0.02      # 流量噪声 Nm³/min
NOISE_PRESSURE = 2.0   # 压力噪声 Pa
NOISE_AIR_TEMP = 0.8   # 进风温度噪声 °C

# 初始环境温度
T_AMBIENT = 25.0


def cp(T):
    """比热容 J/(kg·K)，T单位°C"""
    return 460.0 + 0.2 * T


def heat_transfer_coeff(air_flow):
    """
    对流换热系数 h，与进风流量正相关
    h = 20 + 60 * (air_flow / max_air_flow)
    air_flow: Nm³/min
    """
    max_air = RATED_FUEL_FLOW * AIR_FUEL_RATIO * 1.2  # 最大进风量
    ratio = np.clip(air_flow / max_air, 0, 1)
    return 20.0 + 60.0 * ratio


def generate_target_profile():
    """
    生成7天的目标温度工艺曲线（球化退火循环）
    每天:
      00:00-20:00 (1200分钟) 退火工艺：升温->均热->慢冷->快冷
      20:00-24:00 (240分钟)  开炉卸料/装料，无加热，自然冷却
    """
    target = np.zeros(TOTAL_MINUTES)
    cycle_len = 24 * 60          # 1440分钟/天
    process_len = 20 * 60        # 1200分钟工艺时间
    unload_len = 4 * 60          # 240分钟卸装料时间
    num_cycles = TOTAL_MINUTES // cycle_len

    for c in range(num_cycles):
        offset = c * cycle_len
        rng = np.random.RandomState(42 + c)
        t_heat = 790 + rng.uniform(-10, 10)
        t_cool1 = 700 + rng.uniform(-5, 5)
        t_cool2 = 200 + rng.uniform(-20, 20)

        # 工艺阶段时间分配（共1200分钟）
        dt_heat = 200              # 升温 0-200 min
        dt_hold = 400              # 均热 200-600 min
        dt_slow = 350              # 慢冷 600-950 min
        dt_fast = process_len - dt_heat - dt_hold - dt_slow  # 快冷 950-1200 min

        t_start = T_AMBIENT + rng.uniform(-3, 3)
        idx = offset

        # ---- 00:00-20:00 退火工艺 ----
        # 升温
        for i in range(dt_heat):
            if idx + i >= TOTAL_MINUTES:
                break
            frac = (i + 1) / dt_heat
            target[idx + i] = t_start + (t_heat - t_start) * (frac ** 0.8)
        idx += dt_heat
        # 均热
        for i in range(dt_hold):
            if idx + i >= TOTAL_MINUTES:
                break
            target[idx + i] = t_heat + rng.uniform(-2, 2)
        idx += dt_hold
        # 慢冷
        for i in range(dt_slow):
            if idx + i >= TOTAL_MINUTES:
                break
            frac = (i + 1) / dt_slow
            target[idx + i] = t_heat - (t_heat - t_cool1) * frac
        idx += dt_slow
        # 快冷
        for i in range(dt_fast):
            if idx + i >= TOTAL_MINUTES:
                break
            frac = (i + 1) / dt_fast
            target[idx + i] = t_cool1 - (t_cool1 - t_cool2) * (frac ** 1.5)
        idx += dt_fast

        # ---- 20:00-24:00 开炉卸装料 ----
        # 目标温度设为环境温度（炉门打开，自然冷却）
        for i in range(unload_len):
            if idx + i >= TOTAL_MINUTES:
                break
            target[idx + i] = T_AMBIENT

    return target


def compute_control(t_target, t_core, minute_of_day, rng):
    """
    基于工艺阶段的时间驱动控制逻辑。
    minute_of_day: 0-1439 当天分钟数
    """
    error = t_target - t_core

    if minute_of_day < 200:
        # 升温阶段：温度越高辐射散热(T⁴)越大，燃料需随温度上升
        t_frac = np.clip((t_core - T_AMBIENT) / (800 - T_AMBIENT), 0, 1)
        fuel = RATED_FUEL_FLOW * (0.20 + 0.30 * t_frac)
    elif minute_of_day < 600:
        # 保温阶段：稳定燃料维持温度  0.25 Nm³/min
        fuel = RATED_FUEL_FLOW * 0.15
    elif minute_of_day < 950:
        # 慢冷阶段：降低燃料，缓慢降温  0.07 Nm³/min
        fuel = RATED_FUEL_FLOW * 0.04
    elif minute_of_day < 1200:
        # 快冷阶段：几乎无燃料  0.017 Nm³/min
        fuel = RATED_FUEL_FLOW * 0.01
    else:
        # 卸装料阶段：无加热
        fuel = 0.0

    fuel = max(0.0, fuel)

    # 进风流量
    base_air = 0.3
    air_flow = fuel * AIR_FUEL_RATIO + base_air + rng.normal(0, 0.03)
    air_flow = max(0.1, air_flow)

    # 进风温度
    air_temp = T_AMBIENT + 5.0 * (fuel / RATED_FUEL_FLOW) + rng.normal(0, NOISE_AIR_TEMP)

    # 炉膛压力
    pressure = 12.0 + 25.0 * (fuel / RATED_FUEL_FLOW) + rng.normal(0, NOISE_PRESSURE)

    return fuel, air_flow, air_temp, pressure


def wall_temperature(target):
    """
    三区炉壁温度（上/中/下）
    壁温略高于目标温度（加热时）或略低于目标温度（冷却时）
    """
    wall_upper = np.zeros(TOTAL_MINUTES)
    wall_mid = np.zeros(TOTAL_MINUTES)
    wall_lower = np.zeros(TOTAL_MINUTES)

    for i in range(TOTAL_MINUTES):
        t = target[i]
        # 上部壁温略高，下部略低（热气上升）
        wall_upper[i] = t + 15 + np.random.normal(0, 2.0)
        wall_mid[i] = t + 8 + np.random.normal(0, 1.5)
        wall_lower[i] = t + 2 + np.random.normal(0, 1.5)

    return wall_upper, wall_mid, wall_lower


def rk4_step(t_core, t_gas, t_wall, air_flow, mass, area, dt):
    """
    四阶龙格-库塔法求解一步核心温度变化
    dT/dt = (Q_conv + Q_rad) / (m * Cp)

    t_core: 核心温度 °C
    t_gas: 炉气温度 °C (取壁温均值近似)
    t_wall: 平均壁温 °C
    air_flow: 进风流量 Nm³/min
    dt: 时间步长 秒
    """

    def dTdt(T):
        # 对流换热
        h = heat_transfer_coeff(air_flow)
        Q_conv = h * area * (t_gas - T)

        # 辐射换热（需转开尔文）
        T_core_K = T + 273.15
        T_wall_K = t_wall + 273.15
        Q_rad = SIGMA * EMISSIVITY * area * (T_wall_K**4 - T_core_K**4)

        return (Q_conv + Q_rad) / (mass * cp(T))

    k1 = dTdt(t_core)
    k2 = dTdt(t_core + 0.5 * dt * k1)
    k3 = dTdt(t_core + 0.5 * dt * k2)
    k4 = dTdt(t_core + dt * k3)

    return t_core + (dt / 6.0) * (k1 + 2*k2 + 2*k3 + k4)


def run_simulation():
    """运行完整7天模拟（闭环控制：控制信号与RK4同步迭代）"""
    print("开始生成目标温度曲线...")
    target = generate_target_profile()

    # 初始化数组
    t_core_arr = np.zeros(TOTAL_MINUTES)
    t_core_arr[0] = T_AMBIENT
    fuel_flow = np.zeros(TOTAL_MINUTES)
    air_flow = np.zeros(TOTAL_MINUTES)
    air_temp = np.zeros(TOTAL_MINUTES)
    pressure = np.zeros(TOTAL_MINUTES)

    print("生成壁温数据...")
    wall_upper, wall_mid, wall_lower = wall_temperature(target)

    rng = np.random.RandomState(123)

    # 第0分钟的控制信号
    fuel_flow[0], air_flow[0], air_temp[0], pressure[0] = \
        compute_control(target[0], t_core_arr[0], 0, rng)

    print("RK4求解核心温度（闭环控制 + 能量平衡方程）...")
    for i in range(1, TOTAL_MINUTES):
        # 根据当前核心温度实时计算控制信号（闭环）
        fuel_flow[i], air_flow[i], air_temp[i], pressure[i] = \
            compute_control(target[i], t_core_arr[i-1], i % 1440, rng)

        # 炉气温度取三区壁温均值
        t_gas = (wall_upper[i-1] + wall_mid[i-1] + wall_lower[i-1]) / 3.0
        t_wall_avg = (wall_upper[i-1] + wall_mid[i-1] + wall_lower[i-1]) / 3.0

        t_core_arr[i] = rk4_step(
            t_core=t_core_arr[i-1],
            t_gas=t_gas,
            t_wall=t_wall_avg,
            air_flow=air_flow[i],
            mass=MASS,
            area=AREA,
            dt=DT
        )

        if i % 2000 == 0:
            print(f"  分钟 {i}/{TOTAL_MINUTES}, T_core={t_core_arr[i]:.1f}°C, "
                  f"fuel={fuel_flow[i]:.4f} Nm3/min")

    # 添加传感器噪声
    print("添加传感器噪声...")
    t_core_noisy = t_core_arr + np.random.normal(0, NOISE_TEMP, TOTAL_MINUTES)
    fuel_flow_noisy = np.maximum(fuel_flow + np.random.normal(0, NOISE_FLOW, TOTAL_MINUTES), 0)
    air_flow_noisy = np.maximum(air_flow + np.random.normal(0, NOISE_FLOW * 1.5, TOTAL_MINUTES), 0.05)
    pressure_noisy = pressure + np.random.normal(0, NOISE_PRESSURE, TOTAL_MINUTES)
    air_temp_noisy = air_temp + np.random.normal(0, NOISE_AIR_TEMP, TOTAL_MINUTES)

    # 构建时间序列
    print("构建DataFrame...")
    start_time = datetime(2026, 4, 21, 0, 0, 0)
    timestamps = [start_time + timedelta(minutes=i) for i in range(TOTAL_MINUTES)]

    df = pd.DataFrame({
        'time_stamp': timestamps,
        'fuel_flow': np.round(fuel_flow_noisy, 4),           # Nm³/min
        'air_flow': np.round(air_flow_noisy, 4),             # Nm³/min
        'air_temp': np.round(air_temp_noisy, 2),             # °C
        'furnace_pressure': np.round(pressure_noisy, 2),     # Pa
        'wall_temp_upper': np.round(wall_upper, 2),          # °C
        'wall_temp_mid': np.round(wall_mid, 2),              # °C
        'wall_temp_lower': np.round(wall_lower, 2),          # °C
        'target_temp': np.round(target, 2),                  # °C (工艺设定)
        'core_temp': np.round(t_core_noisy, 2),              # °C (工件核心温度)
    })

    # 数据验证
    print("\n=== 数据统计 ===")
    print(f"总记录数: {len(df)}")
    print(f"时间范围: {df['time_stamp'].min()} ~ {df['time_stamp'].max()}")
    print(f"\n核心温度: {df['core_temp'].min():.1f} ~ {df['core_temp'].max():.1f} °C")
    print(f"燃料流量: {df['fuel_flow'].min():.4f} ~ {df['fuel_flow'].max():.4f} Nm3/min")
    print(f"进风流量: {df['air_flow'].min():.4f} ~ {df['air_flow'].max():.4f} Nm3/min")
    print(f"炉膛压力: {df['furnace_pressure'].min():.1f} ~ {df['furnace_pressure'].max():.1f} Pa")

    # 验证辐射主导（700°C以上区间）
    high_temp_mask = df['core_temp'] > 700
    if high_temp_mask.any():
        print(f"\n700°C以上数据占比: {high_temp_mask.mean()*100:.1f}%")
        # 计算该区间的Q_rad/Q_conv比值（采样验证）
        samples = df[high_temp_mask].iloc[::100]
        ratios = []
        for _, row in samples.iterrows():
            h = heat_transfer_coeff(row['air_flow'])
            Q_conv = h * AREA * (row['wall_temp_mid'] - row['core_temp'])
            T_c = row['core_temp'] + 273.15
            T_w = row['wall_temp_mid'] + 273.15
            Q_rad = SIGMA * EMISSIVITY * AREA * (T_w**4 - T_c**4)
            if abs(Q_conv) > 1e-6:
                ratios.append(abs(Q_rad / Q_conv))
        if ratios:
            print(f"700°C以上 |Q_rad/Q_conv| 均值: {np.mean(ratios):.1f} (应 > 1 表示辐射主导)")

    return df


if __name__ == '__main__':
    df = run_simulation()
    df.to_csv('sensor_data.csv', index=False)
    print(f"\n数据已保存至 sensor_data.csv ({len(df)} 条记录)")
