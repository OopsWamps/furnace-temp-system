import request from './request'

export interface SensorData {
  time: string
  minute_of_day: number
  phase: string
  phase_label: string
  core_temp: number
  target_temp: number
  fuel_flow: number
  air_flow: number
  air_temp: number
  furnace_pressure: number
  wall_temp_upper: number
  wall_temp_mid: number
  wall_temp_lower: number
}

export interface HistoryData {
  timestamps: string[]
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

export interface AlarmInfo {
  alarmed: boolean
  max_temp: number
  min_temp: number
  upper_limit: number | null
  lower_limit: number | null
  message: string
  current_fuel: number
  current_air: number
  suggested_fuel: number | null
  suggested_air: number | null
  overshoot?: number
  direction?: string
  max_at_minute?: number
}

export interface PredictionData {
  timestamps: string[]
  predictions: number[]
  phase: string
  phase_label: string
  alarm: AlarmInfo
}

export const getCurrent = (): Promise<SensorData> => {
  return request.get('/furnace/current')
}

export const getHistory = (): Promise<HistoryData> => {
  return request.get('/furnace/history')
}

export const getPrediction = (): Promise<PredictionData> => {
  return request.get('/furnace/prediction')
}

export const getPhases = (): Promise<any> => {
  return request.get('/furnace/phases')
}
