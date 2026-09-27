<template>
  <div class="dashboard">
    <!-- 阶段时间线 -->
    <el-card shadow="hover" class="phase-card">
      <div class="phase-bar">
        <div class="phase-segment phase-heating" style="width: 13.89%;">{{ t('dashboard.heating') }}</div>
        <div class="phase-segment phase-holding" style="width: 27.78%;">{{ t('dashboard.holding') }}</div>
        <div class="phase-segment phase-cooling" style="width: 41.67%;">{{ t('dashboard.cooling') }}</div>
        <div class="phase-segment phase-unload" style="width: 16.67%;">{{ t('dashboard.unload') }}</div>
        <div class="phase-marker" :style="{ left: progressPercent + '%' }"></div>
      </div>
      <div class="phase-labels">
        <span>00:00</span>
        <span>03:20</span>
        <span>10:00</span>
        <span>20:00</span>
        <span>24:00</span>
      </div>
      <div class="phase-info">
        <div class="phase-info-item">
          <span class="info-label">{{ t('dashboard.current_time') }}</span>
          <span class="info-value">{{ currentTimeStr }}</span>
        </div>
        <el-divider direction="vertical" />
        <div class="phase-info-item">
          <span class="info-label">{{ t('dashboard.cycle_progress') }}</span>
          <span class="info-value">{{ progressPercent.toFixed(1) }}%</span>
        </div>
        <el-divider direction="vertical" />
        <div class="phase-info-item">
          <span class="info-label">{{ t('dashboard.current_phase') }}</span>
          <el-tag :type="phaseTagType" effect="dark" size="large">{{ getPhaseLabel(currentData?.phase) }}</el-tag>
        </div>
        <el-divider direction="vertical" />
        <div class="phase-info-item">
          <span class="info-label">{{ t('dashboard.system_status') }}</span>
          <el-tag :type="prediction?.alarm?.alarmed ? 'danger' : 'success'" effect="dark" size="large">
            {{ prediction?.alarm?.alarmed ? t('dashboard.alarm') : t('dashboard.normal') }}
          </el-tag>
        </div>
      </div>
    </el-card>

    <!-- 主内容区 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <!-- 左侧：核心温度曲线 -->
      <el-col :span="16">
        <el-card shadow="hover" class="chart-card" @click="tempDialogVisible = true">
          <template #header>
            <div class="card-header">
              <span>{{ t('sensor.core_temp') }}曲线</span>
              <el-tag type="info" size="small" effect="plain">{{ t('sensor.trend') }}</el-tag>
            </div>
          </template>
          <div ref="tempChartRef" class="chart-container"></div>
        </el-card>
      </el-col>

      <!-- 右侧 -->
      <el-col :span="8">
        <!-- 交互式退火炉模型 -->
        <el-card shadow="hover" style="margin-bottom: 20px; cursor: pointer;" @click="furnaceDialogVisible = true">
          <template #header>
            <div class="card-header">
              <span>{{ t('dashboard.furnace_overview') }}</span>
              <span class="live-dot">● LIVE</span>
            </div>
          </template>
          <div class="furnace-container" v-if="currentData">
            <img :src="furnaceImageUrl" alt="退火炉模型" class="furnace-image">

            <!-- 传感器热点 -->
            <div
              class="sensor-point"
              v-for="sensor in sensorConfig"
              :key="sensor.id"
              :class="{
                'sensor-point-core': sensor.id === 'core_temp',
                'sensor-point-alarm': sensor.id === 'core_temp' && prediction?.alarm?.alarmed,
                'sensor-point-bottom-value': sensor.id === 'air_temp' || sensor.id === 'fuel_flow'
              }"
              :style="{
                top: sensorPosition[sensor.id].top + '%',
                left: sensorPosition[sensor.id].left + '%'
              }"
              :title="getSensorLabel(sensor.id)"
              @click.stop="openSensorDialog(sensor)"
            >
              <span class="sensor-dot" :style="{ background: sensor.color }"></span>
              <span class="sensor-value" :style="{ color: sensor.color }">
                {{ formatSensorValue(sensor.id, currentData[sensor.id]) }}{{ sensor.unit }}
              </span>
            </div>
          </div>
        </el-card>

        <!-- 报警与建议 -->
        <el-card shadow="hover">
          <template #header><span>{{ t('dashboard.status_advice') }}</span></template>
          <div class="alarm-section">
            <div :class="['alarm-box', prediction?.alarm?.alarmed ? 'alarm-box-danger' : 'alarm-box-success']">
              <p class="alarm-label">{{ t('dashboard.system_status') }}</p>
              <p class="alarm-text">{{ alarmTitle }}</p>
              <p class="alarm-detail" v-html="alarmDetailHtml"></p>
            </div>
            <div class="suggestion-box">
              <p class="suggestion-label">{{ t('dashboard.suggestion') }}</p>
              <div v-if="prediction?.alarm?.alarmed && prediction.alarm.suggested_fuel !== null">
                <div class="suggestion-row">
                  <span>{{ t('sensor.fuel_flow') }}</span>
                  <span>
                    <span class="old-value">{{ prediction.alarm.current_fuel.toFixed(3) }}</span>
                    <span class="new-value">{{ prediction.alarm.suggested_fuel.toFixed(3) }}</span>
                  </span>
                </div>
                <div class="suggestion-row">
                  <span>{{ t('sensor.air_flow') }}</span>
                  <span>
                    <span class="old-value">{{ prediction.alarm.current_air.toFixed(3) }}</span>
                    <span class="new-value">{{ prediction.alarm.suggested_air.toFixed(3) }}</span>
                  </span>
                </div>
              </div>
              <div v-else-if="prediction?.alarm">
                <p class="suggestion-normal">{{ t('dashboard.no_adjustment') }}</p>
                <p class="suggestion-current">{{ t('sensor.fuel_flow') }}: {{ prediction.alarm.current_fuel.toFixed(3) }} Nm³/min</p>
                <p class="suggestion-current">{{ t('sensor.air_flow') }}: {{ prediction.alarm.current_air.toFixed(3) }} Nm³/min</p>
              </div>
              <p v-else class="suggestion-normal">{{ t('dashboard.loading') }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 底部信息 -->
    <div class="footer-info">
      <span>{{ t('dashboard.last_update') }}: {{ lastUpdateTime }}</span>
      <span>
        <span class="dot dot-blue"></span> Bi-LSTM Model
        <span class="dot dot-green" style="margin-left:12px;"></span> Real-time
      </span>
    </div>

    <!-- 传感器详情对话框 -->
    <el-dialog v-model="sensorDialogVisible" :title="activeSensor?.icon + ' ' + getSensorLabel(activeSensor?.id) + ' ' + t('dashboard.detail')" width="70%" destroy-on-close>
      <div ref="sensorChartRef" style="height: 400px;"></div>
    </el-dialog>

    <!-- 温度详情对话框 -->
    <el-dialog v-model="tempDialogVisible" :title="t('sensor.core_temp') + t('dashboard.detail')" width="80%" destroy-on-close>
      <div ref="tempFullChartRef" style="height: 450px;"></div>
      <el-table :data="tempTableData" style="margin-top: 16px;" size="small" border>
        <el-table-column prop="label" :label="t('alarms.type')" width="80" />
        <el-table-column v-for="i in 21" :key="i" :label="getTempColLabel(i - 11)" width="70" align="center">
          <template #default="{ row }">
            <span :class="getTempCellClass(row.values[i - 1])">{{ row.values[i - 1]?.toFixed(1) || '--' }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 退火炉大图对话框 -->
    <el-dialog v-model="furnaceDialogVisible" :title="t('dashboard.furnace_overview')" width="95%" top="2vh" align-center destroy-on-close>
      <div class="furnace-container-large" v-if="currentData">
        <img :src="furnaceImageUrl" alt="退火炉模型" class="furnace-image-large">
        <!-- 传感器热点（大图上也显示） -->
        <div
          class="sensor-point-large"
          v-for="sensor in sensorConfig"
          :key="sensor.id"
          :class="{
            'sensor-point-core-large': sensor.id === 'core_temp',
            'sensor-point-alarm-large': sensor.id === 'core_temp' && prediction?.alarm?.alarmed,
            'sensor-point-bottom-value-large': sensor.id === 'air_temp' || sensor.id === 'fuel_flow'
          }"
          :style="{
            top: sensorPosition[sensor.id].top + '%',
            left: sensorPosition[sensor.id].left + '%'
          }"
          :title="getSensorLabel(sensor.id)"
          @click.stop="openSensorDialog(sensor)"
        >
          <span class="sensor-dot-large" :style="{ background: sensor.color }"></span>
          <span class="sensor-value-large" :style="{ color: sensor.color }">
            {{ formatSensorValue(sensor.id, currentData[sensor.id]) }}{{ sensor.unit }}
          </span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
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

function getPhaseLabel(phase?: string) {
  if (!phase) return '--'
  return t('phase.' + phase)
}

function toLocale(locale: string): string {
  const map: Record<string, string> = {
    'zh-hans': 'zh-Hans-CN',
    'zh-hant': 'zh-Hant-TW',
    'ja-jp': 'ja-JP',
    'en-us': 'en-US',
  }
  return map[locale] || 'zh-Hans-CN'
}

const sensorConfig = [
  { id: 'core_temp', label: '核心温度', unit: '°C', color: '#409eff', icon: '🌡' },
  { id: 'target_temp', label: '目标温度', unit: '°C', color: '#e6a23c', icon: '🎯' },
  { id: 'fuel_flow', label: '燃料流量', unit: 'Nm³/min', color: '#f56c6c', icon: '⛽' },
  { id: 'air_flow', label: '进风流量', unit: 'Nm³/min', color: '#409eff', icon: '💨' },
  { id: 'air_temp', label: '进风温度', unit: '°C', color: '#e6a23c', icon: '🌬' },
  { id: 'furnace_pressure', label: '炉膛压力', unit: 'Pa', color: '#9b59b6', icon: '🏭' },
  { id: 'wall_temp_mid', label: '中部壁温', unit: '°C', color: '#3498db', icon: '🔥' },
  { id: 'wall_temp_upper', label: '上部壁温', unit: '°C', color: '#e74c3c', icon: '🔝' },
  { id: 'wall_temp_lower', label: '下部壁温', unit: '°C', color: '#2ecc71', icon: '⬇' }
]

// 传感器在退火炉模型上的位置（百分比，大小图通用）
const sensorPosition: Record<string, { top: number; left: number }> = {
  target_temp: { top: 50, left: 10 },    // 左侧控制柜（显示屏位置）
  wall_temp_upper: { top: 34, left: 36 }, // 炉门上部
  core_temp: { top: 48, left: 31 },      // 炉门中心（靠左，和中部壁温错开）
  wall_temp_mid: { top: 48, left: 40 },  // 炉体中部（靠右，完全错开）
  wall_temp_lower: { top: 62, left: 36 }, // 炉门下部
  furnace_pressure: { top: 28, left: 50 }, // 炉体出口管道连接处
  air_temp: { top: 58, left: 63 },       // 冷凝器下部管道
  fuel_flow: { top: 74, left: 82 },      // 右侧蓝色大泵
  air_flow: { top: 76, left: 94 }        // 右侧蓝色小泵
}

// 退火炉模型图片路径（public目录下的资源直接使用根路径）
const furnaceImageUrl = '/images/furnace_model.png'

const tempChartRef = ref<HTMLElement | null>(null)
const sensorChartRef = ref<HTMLElement | null>(null)
const tempFullChartRef = ref<HTMLElement | null>(null)

let tempChart: any = null
let sensorChart: any = null
let tempFullChart: any = null
let updateTimer: number | null = null

const currentData = ref<any>(null)
const historyData = ref<any>(null)
const prediction = ref<any>(null)
const lastUpdateTime = ref('--')

const sensorDialogVisible = ref(false)
const tempDialogVisible = ref(false)
const furnaceDialogVisible = ref(false)
const activeSensor = ref<any>(null)

const progressPercent = computed(() => {
  return ((currentData.value?.minute_of_day || 0) / 1440) * 100
})

const currentTimeStr = computed(() => {
  const m = currentData.value?.minute_of_day || 0
  return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
})

const phaseTagType = computed(() => {
  const phase = currentData.value?.phase
  if (phase === 'heating') return 'warning'
  if (phase === 'holding') return 'success'
  if (phase === 'cooling') return 'info'
  return 'info'
})

const alarmTitle = computed(() => {
  if (!prediction.value) return '--'
  const phase = getPhaseLabel(prediction.value.phase)
  return prediction.value.alarm?.alarmed ? `${phase} ${t('dashboard.alarm')}` : phase
})

const alarmDetailHtml = computed(() => {
  if (!prediction.value?.alarm) return ''
  const alarm = prediction.value.alarm
  const phase = getPhaseLabel(prediction.value.phase)
  const tempRange = `${alarm.min_temp.toFixed(1)}~${alarm.max_temp.toFixed(1)}°C`
  let html = alarm.alarmed
    ? `${t('dashboard.predicted_temp')} ${getAlarmTemp(alarm).toFixed(1)}°C，${getAlarmDirectionText(alarm)} ${alarm.overshoot?.toFixed(1) || '0.0'}°C`
    : `${t('dashboard.normal_bracket')} ${phase}，${t('dashboard.predicted_temp')} ${tempRange}`
  if (alarm.upper_limit !== null || alarm.lower_limit !== null) {
    html += '<br><span style="color:#909399;">'
    if (alarm.upper_limit !== null) html += `${t('alarms.upper')}: <span style="color:#f56c6c;">${alarm.upper_limit.toFixed(1)}°C</span>`
    if (alarm.upper_limit !== null && alarm.lower_limit !== null) html += ' | '
    if (alarm.lower_limit !== null) html += `${t('alarms.lower')}: <span style="color:#e6a23c;">${alarm.lower_limit.toFixed(1)}°C</span>`
    html += '</span>'
  }
  return html
})

function getAlarmTemp(alarm: any) {
  return alarm.direction === '下限' ? alarm.min_temp : alarm.max_temp
}

function getAlarmDirectionText(alarm: any) {
  if (alarm.direction === '下限') return t('dashboard.below_lower_limit')
  if (alarm.direction === '双限') return t('dashboard.exceeds_both_limits')
  if (alarm.direction === '回温') return t('dashboard.abnormal_reheating')
  return t('dashboard.exceeds_upper_limit')
}

const tempTableData = computed(() => {
  if (!historyData.value || !prediction.value) return []
  const hist10 = historyData.value.core_temp.slice(-10)
  const current = historyData.value.core_temp[historyData.value.core_temp.length - 1]
  const pred10 = prediction.value.predictions
  return [{
    label: '温度(°C)',
    values: [...hist10, current, ...pred10]
  }]
})

function formatSensorValue(id: string, val: number) {
  if (val == null) return '--'
  if (id.includes('flow')) return val.toFixed(3)
  return val.toFixed(1)
}

function getTempColLabel(offset: number) {
  if (offset === 0) return '当前'
  if (offset > 0) return `t+${offset}`
  return `t${offset}`
}

function getTempCellClass(val: number | undefined) {
  if (val == null) return ''
  const upper = prediction.value?.alarm?.upper_limit
  const lower = prediction.value?.alarm?.lower_limit
  if (upper !== null && val >= upper) return 'cell-danger'
  if (lower !== null && val <= lower) return 'cell-warning'
  return ''
}

function formatTime(ts: string) {
  const d = new Date(ts)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function initTempChart() {
  if (!tempChartRef.value) return
  tempChart = echarts.init(tempChartRef.value)
}

function updateTempChart() {
  if (!tempChart || !historyData.value || !prediction.value) return

  const histTimes = (historyData.value.timestamps || []).map(formatTime)
  const predTimes = (prediction.value.timestamps || []).map(formatTime)
  const histCore = historyData.value.core_temp || []
  const histTarget = historyData.value.target_temp || []
  const predCore = prediction.value.predictions || []
  const upperLimit = prediction.value.alarm?.upper_limit
  const lowerLimit = prediction.value.alarm?.lower_limit

  const allTimes = [...histTimes, ...predTimes]
  const predData = new Array(Math.max(0, histCore.length - 1)).fill(null)
    .concat(histCore.length > 0 ? [histCore[histCore.length - 1]] : [])
    .concat(predCore)

  tempChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: [t('dashboard.legend_hist_core'), t('dashboard.legend_target'), t('dashboard.legend_pred'), t('dashboard.legend_upper'), t('dashboard.legend_lower')] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: allTimes },
    yAxis: { type: 'value', min: 0, max: 1000, axisLabel: { formatter: '{value}°C' } },
    series: [
      {
        name: t('dashboard.legend_hist_core'), type: 'line', smooth: true,
        data: [...histCore, ...new Array(predTimes.length).fill(null)],
        itemStyle: { color: '#409eff' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(64,158,255,0.3)' }, { offset: 1, color: 'rgba(64,158,255,0.05)' }]) }
      },
      {
        name: t('dashboard.legend_target'), type: 'line', smooth: true,
        data: [...histTarget, ...new Array(predTimes.length).fill(null)],
        itemStyle: { color: '#e6a23c' }, lineStyle: { type: 'dashed' }
      },
      {
        name: t('dashboard.legend_pred'), type: 'line', smooth: true,
        data: predData,
        itemStyle: { color: '#67c23a' },
        lineStyle: { width: 3 },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(103,194,58,0.3)' }, { offset: 1, color: 'rgba(103,194,58,0.05)' }]) }
      },
      {
        name: t('dashboard.legend_upper'), type: 'line',
        data: upperLimit != null ? new Array(allTimes.length).fill(upperLimit) : [],
        itemStyle: { color: '#f56c6c' }, lineStyle: { type: 'dotted', width: 2 }, symbol: 'none'
      },
      {
        name: t('dashboard.legend_lower'), type: 'line',
        data: lowerLimit != null ? new Array(allTimes.length).fill(lowerLimit) : [],
        itemStyle: { color: '#e6a23c' }, lineStyle: { type: 'dotted', width: 2 }, symbol: 'none'
      }
    ]
  }, true)
}

function openSensorDialog(sensor: any) {
  activeSensor.value = sensor
  sensorDialogVisible.value = true
}

watch(sensorDialogVisible, async (val) => {
  if (val) {
    await nextTick()
    initSensorChart()
  } else {
    if (sensorChart) { sensorChart.dispose(); sensorChart = null }
  }
})

function initSensorChart() {
  if (!sensorChartRef.value) return
  if (sensorChart) sensorChart.dispose()
  sensorChart = echarts.init(sensorChartRef.value)
  if (!historyData.value || !activeSensor.value) return

  const times = (historyData.value.timestamps || []).map(formatTime)
  const s = activeSensor.value
  sensorChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: [getSensorLabel(s.id)] },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: times },
    yAxis: { type: 'value' },
    series: [{
      name: getSensorLabel(s.id), type: 'line', smooth: true,
      data: historyData.value[s.id] || [],
      itemStyle: { color: s.color },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: s.color + '40' }, { offset: 1, color: s.color + '05' }]) }
    }]
  })
}

watch(tempDialogVisible, async (val) => {
  if (val) {
    await nextTick()
    initTempFullChart()
  } else {
    if (tempFullChart) { tempFullChart.dispose(); tempFullChart = null }
  }
})

function initTempFullChart() {
  if (!tempFullChartRef.value || !historyData.value || !prediction.value) return
  if (tempFullChart) tempFullChart.dispose()
  tempFullChart = echarts.init(tempFullChartRef.value)

    const histTimes = (historyData.value.timestamps || []).map(formatTime)
    const predTimes = (prediction.value.timestamps || []).map(formatTime)
    const histCore = historyData.value.core_temp || []
    const histTarget = historyData.value.target_temp || []
    const predCore = prediction.value.predictions || []
    const upperLimit = prediction.value.alarm?.upper_limit
    const lowerLimit = prediction.value.alarm?.lower_limit

    const allTimes = [...histTimes, ...predTimes]
    const predData = new Array(Math.max(0, histCore.length - 1)).fill(null)
      .concat(histCore.length > 0 ? [histCore[histCore.length - 1]] : [])
      .concat(predCore)

    tempFullChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: [t('dashboard.legend_hist_core'), t('dashboard.legend_target'), t('dashboard.legend_pred'), t('dashboard.legend_upper'), t('dashboard.legend_lower')] },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', boundaryGap: false, data: allTimes },
      yAxis: { type: 'value', min: 0, max: 1000, axisLabel: { formatter: '{value}°C' } },
      series: [
        {
          name: t('dashboard.legend_hist_core'), type: 'line', smooth: true,
          data: [...histCore, ...new Array(predTimes.length).fill(null)],
          itemStyle: { color: '#409eff' },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(64,158,255,0.15)' }, { offset: 1, color: 'rgba(64,158,255,0.02)' }]) }
        },
        {
          name: t('dashboard.legend_target'), type: 'line', smooth: true,
          data: [...histTarget, ...new Array(predTimes.length).fill(null)],
          itemStyle: { color: '#e6a23c' }, lineStyle: { type: 'dashed' }
        },
        {
          name: t('dashboard.legend_pred'), type: 'line', smooth: true,
          data: predData,
          itemStyle: { color: '#67c23a' }, lineStyle: { width: 3 },
          areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(103,194,58,0.25)' }, { offset: 1, color: 'rgba(103,194,58,0.02)' }]) }
        },
        {
          name: t('dashboard.legend_upper'), type: 'line',
          data: upperLimit != null ? new Array(allTimes.length).fill(upperLimit) : [],
          itemStyle: { color: '#f56c6c' }, lineStyle: { type: 'dotted', width: 2 }, symbol: 'none'
        },
        {
          name: t('dashboard.legend_lower'), type: 'line',
          data: lowerLimit != null ? new Array(allTimes.length).fill(lowerLimit) : [],
          itemStyle: { color: '#e6a23c' }, lineStyle: { type: 'dotted', width: 2 }, symbol: 'none'
        }
      ]
    })
}

const fetchData = async () => {
  try {
    const [current, history, pred] = await Promise.all([
      fetch('/api/furnace/current').then(r => r.json()),
      fetch('/api/furnace/history').then(r => r.json()),
      fetch('/api/furnace/prediction').then(r => r.json())
    ])
    currentData.value = current.data
    historyData.value = history.data
    prediction.value = pred.data
    updateTempChart()
    lastUpdateTime.value = new Date().toLocaleTimeString(toLocale(localeStore.locale))
  } catch (e) {
    console.error('获取数据失败', e)
  }
}

const handleResize = () => {
  tempChart?.resize()
  sensorChart?.resize()
  tempFullChart?.resize()
}

// Re-render charts when locale changes
watch(() => localeStore.locale, () => {
  updateTempChart()
  if (sensorDialogVisible.value) {
    initSensorChart()
  }
  if (tempDialogVisible.value) {
    initTempFullChart()
  }
})

onMounted(async () => {
  await nextTick()
  initTempChart()
  fetchData()
  window.addEventListener('resize', handleResize)
  updateTimer = window.setInterval(fetchData, 2000)
})

onUnmounted(() => {
  tempChart?.dispose()
  sensorChart?.dispose()
  tempFullChart?.dispose()
  window.removeEventListener('resize', handleResize)
  if (updateTimer) clearInterval(updateTimer)
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
}

/* 阶段时间线 */
.phase-card {
  margin-bottom: 0;
}

.phase-bar {
  width: 100%;
  height: 12px;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  position: relative;
}

.phase-segment {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  color: white;
  font-weight: 500;
}

.phase-heating { background: linear-gradient(90deg, #f97316, #ea580c, #dc2626); }
.phase-holding { background: linear-gradient(90deg, #eab308, #ca8a04, #a16207); }
.phase-cooling { background: linear-gradient(90deg, #06b6d4, #0891b2, #0e7490); }
.phase-unload { background: linear-gradient(90deg, #6b7280, #4b5563, #374151); }

.phase-marker {
  position: absolute;
  top: -4px;
  width: 12px;
  height: 20px;
  transform: translateX(-50%);
  border-radius: 6px;
  background: linear-gradient(to bottom, white, #67c23a);
  box-shadow: 0 0 8px rgba(103, 194, 58, 0.6);
  border: 2px solid #67c23a;
  z-index: 10;
  transition: left 0.5s ease;
}

.phase-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  font-family: monospace;
}

.phase-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 12px;
}

.phase-info-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.info-label {
  font-size: 12px;
  color: #909399;
}

.info-value {
  font-size: 16px;
  font-weight: bold;
  font-family: monospace;
  color: #409eff;
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.live-dot {
  color: #67c23a;
  font-size: 12px;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 图表 */
.chart-container {
  height: 400px;
}

/* 退火炉模型容器 */
.furnace-container {
  position: relative;
  width: 100%;
  min-height: fit-content;
  padding-bottom: 8px;
}

.furnace-image {
  width: 100%;
  height: auto;
  border-radius: 8px;
  display: block;
}

/* 传感器热点 */
.sensor-point {
  position: absolute;
  cursor: pointer;
  transform: translate(-50%, -50%);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 10;
}

.sensor-point:hover {
  transform: translate(-50%, -50%) scale(1.2);
  z-index: 20;
}

.sensor-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  display: block;
  box-shadow: 0 0 10px currentColor, 0 0 20px rgba(0, 0, 0, 0.2);
  border: 2px solid white;
  animation: sensorPulse 2s infinite;
}

.sensor-value {
  position: absolute;
  top: -25px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  background: rgba(15, 23, 42, 0.9);
  padding: 2px 6px;
  border-radius: 6px;
  border: 1px solid currentColor30;
  text-shadow: 0 0 5px rgba(0, 0, 0, 0.3);
  pointer-events: none;
  font-family: monospace;
}

.sensor-point:hover .sensor-value {
  background: rgba(15, 23, 42, 0.95);
  border-color: rgba(255, 255, 255, 0.3);
  font-size: 11px;
}

@keyframes sensorPulse {
  0%, 100% {
    box-shadow: 0 0 10px currentColor, 0 0 20px currentColor40;
  }
  50% {
    box-shadow: 0 0 15px currentColor, 0 0 30px currentColor60;
  }
}

/* 核心温度高亮样式（小图） */
.sensor-point-core .sensor-dot {
  width: 16px;
  height: 16px;
  border-width: 3px;
  box-shadow: 0 0 20px #409eff, 0 0 40px rgba(64, 158, 255, 0.6);
  animation-duration: 1s;
}
.sensor-point-core .sensor-value {
  font-size: 12px;
  font-weight: 800;
  box-shadow: 0 0 10px rgba(64, 158, 255, 0.5);
}

/* 核心温度报警样式（小图） */
.sensor-point-alarm .sensor-dot {
  background: #f56c6c !important;
  box-shadow: 0 0 20px #f56c6c, 0 0 40px rgba(245, 108, 108, 0.8) !important;
  animation: alarmPulse 0.8s infinite !important;
}
.sensor-point-alarm .sensor-value {
  color: #f56c6c !important;
  background: rgba(245, 108, 108, 0.15) !important;
  border-color: #f56c6c !important;
}

/* 核心温度高亮样式（大图） */
.sensor-point-core-large .sensor-dot-large {
  width: 22px;
  height: 22px;
  border-width: 4px;
  box-shadow: 0 0 25px #409eff, 0 0 50px rgba(64, 158, 255, 0.7);
  animation-duration: 1s;
}
.sensor-point-core-large .sensor-value-large {
  font-size: 18px;
  font-weight: 800;
  box-shadow: 0 0 15px rgba(64, 158, 255, 0.6);
}

/* 核心温度报警样式（大图） */
.sensor-point-alarm-large .sensor-dot-large {
  background: #f56c6c !important;
  box-shadow: 0 0 25px #f56c6c, 0 0 50px rgba(245, 108, 108, 0.9) !important;
  animation: alarmPulse 0.8s infinite !important;
}
.sensor-point-alarm-large .sensor-value-large {
  color: #f56c6c !important;
  background: rgba(245, 108, 108, 0.2) !important;
  border-color: #f56c6c !important;
}

/* 右下角传感器数值显示在下方（小图） */
.sensor-point-bottom-value .sensor-value {
  top: auto;
  bottom: -25px;
}

/* 右下角传感器数值显示在下方（大图） */
.sensor-point-bottom-value-large .sensor-value-large {
  top: auto;
  bottom: -35px;
}

/* 大图模式样式 */
.furnace-container-large {
  position: relative;
  width: fit-content; /* 容器宽度自适应图片宽度，保证百分比定位准确 */
  margin: 0 auto;
}

.furnace-image-large {
  height: auto;
  max-height: 72vh;
  max-width: 100%;
  border-radius: 8px;
  display: block;
}

.sensor-point-large {
  position: absolute;
  cursor: pointer;
  transform: translate(-50%, -50%);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 10;
}

.sensor-point-large:hover {
  transform: translate(-50%, -50%) scale(1.2);
  z-index: 20;
}

.sensor-dot-large {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: block;
  box-shadow: 0 0 15px currentColor, 0 0 30px rgba(0, 0, 0, 0.2);
  border: 3px solid white;
  animation: sensorPulse 2s infinite;
}

.sensor-value-large {
  position: absolute;
  top: -42px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 16px;
  font-weight: 700;
  white-space: nowrap;
  background: rgba(15, 23, 42, 0.98);
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid currentColor50;
  text-shadow: 0 0 8px rgba(0, 0, 0, 0.5);
  pointer-events: none;
  font-family: monospace;
}

/* 报警区域 */
.alarm-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.alarm-box {
  padding: 12px;
  border-radius: 8px;
}

.alarm-box-success {
  background: linear-gradient(135deg, #f0f9eb, #e1f3d8);
  border: 1px solid #67c23a;
}

.alarm-box-danger {
  background: linear-gradient(135deg, #fef0f0, #fde2e2);
  border: 1px solid #f56c6c;
  animation: alarmPulse 1.5s infinite;
}

@keyframes alarmPulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.alarm-label {
  font-size: 12px;
  color: #909399;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 600;
  margin-bottom: 4px;
}

.alarm-text {
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

.alarm-detail {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.suggestion-box {
  padding: 12px;
  border-radius: 8px;
  background: linear-gradient(135deg, #ecf5ff, #d9ecff);
  border: 1px solid #409eff;
}

.suggestion-label {
  font-size: 12px;
  color: #409eff;
  font-weight: 600;
  margin-bottom: 8px;
}

.suggestion-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid #d9ecff;
  font-size: 13px;
}

.old-value {
  text-decoration: line-through;
  color: #f56c6c;
  margin-right: 8px;
}

.new-value {
  color: #67c23a;
  font-weight: bold;
  font-family: monospace;
}

.suggestion-normal {
  color: #67c23a;
  font-size: 13px;
}

.suggestion-current {
  color: #67c23a;
  font-size: 12px;
  font-family: monospace;
  margin-top: 4px;
}

/* 底部信息 */
.footer-info {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
  font-size: 12px;
  color: #909399;
}

.dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
}

.dot-blue { background: #409eff; }
.dot-green { background: #67c23a; }

/* 表格单元格 */
:deep(.cell-danger) {
  color: #f56c6c;
  font-weight: bold;
}

:deep(.cell-warning) {
  color: #e6a23c;
  font-weight: bold;
}

/* 大图对话框内容区无滚动 */
:deep(.el-dialog__body) {
  padding: 10px 20px 0 20px;
  overflow: hidden;
}
</style>
