<template>
  <el-container class="layout-container">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <h2 v-if="!isCollapse">{{ t('app.logo') }}</h2>
        <h2 v-else>{{ t('app.logo.short') }}</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        background-color="#001529"
        text-color="#bfcbd9"
        active-text-color="#1890ff"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <template #title>{{ t('menu.dashboard') }}</template>
        </el-menu-item>
        <el-menu-item index="/sensors">
          <el-icon><DataBoard /></el-icon>
          <template #title>{{ t('menu.sensors') }}</template>
        </el-menu-item>
        <el-menu-item index="/alarms">
          <el-icon><Bell /></el-icon>
          <template #title>{{ t('menu.alarms') }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container class="main-container">
      <el-header class="header">
        <div class="header-left">
          <el-icon class="toggle-btn" @click="toggleCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
        </div>
        <div class="header-center">
          <span class="header-title">{{ t('app.title') }}</span>
        </div>
        <div class="header-right">
          <el-dropdown trigger="click" @command="handleLocaleChange">
            <span class="locale-btn">
              <span style="margin-right:2px;">&#127760;</span>
              <span>{{ localeNames[currentLocale] }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item
                  v-for="(name, key) in localeNames"
                  :key="key"
                  :command="key"
                  :class="{ active: currentLocale === key }"
                >
                  {{ name }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Fold, Expand, Odometer, DataBoard, Bell, ArrowDown } from '@element-plus/icons-vue'
import { useLocaleStore } from '@/stores/locale'
import { localeNames, type Locale } from '@/utils/i18n'

const route = useRoute()
const localeStore = useLocaleStore()
const { t, setLocale } = localeStore

const currentLocale = computed(() => localeStore.locale)

const isCollapse = ref(false)

const activeMenu = computed(() => route.path)

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
}

const handleLocaleChange = (lang: string) => {
  setLocale(lang as Locale)
}
</script>

<style scoped>
.layout-container {
  height: 100vh;
}

.aside {
  background-color: #001529;
  transition: width 0.3s;
  overflow-x: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #002140;
}

.logo h2 {
  color: white;
  font-size: 18px;
  margin: 0;
  white-space: nowrap;
}

.el-menu {
  border-right: none;
}

.main-container {
  display: flex;
  flex-direction: column;
}

.header {
  background-color: white;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
  height: 60px;
}

.header-left {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
}

.header-center {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
}

.header-right {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
}

.toggle-btn {
  font-size: 20px;
  cursor: pointer;
  color: #333;
}

.toggle-btn:hover {
  color: #1890ff;
}

.header-title {
  font-size: 18px;
  font-weight: bold;
  color: #333;
}

.locale-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  font-size: 14px;
  color: #333;
  padding: 6px 12px;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.locale-btn:hover {
  background-color: #f0f2f5;
}

.locale-btn .el-icon {
  font-size: 16px;
}

.main-content {
  background-color: #f0f2f5;
  padding: 0;
  overflow-y: auto;
}
</style>
