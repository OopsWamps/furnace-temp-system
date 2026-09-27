<template>
  <div class="sensors-view">
    <div class="sensors-grid">
      <el-card v-for="sensor in sensorConfig" :key="sensor.id" class="sensor-card" shadow="hover" @click="openDialog(sensor)">
        <div class="sensor-header">
          <span class="sensor-icon">{{ sensor.icon }}</span>
          <span class="sensor-name">{{ getSensorLabel(sensor.id) }}</span>
          <span class="live-tag">LIVE</span>
        </div>
        <div class="sensor-value" :style="{ color: sensor.color }">
          {{ formatValue(sensor.id, currentData?.[sensor.id]) }}
          <span class="sensor-unit">{{ sensor.unit }}</span>
        </div>
        <div class="sensor-chart-wrap">
          <div :ref="el => setChartRef(sensor.id, el)" class="mini-chart"></div>
        </div>
        <div class="sensor-footer">
          <div class="stat">
            <span class="stat-label">{{ t('sensor.min') }}</span>
            <span class="stat-val">{{ formatValue(sensor.id, sensorStats[sensor.id]?.min) }}</span>
          </div>
          <div class="stat">
            <span class="stat-label">{{ t('sensor.avg') }}</span>
            <span class="stat-val">{{ formatValue(sensor.id, sensorStats[sensor.id]?.avg) }}</span>
          </div>
          <div class="stat">
            <span class="stat-label">{{ t('sensor.max') }}</span>
            <span class="stat-val">{{ formatValue(sensor.id, sensorStats[sensor.id]?.max) }}</span>
          </div>
        </div>
      </el-card>
    </div>

    <!-- 传感器详情弹窗 -->
    <el-dialog v-model="dialogVisible" :title="activeSensor?.icon + ' ' + getSensorLabel(activeSensor?.id) + ' ' + t('sensor.trend')" width="70%" destroy-on-close>
      <div ref="dialogChartRef" style="height: 400px;"></div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { useLocaleStore } from '@/stores/locale'

const localeStore = useLocaleStore()

function t(key: string): string {
  void localeStore.locale
  return localeStore.t(key)
}

function getSensorLabel(id: string) {
  return t('sensor.' + id)
}

const sensorConfig = [
  { id: 'core_temp', label: '核心温度', unit: '°C', color: '#409eff', icon: '🌡' },
  { id: 'target_temp', label: '目标温度', unit: '°C', color: '#e6a23c', icon: '🎯' },
  { id: 'fuel_flow', label: '燃料流量', unit: 'Nm³/min', color: '#f56c6c', icon: '⛽' },
  { id: 'air_flow', label: '进风流量', unit: 'Nm³/min', color: '#3498db', icon: '💨' },
  { id: 'air_temp', label: '进风温度', unit: '°C', color: '#e67e22', icon: '🌬' },
  { id: 'furnace_pressure', label: '炉膛压力', unit: 'Pa', color: '#9b59b6', icon: '🏭' },
  { id: 'wall_temp_upper', label: '上部壁温', unit: '°C', color: '#e74c3c', icon: '🔝' },
  { id: 'wall_temp_mid', label: '中部壁温', unit: '°C', color: '#2ecc71', icon: '🔥' },
  { id: 'wall_temp_lower', label: '下部壁温', unit: '°C', color: '#1abc9c', icon: '⬇' }
]

const currentData = ref<any>(null)
const historyData = ref<any>(null)
const sensorStats = reactive<Record<string, { min: number; max: number; avg: number }>>({})

const chartRefs: Record<string, HTMLElement> = {}
const chartInstances: Record<string, any> = {}
let updateTimer: number | null = null

const dialogVisible = ref(false)
const activeSensor = ref<any>(null)
const dialogChartRef = ref<HTMLElement | null>(null)
let dialogChart: any = null

function setChartRef(id: string, el: any) {
  if (el) chartRefs[id] = el
}

function formatValue(id: string, val: number | undefined) {
  if (val == null) return '--'
  if (id.includes('flow')) return val.toFixed(3)
  return val.toFixed(1)
}

function formatTime(ts: string) {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function calcStats(id: string, data: number[]) {
  if (!data || data.length === 0) {
    sensorStats[id] = { min: 0, max: 0, avg: 0 }
    return
  }
  const min = Math.min(...data)
  const max = Math.max(...data)
  const avg = data.reduce((a, b) => a + b, 0) / data.length
  sensorStats[id] = { min, max, avg }
}

function initMiniCharts() {
  sensorConfig.forEach(s => {
    const el = chartRefs[s.id]
    if (!el) return
    if (chartInstances[s.id]) chartInstances[s.id].dispose()
    chartInstances[s.id] = echarts.init(el)
  })
}

function updateMiniCharts() {
  if (!historyData.value) return
  const times = (historyData.value.timestamps || []).map(formatTime)

  sensorConfig.forEach(s => {
    const chart = chartInstances[s.id]
    if (!chart) return
    const data = historyData.value[s.id] || []
    calcStats(s.id, data)

    chart.setOption({
      grid: { left: 0, right: 0, top: 4, bottom: 0 },
      xAxis: { type: 'category', show: false, data: times },
      yAxis: { type: 'value', show: false },
      series: [{
        type: 'line', smooth: true, data,
        symbol: 'none', lineStyle: { width: 1.5, color: s.color },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: s.color + '40' },
            { offset: 1, color: s.color + '05' }
          ])
        }
      }],
      tooltip: { show: false }
    }, true)
  })
}

function openDialog(sensor: any) {
  activeSensor.value = sensor
  dialogVisible.value = true
}

watch(dialogVisible, async (val) => {
  if (val) {
    await nextTick()
    initDialogChart()
  } else {
    if (dialogChart) { dialogChart.dispose(); dialogChart = null }
  }
})

function initDialogChart() {
  if (!dialogChartRef.value || !activeSensor.value || !historyData.value) return
  if (dialogChart) dialogChart.dispose()
  dialogChart = echarts.init(dialogChartRef.value)

  const s = activeSensor.value
  const times = (historyData.value.timestamps || []).map(formatTime)
  const data = historyData.value[s.id] || []

  dialogChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: [getSensorLabel(s.id)] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: times },
    yAxis: { type: 'value' },
    series: [{
      name: getSensorLabel(s.id),
      type: 'line',
      smooth: true,
      data,
      itemStyle: { color: s.color },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: s.color + '30' },
          { offset: 1, color: s.color + '05' }
        ])
      }
    }]
  })
}

const fetchData = async () => {
  try {
    const [current, history] = await Promise.all([
      fetch('/api/furnace/current').then(r => r.json()),
      fetch('/api/furnace/history').then(r => r.json())
    ])
    currentData.value = current.data
    historyData.value = history.data
    updateMiniCharts()
  } catch (e) {
    console.error('获取数据失败', e)
  }
}

const handleResize = () => {
  Object.values(chartInstances).forEach(c => c?.resize())
  dialogChart?.resize()
}

// Re-render charts when locale changes
watch(() => localeStore.locale, () => {
  updateMiniCharts()
  if (dialogVisible.value) {
    initDialogChart()
  }
})

onMounted(async () => {
  await fetchData()
  await nextTick()
  initMiniCharts()
  updateMiniCharts()
  window.addEventListener('resize', handleResize)
  updateTimer = window.setInterval(fetchData, 2000)
})

onUnmounted(() => {
  Object.values(chartInstances).forEach(c => c?.dispose())
  dialogChart?.dispose()
  window.removeEventListener('resize', handleResize)
  if (updateTimer) clearInterval(updateTimer)
})
</script>

<style scoped>
.sensors-view {
  padding: 20px;
}

.sensors-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.sensor-card {
  cursor: pointer;
  transition: all 0.3s;
}

.sensor-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.sensor-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.sensor-icon {
  font-size: 20px;
}

.sensor-name {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
  flex: 1;
}

.live-tag {
  font-size: 10px;
  color: #67c23a;
  font-weight: 600;
  letter-spacing: 1px;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.sensor-value {
  font-size: 32px;
  font-weight: bold;
  font-family: monospace;
  margin-bottom: 8px;
}

.sensor-unit {
  font-size: 14px;
  font-weight: normal;
  color: #909399;
}

.mini-chart {
  height: 60px;
  width: 100%;
  margin-bottom: 8px;
}

.sensor-footer {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid #ebeef5;
  padding-top: 8px;
}

.stat {
  text-align: center;
}

.stat-label {
  font-size: 11px;
  color: #909399;
  display: block;
}

.stat-val {
  font-size: 13px;
  font-weight: 600;
  font-family: monospace;
  color: #606266;
}
</style>
