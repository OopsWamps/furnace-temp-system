<template>
  <div class="history">
    <el-card>
      <template #header>
        <div class="header-content">
          <span>{{ t('history.title') }}</span>
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            :range-separator="t('history.to')"
            :start-placeholder="t('history.start_time')"
            :end-placeholder="t('history.end_time')"
          />
          <el-button type="primary">{{ t('history.query') }}</el-button>
        </div>
      </template>
      <div ref="chartRef" class="chart-container"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import type { ECharts } from 'echarts'
import { useLocaleStore } from '@/stores/locale'

const localeStore = useLocaleStore()

function t(key: string): string {
  void localeStore.locale
  return localeStore.t(key)
}

const dateRange = ref()
const chartRef = ref<HTMLElement>()
let chart: ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: [t('sensor.fuel_flow'), t('sensor.air_flow'), t('sensor.core_temp')] },
    xAxis: { type: 'category', data: Array.from({ length: 24 }, (_, i) => `${i}:00`) },
    yAxis: [
      { type: 'value', name: t('history.flow'), position: 'left' },
      { type: 'value', name: t('history.temp'), position: 'right' }
    ],
    series: [
      { name: t('sensor.fuel_flow'), type: 'line', smooth: true, data: Array.from({ length: 24 }, () => Math.random() * 0.5 + 0.2) },
      { name: t('sensor.air_flow'), type: 'line', smooth: true, data: Array.from({ length: 24 }, () => Math.random() * 5 + 2) },
      { name: t('sensor.core_temp'), type: 'line', smooth: true, yAxisIndex: 1, data: Array.from({ length: 24 }, () => Math.random() * 200 + 600) }
    ]
  }
  chart.setOption(option)
}

const handleResize = () => {
  chart?.resize()
}

// Re-render chart when locale changes
watch(() => localeStore.locale, () => { initChart() })

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  chart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.chart-container {
  height: 500px;
}
</style>
