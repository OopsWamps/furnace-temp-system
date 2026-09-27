<template>
  <div class="alarm">
    <el-card>
      <template #header>
        <span>{{ t('alarm.title') }}</span>
      </template>
      <el-table :data="alarmList" style="width: 100%">
        <el-table-column prop="time" :label="t('alarms.time')" width="180" />
        <el-table-column prop="level" :label="t('alarms.level')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.level === '严重' ? 'danger' : 'warning'">
              {{ row.level }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type" :label="t('alarms.type')" width="150" />
        <el-table-column prop="description" :label="t('alarms.description')" />
        <el-table-column prop="status" :label="t('alarms.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === '已处理' ? 'success' : 'info'">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('alarms.action')" width="120">
          <template #default>
            <el-button type="primary" link size="small">{{ t('alarms.process') }}</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useLocaleStore } from '@/stores/locale'

const localeStore = useLocaleStore()

function t(key: string): string {
  void localeStore.locale
  return localeStore.t(key)
}

const alarmList = ref([
  {
    time: '2026-05-19 14:30:00',
    level: '严重',
    type: '温度告警',
    description: '核心温度超过阈值 (810°C)',
    status: '待处理'
  },
  {
    time: '2026-05-19 12:15:00',
    level: '警告',
    type: '压力告警',
    description: '炉膛压力异常',
    status: '已处理'
  }
])
</script>

<style scoped>
</style>
