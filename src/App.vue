<template>
  <div class="app-wrapper">
    <TitleBar />
    <el-container class="app-container">
    <!-- Header -->
    <el-header class="app-header">
      <div class="header-left">
        <div class="stat-item">
          <span class="stat-dot running"></span>
          <span>运行中 <strong>{{ stats.running }}</strong></span>
        </div>
        <span class="stat-divider">|</span>
        <div class="stat-item">
          <span class="stat-dot stopped"></span>
          <span>已停止 <strong>{{ stats.stopped }}</strong></span>
        </div>
        <span class="stat-divider">|</span>
        <div class="stat-item">
          <span class="stat-dot failed"></span>
          <span>异常 <strong>{{ stats.failed }}</strong></span>
        </div>
      </div>
      <div class="header-right">
        <el-button :icon="Setting" circle @click="settingsVisible = true" />
        <el-button type="primary" :icon="Plus" @click="showAddDialog">新增服务</el-button>
      </div>
    </el-header>

    <!-- Offline banner -->
    <el-alert
      v-if="!backendOnline && !loading" title="后端未连接" type="warning" show-icon :closable="false"
    >
      <span style="margin-right:12px">{{ lastError || '请确保 Python 后端已启动（localhost:8710）' }}</span>
      <el-button size="small" @click="loadServices">重试</el-button>
    </el-alert>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-button
          :type="batchMode ? 'warning' : 'default'"
          :icon="Select"
          size="small"
          @click="toggleBatchMode"
        >{{ batchMode ? '退出批量' : '批量选择' }}</el-button>
      </div>
      <div class="toolbar-right">
        <el-input v-model="searchQuery" placeholder="搜索..." :prefix-icon="Search" clearable class="search-input" />
      </div>
    </div>

    <!-- Body area: main + log + status bar 统一管理高度 -->
    <div class="body-area">
      <!-- Main -->
      <el-main class="app-main">
        <div v-if="loading" class="loading-container"><el-skeleton :rows="4" animated /></div>
        <el-empty v-else-if="!services.length && backendOnline" description="还没有服务，点击右上角添加吧" :image-size="100">
          <el-button type="primary" :icon="Plus" @click="showAddDialog">新增服务</el-button>
        </el-empty>

        <!-- Service list -->
        <div v-else-if="services.length" class="grouped-view">
          <div v-for="group in visibleGroups" :key="group.key" class="group-section">
            <div v-if="group.showHeader" class="group-header">
              <div class="group-title">
                <span class="group-badge" :style="{ background: group.color }"></span>
                <span class="group-name">{{ group.label }}</span>
                <el-tag size="small" type="info" effect="plain">{{ group.count }} 个</el-tag>
              </div>
            </div>
            <div v-else class="group-divider"></div>
            <div class="service-grid">
              <ServiceCard
                v-for="svc in group.services" :key="svc.id"
                :service="svc"
                :status="getStatus(svc.id)"
                :detected-port="detectedPorts[svc.id]"
                :starting="!!startingMap[svc.id]"
                :show-logs="activeLogTab === svc.id"
                :disabled="!backendOnline"
                :batch-mode="batchMode"
                :selected="!!selectedMap[svc.id]"
                @start="handleStart"
                @stop="handleStop"
                @edit="handleEdit"
                @delete="handleDelete"
                @toggle-log="handleToggleLog"
                @toggle-select="toggleSelect"
              />
            </div>
          </div>
        </div>
      </el-main>

      <!-- Batch action bar -->
      <div v-if="batchMode && selectedCount > 0" class="batch-bar">
        <span class="batch-info">已选择 {{ selectedCount }} 个服务</span>
        <div class="batch-actions">
          <el-button size="small" type="success" plain :icon="VideoPlay" :disabled="!backendOnline || batRunning" @click="batchStartSelected">
            {{ batRunning ? `启动中 ${batDone}/${batTotal}` : '启动选中' }}
          </el-button>
          <el-button size="small" type="danger" plain :icon="VideoPause" :disabled="!backendOnline || batRunning" @click="batchStopSelected">
            {{ batRunning ? `停止中 ${batDone}/${batTotal}` : '停止选中' }}
          </el-button>
          <el-button size="small" text @click="clearSelection">取消选择</el-button>
        </div>
      </div>

      <!-- Log panel -->
      <div v-if="showLogPanel" class="log-resize-handle" @mousedown="startResize"></div>
      <div v-if="showLogPanel" class="log-wrapper" :style="{ height: logHeight + 'px' }">
        <LogPanel
          :services="services" :statuses="statuses" :logs-map="logsMap" :active-tab="activeLogTab"
          :starting-map="startingMap"
          @close="showLogPanel = false" @tab-change="onLogTabChange"
          @start="handleStart" @stop="handleStop"
        />
      </div>

    </div>

    <ServiceForm v-model:visible="formVisible" :service="editingService" @confirm="handleConfirm" />
    <SettingsDialog v-model:visible="settingsVisible" :settings="settings" @update:settings="onSettingsChange" @services-imported="loadServices" />
  </el-container>
</div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted } from 'vue'
import { Plus, Search, Select, VideoPlay, VideoPause, Setting } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ServiceCard from './components/ServiceCard.vue'
import ServiceForm from './components/ServiceForm.vue'
import LogPanel from './components/LogPanel.vue'
import TitleBar from './components/TitleBar.vue'
import SettingsDialog from './components/SettingsDialog.vue'
import { getGroupColor, THEMES, FONT_SIZES, FONT_FAMILIES } from './constants.js'
import * as api from './api/index.js'

// ─── State ───
const services = ref([])
const statuses = reactive({})
const detectedPorts = reactive({})
const logsMap = reactive({})
const loading = ref(true)
const lastError = ref('')
const backendOnline = ref(false)
const formVisible = ref(false)
const editingService = ref(null)
const showLogPanel = ref(false)
const activeLogTab = ref('')
const logHeight = ref(250)
const searchQuery = ref('')
const startingMap = reactive({})
const failedMap = reactive({})
// Batch mode
const batchMode = ref(false)
const selectedMap = reactive({})
const batRunning = ref(false)
const batTotal = ref(0)
const batDone = ref(0)

// ─── Settings ───
const DEFAULT_SETTINGS = {
  theme: 'light',
  fontSize: 'medium',
  fontFamily: 'system',
}
const settings = reactive({ ...DEFAULT_SETTINGS })
const settingsVisible = ref(false)
let systemThemeListener = null

function loadSettings() {
  try {
    const saved = localStorage.getItem('onestopservice-settings')
    if (saved) Object.assign(settings, JSON.parse(saved))
  } catch { /* ignore */ }
}

function applyTheme(theme) {
  const html = document.documentElement
  html.classList.remove('theme-cream', 'dark')
  const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  if (isDark) html.classList.add('dark')
  else if (theme === 'cream') html.classList.add('theme-cream')
}

function applyFontSize(size) {
  const sizeMap = { small: '12px', medium: '14px', large: '16px' }
  const base = sizeMap[size] || '14px'
  const basePx = parseInt(base)
  const el = document.documentElement
  el.style.setProperty('--el-font-size-base', base)
  el.style.setProperty('--el-font-size-small', Math.max(11, basePx - 2) + 'px')
  el.style.setProperty('--el-font-size-large', (basePx + 2) + 'px')
  el.style.setProperty('--el-font-size-extra-large', (basePx + 4) + 'px')
  document.body.style.fontSize = base
}

function applyFontFamily(key) {
  const f = FONT_FAMILIES.find(x => x.key === key)
  document.documentElement.style.setProperty('--app-font-family', f?.value || FONT_FAMILIES[0].value)
}

function applySettings(s) {
  applyTheme(s.theme)
  applyFontSize(s.fontSize)
  applyFontFamily(s.fontFamily)
}

function onSettingsChange(s) {
  Object.assign(settings, s)
  applySettings(settings)
  localStorage.setItem('onestopservice-settings', JSON.stringify(settings))
}

// Watch system theme changes
function setupSystemThemeListener() {
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  systemThemeListener = () => {
    if (settings.theme === 'system') applyTheme('system')
  }
  mq.addEventListener('change', systemThemeListener)
}

// ─── Computed ───
const selectedCount = computed(() => Object.values(selectedMap).filter(Boolean).length)

const stats = computed(() => {
  let running = 0, stopped = 0, failed = 0
  for (const svc of services.value) {
    const s = getStatus(svc.id)
    if (s === 'running') running++
    else if (s === 'failed') failed++
    else stopped++
  }
  return { running, stopped, failed }
})

function getStatus(id) {
  if (failedMap[id]) return 'failed'
  return statuses[id] || 'stopped'
}

const filteredServices = computed(() => {
  let list = services.value
  const q = searchQuery.value.trim().toLowerCase()
  if (q) list = list.filter(s =>
    [s.name, s.group, s.version, s.command, s.id].some(f => (f || '').toLowerCase().includes(q))
  )
  return list
})

const visibleGroups = computed(() => {
  const filtered = filteredServices.value
  if (!filtered.length) return []
  const map = {}
  for (const svc of filtered) {
    const key = svc.group || '__ungrouped__'
    if (!map[key]) map[key] = { key, label: svc.group || '其他', services: [], count: 0, color: getGroupColor(svc.group), showHeader: !!svc.group }
    map[key].services.push(svc); map[key].count++
  }
  return Object.values(map).sort((a, b) => {
    if (a.key === '__ungrouped__') return 1; if (b.key === '__ungrouped__') return -1
    return a.label.localeCompare(b.label)
  })
})

// ─── Health & Data (WebSocket + HTTP 降级兜底) ───
let ws = null
let wsReconnectTimer = null
let wsRetryCount = 0
const WS_URL = 'ws://localhost:8710/api/ws'
const MAX_WS_RETRY = 10
let httpFallbackTimer = null
let logPollTimer = null

async function checkHealth() {
  try { await api.healthCheck(); backendOnline.value = true; return true }
  catch { backendOnline.value = false; return false }
}

async function loadServices() {
  try {
    if (!await checkHealth()) { loading.value = false; return }
    lastError.value = ''
    const data = await api.fetchServices()
    applyServiceData(data)
  } catch (e) { lastError.value = e.message }
  finally { loading.value = false }
}

function applyServiceData(data) {
  services.value = data.services || []
  Object.assign(statuses, data.statuses || {})
  Object.assign(detectedPorts, data.ports || {})
  for (const [id, st] of Object.entries(data.statuses || {})) {
    if (st === 'running') delete failedMap[id]
  }
}

// ─── WebSocket ───
function connectWebSocket() {
  if (ws) return
  try {
    ws = new WebSocket(WS_URL)
    ws.onopen = () => {
      wsRetryCount = 0
      stopHttpFallback()
    }
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'services') {
          applyServiceData(data)
        }
      } catch { /* ignore parse errors */ }
    }
    ws.onclose = () => {
      ws = null
      scheduleWsReconnect()
    }
    ws.onerror = () => {
      // onclose 会在 onerror 后自动触发，重连逻辑在里面处理
    }
  } catch {
    scheduleWsReconnect()
  }
}

function scheduleWsReconnect() {
  if (wsReconnectTimer) return
  if (wsRetryCount >= MAX_WS_RETRY) {
    startHttpFallback()
    return
  }
  const delay = Math.min(1000 * Math.pow(2, wsRetryCount), 30000)
  wsRetryCount++
  wsReconnectTimer = setTimeout(() => {
    wsReconnectTimer = null
    connectWebSocket()
  }, delay)
}

function stopWsReconnect() {
  if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null }
}

// ─── HTTP 降级兜底（WebSocket 连不上时） ───
function startHttpFallback() {
  if (httpFallbackTimer) return
  backendOnline.value = false
  httpFallbackTimer = setInterval(async () => {
    if (!await checkHealth()) return
    try {
      const data = await api.fetchServices()
      applyServiceData(data)
    } catch {}
    if (showLogPanel.value && activeLogTab.value) {
      try { logsMap[activeLogTab.value] = (await api.fetchLogs(activeLogTab.value)).logs || [] } catch {}
    }
  }, 10000) // HTTP 降级时每 10s 拉一次，不再是 1s
}

function stopHttpFallback() {
  if (httpFallbackTimer) { clearInterval(httpFallbackTimer); httpFallbackTimer = null }
}

// ─── 日志轮询（日志面板打开时才启动） ───
function startLogPolling() {
  if (logPollTimer) return
  logPollTimer = setInterval(async () => {
    if (!showLogPanel.value || !activeLogTab.value) return
    try { logsMap[activeLogTab.value] = (await api.fetchLogs(activeLogTab.value)).logs || [] } catch {}
  }, 3000) // 日志 3s 轮询一次
}

function stopLogPolling() {
  if (logPollTimer) { clearInterval(logPollTimer); logPollTimer = null }
}

// 用 watch 监听日志面板状态变化来自动启停日志轮询
watch([showLogPanel, activeLogTab], ([panel, tab]) => {
  if (panel && tab) startLogPolling()
  else stopLogPolling()
})

onMounted(() => {
  loadSettings()
  applySettings(settings)
  setupSystemThemeListener()
  // 初始 HTTP 加载 + 健康检查
  loadServices().then(() => {
    // 然后再尝试 WebSocket
    connectWebSocket()
  })
})
onUnmounted(() => {
  if (ws) { ws.onclose = null; ws.close(); ws = null }
  stopWsReconnect()
  stopHttpFallback()
  stopLogPolling()
  if (systemThemeListener) {
    window.matchMedia('(prefers-color-scheme: dark)').removeEventListener('change', systemThemeListener)
  }
})

// ─── Batch Mode ───
function toggleBatchMode() {
  batchMode.value = !batchMode.value
  if (!batchMode.value) clearSelection()
}

function toggleSelect(id) {
  selectedMap[id] = !selectedMap[id]
}

function clearSelection() {
  Object.keys(selectedMap).forEach(k => delete selectedMap[k])
}

async function batchStartSelected() {
  const ids = Object.entries(selectedMap).filter(([, v]) => v).map(([k]) => k)
  if (!ids.length) return
  const toStart = ids.filter(id => getStatus(id) !== 'running')
  const alreadyRunning = ids.length - toStart.length
  if (!toStart.length) {
    ElMessage.info('所选服务均已运行中')
    return
  }
  batRunning.value = true; batTotal.value = toStart.length; batDone.value = 0
  toStart.forEach(id => { startingMap[id] = true })
  try {
    const res = await api.batchStart(toStart)
    const results = res.results || {}
    let success = 0, failed = []
    for (const id of toStart) {
      if (results[id]?.ok) { success++; delete failedMap[id] }
      else { failed.push(id); failedMap[id] = true }
    }
    batDone.value = success + failed.length
    let msg = `成功 ${success} 个`
    if (failed.length) msg += `，失败 ${failed.length} 个`
    if (alreadyRunning) msg += `，${alreadyRunning} 个已跳过`
    if (failed.length) {
      const names = failed.map(id => services.value.find(s => s.id === id)?.name || id).join('、')
      ElMessage.warning(`${msg}，失败: ${names}`)
    } else {
      ElMessage.success(msg)
    }
  } catch (e) {
    ElMessage.error('批量启动失败: ' + e.message)
  } finally {
    toStart.forEach(id => { delete startingMap[id] })
    batRunning.value = false
  }
}

async function batchStopSelected() {
  const ids = Object.entries(selectedMap).filter(([, v]) => v).map(([k]) => k)
  if (!ids.length) return
  batRunning.value = true; batTotal.value = ids.length; batDone.value = 0
  try {
    const res = await api.batchStop(ids)
    const results = res.results || {}
    let success = 0, failed = []
    for (const id of ids) {
      if (results[id]?.ok) { success++; statuses[id] = 'stopped'; delete failedMap[id] }
      else { failed.push(id) }
    }
    batDone.value = success + failed.length
    let msg = `成功 ${success} 个`
    if (failed.length) {
      const names = failed.map(id => services.value.find(s => s.id === id)?.name || id).join('、')
      msg += `，失败 ${failed.length} 个: ${names}`
      ElMessage.warning(msg)
    } else {
      ElMessage.success(msg)
    }
  } catch (e) {
    ElMessage.error('批量停止失败: ' + e.message)
  } finally {
    batRunning.value = false
  }
}

// ─── Service Actions ───
function showAddDialog() { editingService.value = null; formVisible.value = true }

async function handleConfirm(payload, isEdit) {
  try {
    if (isEdit) { await api.updateService(payload.id, payload) }
    else { await api.addService(payload) }
    formVisible.value = false // 立即关闭弹窗，不阻塞用户操作
    // 直接拉取最新数据（跳过健康检查，刚保存成功说明后端在线）
    const data = await api.fetchServices()
    services.value = data.services || []
    Object.assign(statuses, data.statuses || {})
    Object.assign(detectedPorts, data.ports || {})
    ElMessage.success(isEdit ? '服务已更新' : '服务已添加')
  } catch (e) { ElMessage.error(e.message) }
}

function handleEdit(svc) { editingService.value = svc; formVisible.value = true }

async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定要删除该服务吗？', '确认删除', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
    await api.deleteService(id)
    const data = await api.fetchServices()
    services.value = data.services || []
    Object.assign(statuses, data.statuses || {})
    Object.assign(detectedPorts, data.ports || {})
    ElMessage.success('已删除')
  } catch (e) { if (e !== 'cancel') ElMessage.error(e.message) }
}

async function handleStart(id) {
  startingMap[id] = true
  const name = services.value.find(s => s.id === id)?.name || id
  try {
    await api.startService(id)
    delete failedMap[id]
    let waited = 0
    while (waited < 5) {
      await new Promise(r => setTimeout(r, 800)); waited += 0.8
      try { const data = await api.fetchServices(); const cur = data.statuses?.[id]
        if (cur === 'running') { statuses[id] = 'running'; ElMessage.success(`${name} 启动成功`); delete startingMap[id]; return }
      } catch {}
    }
    ElMessage.error(`${name} 启动失败，详见日志`)
    failedMap[id] = true
  } catch (e) { ElMessage.error(e.message); failedMap[id] = true }
  finally { delete startingMap[id] }
}

async function handleStop(id) {
  try {
    await api.stopService(id); statuses[id] = 'stopped'; delete failedMap[id]
    ElMessage.success(`${services.value.find(s => s.id === id)?.name} 已停止`)
  } catch (e) { ElMessage.error(e.message) }
}

function handleToggleLog(id) {
  if (showLogPanel.value && activeLogTab.value === id) { showLogPanel.value = false; activeLogTab.value = '' }
  else { activeLogTab.value = id; showLogPanel.value = true; fetchLogsForTab(id) }
}

function onLogTabChange(tabId) { activeLogTab.value = tabId; fetchLogsForTab(tabId) }

async function fetchLogsForTab(id) {
  try { logsMap[id] = (await api.fetchLogs(id)).logs || [] } catch { logsMap[id] = ['[获取日志失败]'] }
}

function startResize(e) {
  const startY = e.clientY; const startH = logHeight.value
  function onMove(ev) { logHeight.value = Math.max(100, Math.min(600, startH + (startY - ev.clientY))) }
  function onUp() { document.removeEventListener('mousemove', onMove); document.removeEventListener('mouseup', onUp) }
  document.addEventListener('mousemove', onMove); document.addEventListener('mouseup', onUp)
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
html, body, #app { height: 100%; overflow: hidden; }

/* 全局滚动条美化 */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
  background: var(--el-border-color-darker, #c0c4cc);
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: var(--el-text-color-placeholder, #909399);
}

/* ─── Cream Theme ─── */
.theme-cream {
  --el-bg-color: #faf6f0;
  --el-bg-color-page: #f2ece4;
  --el-bg-color-overlay: #faf6f0;
  --el-text-color-primary: #4a4a4a;
  --el-text-color-regular: #5a5a5a;
  --el-text-color-secondary: #8a8a8a;
  --el-border-color: #e5ddd2;
  --el-border-color-light: #eae3d8;
  --el-border-color-lighter: #efe8de;
  --el-border-color-extra-light: #f4eee6;
  --el-fill-color: #ede6dc;
  --el-fill-color-light: #f2ece4;
  --el-fill-color-lighter: #f8f2ea;
  --el-fill-color-extra-light: #fcf9f5;
  --el-fill-color-dark: #e0d8cc;
  --el-color-primary: #b88a6e;
  --el-color-primary-light-3: #cda88e;
  --el-color-primary-light-5: #e0c4b0;
  --el-color-primary-light-7: #ede0d4;
  --el-color-primary-light-8: #f5ede6;
  --el-color-primary-light-9: #faf5f0;
  --el-color-primary-dark-2: #9c7056;
  --el-color-success: #8fb88a;
  --el-color-warning: #d4a86a;
  --el-color-danger: #c97c7c;
  --el-color-info: #b0a898;
  --el-box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  --el-box-shadow-light: 0 1px 2px rgba(0,0,0,0.05);
}

/* ─── Font Family ─── */
body { font-family: var(--app-font-family, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif); }
</style>

<style scoped>
.app-wrapper { height: 100%; display: flex; flex-direction: column; }
.app-container { flex: 1; overflow: hidden; display: flex; flex-direction: column; min-height: 0; }
.app-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 20px; background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color); height: 52px !important; flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 8px; }
.header-left .stat-item { display: flex; align-items: center; gap: 4px; font-size: 13px; color: var(--el-text-color-regular); }
.header-left .stat-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.header-left .stat-dot.running { background: #67c23a; }
.header-left .stat-dot.stopped { background: #909399; }
.header-left .stat-dot.failed { background: #f56c6c; }
.header-left .stat-divider { color: var(--el-border-color); font-size: 13px; user-select: none; }
.header-left strong { font-weight: 600; }
.header-title { font-size: 18px; font-weight: 700; color: var(--el-text-color-primary); }

.toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 20px; background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-light); flex-shrink: 0;
  gap: 12px;
}
.toolbar-left { flex: 1; }
.toolbar-right { display: flex; align-items: center; gap: 8px; }
.search-input { width: 240px; }
.search-input :deep(.el-input__wrapper) { height: 32px; }
.search-input :deep(.el-input__inner) { height: 32px; font-size: 13px; }

.body-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; min-height: 0; }
.app-main { flex: 1; overflow-y: auto; padding: 16px 20px; background: var(--el-bg-color-page); min-height: 0; }
.loading-container { padding: 40px; max-width: 400px; margin: 0 auto; }

.group-section { margin-bottom: 16px; }
.group-header { display: flex; align-items: center; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid var(--el-border-color-light); }
.group-title { display: flex; align-items: center; gap: 8px; }
.group-badge { width: 10px; height: 10px; border-radius: 50%; }
.group-name { font-size: 14px; font-weight: 600; color: var(--el-text-color-primary); }
.group-divider { height: 1px; background: var(--el-border-color-light); margin-bottom: 8px; }
.service-grid { display: flex; flex-direction: column; gap: 6px; }

/* Batch bar */
.batch-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 16px; flex-shrink: 0;
  background: var(--el-color-primary-light-9); border-top: 1px solid var(--el-color-primary);
}
.batch-info { font-size: 13px; font-weight: 500; color: var(--el-color-primary); }
.batch-actions { display: flex; gap: 8px; }

.log-resize-handle { height: 4px; cursor: ns-resize; background: var(--el-border-color); flex-shrink: 0; }
.log-resize-handle:hover { background: var(--el-color-primary); }
.log-wrapper { flex-shrink: 0; overflow: hidden; }
</style>
