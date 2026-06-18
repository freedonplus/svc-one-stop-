<template>
  <div class="log-panel">
    <!-- 顶栏 -->
    <div class="log-bar">
      <div class="log-tabs">
        <button
          v-for="svc in services"
          :key="svc.id"
          :class="['log-tab', { active: activeTab === svc.id }]"
          @click="onTabChange(svc.id)"
        >
          <span class="tab-dot" :class="getStatus(svc.id)"></span>
          {{ svc.name }}
        </button>
      </div>
      <div class="log-actions">
        <template v-if="activeTabService">
          <button
            v-if="getStatus(activeTab) === 'running'"
            class="log-bar-btn log-act-btn stop" title="停止"
            @click="$emit('stop', activeTab)"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
          </button>
          <button
            v-else-if="startingMap[activeTab]"
            class="log-bar-btn log-act-btn start spinning" title="启动中" disabled
          >
            <svg class="spin" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5">
              <circle cx="12" cy="12" r="10" stroke-dasharray="31.4 31.4" stroke-linecap="round"/>
            </svg>
          </button>
          <button
            v-else
            class="log-bar-btn log-act-btn start" title="启动"
            @click="$emit('start', activeTab)"
          >
            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
          </button>
          <span class="log-act-sep"></span>
        </template>
        <button class="log-bar-btn" title="清空" @click="clearLogs">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
        <button class="log-bar-btn" title="收起" @click="$emit('close')">
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>
        </button>
      </div>
    </div>

    <!-- 日志内容 -->
    <div class="log-body" ref="logContainer">
      <div v-if="!logs.length" class="log-empty">暂无日志</div>
      <div v-else class="log-content">
        <div
          v-for="(line, i) in logs"
          :key="i"
          :class="['log-line', { 'log-sys': line.startsWith('[系统]') }]"
        >{{ line }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import * as api from '../api/index.js'

const props = defineProps({
  services: { type: Array, default: () => [] },
  statuses: { type: Object, default: () => ({}) },
  logsMap: { type: Object, default: () => ({}) },
  activeTab: { type: String, default: '' },
  startingMap: { type: Object, default: () => ({}) },
})

const emit = defineEmits(['close', 'tabChange', 'start', 'stop'])

const logContainer = ref(null)
const logs = ref([])

function getStatus(id) { return props.statuses[id] || 'stopped' }

const activeTabService = computed(() =>
  props.services.find(s => s.id === props.activeTab)
)

watch(
  () => ({ tab: props.activeTab, map: props.logsMap[props.activeTab] }),
  ({ tab, map }) => {
    const wasNearBottom = isNearBottom()
    logs.value = map || []
    if (wasNearBottom) scrollToBottom()
  },
  { immediate: true }
)

function onTabChange(tabId) {
  logs.value = props.logsMap[tabId] || []
  emit('tabChange', tabId)
  scrollToBottom()
}

function isNearBottom(threshold = 30) {
  const el = logContainer.value
  if (!el) return true
  return el.scrollHeight - el.scrollTop - el.clientHeight < threshold
}

function scrollToBottom() {
  nextTick(() => { if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight })
}

async function clearLogs() {
  if (props.activeTab) {
    try { await api.clearLogs(props.activeTab) } catch {}
  }
  logs.value = []
}
</script>

<style scoped>
.log-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #1a1a1a;
}

/* ─── 顶栏 ─── */
.log-bar {
  display: flex; align-items: center; justify-content: space-between;
  flex-shrink: 0;
  padding: 6px 10px;
  background: #222;
  border-bottom: 1px solid #333;
}

.log-tabs { display: flex; gap: 2px; overflow-x: auto; flex: 1; }

.log-tab {
  display: flex; align-items: center; gap: 4px;
  padding: 4px 10px; font-size: 12px;
  border: none; border-radius: 4px;
  background: transparent; color: #999;
  cursor: pointer; white-space: nowrap;
  transition: all .12s;
}
.log-tab:hover { background: #333; color: #ddd; }
.log-tab.active { background: #333; color: #fff; }

.tab-dot {
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}
.tab-dot.running { background: var(--el-color-success); }
.tab-dot.stopped { background: #555; }

.log-actions { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }

.log-act-sep { width: 1px; height: 16px; background: #444; margin: 0 4px; flex-shrink: 0; }
.log-act-btn.start { color: var(--el-color-success); }
.log-act-btn.stop { color: var(--el-color-danger); }
.log-act-btn.start.spinning { color: var(--el-color-warning); }
.log-act-btn.start.spinning .spin { animation: logspin .8s linear infinite; }
@keyframes logspin { to { transform: rotate(360deg); } }

.log-bar-btn {
  width: 24px; height: 24px; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  border: none; cursor: pointer;
  background: transparent; color: #888;
  transition: all .12s;
}
.log-bar-btn:hover { background: #333; color: #fff; }

/* ─── 日志内容 ─── */
.log-body {
  flex: 1; overflow-y: auto; padding: 6px 10px;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 12px; line-height: 1.6;
}

.log-empty {
  display: flex; justify-content: center; align-items: center;
  height: 100%; color: #555; font-size: 13px;
}

.log-content { color: #ccc; }

.log-line { white-space: pre-wrap; word-break: break-all; }
.log-line:hover { background: rgba(255,255,255,.03); }

.log-sys { color: #67c23a; font-weight: 500; }
.log-sys::before { content: '◆ '; }
</style>
