<template>
  <div class="temperature">
    <el-card>
      <template #header>
        <span>{{ t('temperature.title') }}</span>
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

const chartRef = ref<HTMLElement>()
let chart: ECharts | null = null

const initChart = () => {
  if (!chartRef.value) return
  chart = echarts.init(chartRef.value)
  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: [t('sensor.core_temp'), t('sensor.wall_temp_upper'), t('sensor.wall_temp_mid'), t('sensor.wall_temp_lower')] },
    xAxis: {
      type: 'category',
      data: Array.from({ length: 60 }, (_, idx) => `${idx}min`)
    },
    yAxis: { type: 'value', min: 0, max: 1000 },
    series: [
      { name: t('sensor.core_temp'), type: 'line', smooth: true, data: Array.from({ length: 60 }, () => 600 + Math.random() * 200) },
      { name: t('sensor.wall_temp_upper'), type: 'line', smooth: true, data: Array.from({ length: 60 }, () => 580 + Math.random() * 180) },
      { name: t('sensor.wall_temp_mid'), type: 'line', smooth: true, data: Array.from({ length: 60 }, () => 590 + Math.random() * 190) },
      { name: t('sensor.wall_temp_lower'), type: 'line', smooth: true, data: Array.from({ length: 60 }, () => 570 + Math.random() * 170) }
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
.chart-container {
  height: 500px;
}
</style>
