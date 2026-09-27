<template>
  <div class="alarms-view">
    <!-- 统计卡片 -->
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #f56c6c;">
              <el-icon :size="28"><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ alarmData?.total || 0 }}</div>
              <div class="stat-title">{{ t('alarms.total') }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #e6a23c;">
              <el-icon :size="28"><Bell /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ alarmData?.unacknowledged || 0 }}</div>
              <div class="stat-title">{{ t('alarms.unacknowledged') }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background-color: #67c23a;">
              <el-icon :size="28"><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ (alarmData?.total || 0) - (alarmData?.unacknowledged || 0) }}</div>
              <div class="stat-title">{{ t('alarms.acknowledged') }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选和操作栏 -->
    <el-card shadow="hover" style="margin-top: 20px;">
      <div class="filter-bar">
        <div class="filter-left">
          <el-select v-model="filterPhase" :placeholder="t('alarms.filter_phase')" clearable style="width: 140px;">
            <el-option :label="t('dashboard.heating')" value="heating" />
            <el-option :label="t('dashboard.holding')" value="holding" />
            <el-option :label="t('dashboard.cooling')" value="cooling" />
          </el-select>
          <el-select v-model="filterAck" :placeholder="t('alarms.status')" clearable style="width: 140px;">
            <el-option :label="t('alarms.unacknowledged')" :value="false" />
            <el-option :label="t('alarms.acknowledged')" :value="true" />
          </el-select>
        </div>
        <el-button type="success" @click="ackAll" :disabled="!alarmData?.unacknowledged">
          {{ t('alarms.ack_all') }}
        </el-button>
      </div>
    </el-card>

    <!-- 报警列表 -->
    <el-card shadow="hover" style="margin-top: 20px;">
      <el-table :data="alarmData?.records || []" stripe style="width: 100%;" :empty-text="t('alarms.empty')">
        <el-table-column :label="t('alarms.status')" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.acknowledged ? 'info' : 'danger'" size="small" effect="dark">
              {{ row.acknowledged ? t('alarms.acknowledged') : t('alarms.unacknowledged') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('alarms.time')" width="180">
          <template #default="{ row }">
            {{ formatTime(row.time) }}
          </template>
        </el-table-column>
        <el-table-column :label="t('alarms.phase')" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="phaseTagType(row.phase)" size="small">{{ t('dashboard.' + row.phase) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('alarms.direction')" width="80" align="center">
          <template #default="{ row }">
            <el-tag type="warning" size="small">{{ directionLabel(row.direction) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('alarms.pred_max_temp')" width="130" align="center">
          <template #default="{ row }">
            <span class="temp-danger">{{ row.max_temp.toFixed(1) }}°C</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('alarms.overshoot')" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.overshoot" class="temp-danger">+{{ row.overshoot.toFixed(1) }}°C</span>
            <span v-else>--</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('alarms.limit')" width="130" align="center">
          <template #default="{ row }">
            <span v-if="row.upper_limit">{{ t('alarms.upper') }} {{ row.upper_limit.toFixed(1) }}°C</span>
            <span v-if="row.lower_limit">{{ t('alarms.lower') }} {{ row.lower_limit.toFixed(1) }}°C</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('alarms.current_temp')" width="110" align="center">
          <template #default="{ row }">
            {{ row.current_temp.toFixed(1) }}°C
          </template>
        </el-table-column>
        <el-table-column :label="t('alarms.suggested_fuel')" width="110" align="center">
          <template #default="{ row }">
            <span v-if="row.suggested_fuel !== null">
              <span class="old-val">{{ row.current_fuel.toFixed(3) }}</span>
              → <span class="new-val">{{ row.suggested_fuel.toFixed(3) }}</span>
            </span>
            <span v-else>--</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('alarms.description')" min-width="200">
          <template #default="{ row }">
            <span class="detail-text">{{ alarmMsg(row.message) }}</span>
          </template>
        </el-table-column>
        <el-table-column :label="t('alarms.action')" width="100" align="center" fixed="right">
          <template #default="{ row }">
            <el-button v-if="!row.acknowledged" type="primary" size="small" @click="ackOne(row.id)">
              {{ t('alarms.ack') }}
            </el-button>
            <span v-else class="ack-text">--</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Warning, Bell, CircleCheck } from '@element-plus/icons-vue'
import { useLocaleStore } from '@/stores/locale'

const localeStore = useLocaleStore()

function t(key: string): string {
  void localeStore.locale
  return localeStore.t(key)
}

function directionLabel(dir: string): string {
  const map: Record<string, string> = {
    '上升': t('alarms.direction_up'),
    '下降': t('alarms.direction_down'),
    '上限': t('alarms.upper'),
    '下限': t('alarms.lower'),
    '双限': t('alarms.both_limits'),
    '回温': t('alarms.reheating'),
  }
  return map[dir] || dir
}

function alarmMsg(msg: string): string {
  if (!msg) return msg
  const replacements: [RegExp, string][] = [
    [/预测 /g, t('alarms.msg_pred') + ' '],
    [/核心温度/g, t('sensor.core_temp')],
    [/炉膛压力/g, t('sensor.furnace_pressure')],
    [/燃料流量/g, t('sensor.fuel_flow')],
    [/进风流量/g, t('sensor.air_flow')],
    [/分钟温度/g, t('alarms.msg_min_temp')],
    [/超出上限/g, t('alarms.msg_exceed_upper')],
    [/低于下限/g, t('alarms.msg_below_lower')],
    [/超过阈值/g, t('alarms.msg_exceeds')],
    [/\(限:/g, '(' + t('alarms.msg_limit_label')],
    [/异常/g, t('alarms.msg_abnormal')],
  ]
  let result = msg
  for (const [pattern, replacement] of replacements) {
    result = result.replace(pattern, replacement)
  }
  return result
}

const alarmData = ref<any>(null)
const filterPhase = ref<string | null>(null)
const filterAck = ref<boolean | null>(null)
let updateTimer: number | null = null

function formatTime(ts: string) {
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function phaseTagType(phase: string) {
  if (phase === 'heating') return 'warning'
  if (phase === 'holding') return 'success'
  if (phase === 'cooling') return 'info'
  return 'info'
}

async function fetchData() {
  try {
    const params = new URLSearchParams()
    if (filterPhase.value) params.set('phase', filterPhase.value)
    if (filterAck.value !== null) params.set('acknowledged', String(filterAck.value))
    const qs = params.toString() ? `?${params.toString()}` : ''
    const res = await fetch(`/api/furnace/alarms${qs}`).then(r => r.json())
    alarmData.value = res.data
  } catch (e) {
    console.error('获取报警记录失败', e)
  }
}

async function ackOne(id: number) {
  try {
    await fetch(`/api/furnace/alarms/${id}/acknowledge`, { method: 'PUT' }).then(r => r.json())
    ElMessage.success(t('alarms.acknowledged'))
    fetchData()
  } catch (e) {
    ElMessage.error(t('alarms.operation_failed'))
  }
}

async function ackAll() {
  try {
    const res = await fetch('/api/furnace/alarms/acknowledge-all', { method: 'PUT' }).then(r => r.json())
    ElMessage.success(`${t('alarms.acknowledged')} ${res.data.count} ${t('alarms.records')}`)
    fetchData()
  } catch (e) {
    ElMessage.error(t('alarms.operation_failed'))
  }
}

watch([filterPhase, filterAck], () => { fetchData() })

onMounted(() => {
  fetchData()
  updateTimer = window.setInterval(fetchData, 5000)
})

onUnmounted(() => {
  if (updateTimer) clearInterval(updateTimer)
})
</script>

<style scoped>
.alarms-view {
  padding: 20px;
}

.stat-card { margin-bottom: 20px; }
.stat-content { display: flex; align-items: center; gap: 16px; }
.stat-icon {
  width: 56px; height: 56px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; color: white;
}
.stat-info { flex: 1; }
.stat-value { font-size: 28px; font-weight: bold; color: #333; }
.stat-title { font-size: 14px; color: #909399; margin-top: 4px; }

.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.filter-left {
  display: flex;
  gap: 12px;
}

.temp-danger { color: #f56c6c; font-weight: bold; }
.old-val { color: #f56c6c; text-decoration: line-through; }
.new-val { color: #67c23a; font-weight: bold; }
.detail-text { font-size: 12px; color: #606266; }
.ack-text { color: #c0c4cc; }
</style>
