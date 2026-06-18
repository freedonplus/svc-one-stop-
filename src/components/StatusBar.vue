<template>
  <div class="status-bar">
    <div class="status-left">
      <span class="status-item">
        <el-icon :size="14"><Connection /></el-icon>
        后端: {{ backendConnected ? '已连接' : '未连接' }}
        <span
          class="inline-dot"
          :class="backendConnected ? 'connected' : 'disconnected'"
        ></span>
      </span>
    </div>
    <div class="status-right">
      <span class="status-item">
        共 {{ total }} 个服务
      </span>
      <span class="status-item running-count">
        🟢 {{ runningCount }} 运行中
      </span>
      <span class="status-item stopped-count">
        ⚪ {{ stoppedCount }} 已停止
      </span>
      <span v-if="failedCount > 0" class="status-item failed-count">
        🔴 {{ failedCount }} 启动失败
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Connection } from '@element-plus/icons-vue'

const props = defineProps({
  services: { type: Array, default: () => [] },
  statuses: { type: Object, default: () => ({}) },
  failedCount: { type: Number, default: 0 },
  backendConnected: { type: Boolean, default: false },
})

const total = computed(() => props.services.length)

const runningCount = computed(() =>
  props.services.filter(s => props.statuses[s.id] === 'running').length
)

const stoppedCount = computed(() => total.value - runningCount.value)
</script>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 28px;
  flex-shrink: 0;
  background: var(--el-fill-color-light);
  border-top: 1px solid var(--el-border-color);
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.status-left,
.status-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-item {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.inline-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  margin-top: 3px;
}
.inline-dot.connected { background: var(--el-color-success); }
.inline-dot.disconnected { background: var(--el-color-danger); }

.running-count { color: var(--el-color-success); }
.stopped-count { color: var(--el-color-info); }
.failed-count { color: var(--el-color-danger); }
</style>
