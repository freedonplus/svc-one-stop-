<template>
  <div class="title-bar" data-tauri-drag-region>
    <div class="title-bar-left" data-tauri-drag-region>
      <img src="/icon.png" class="app-icon" alt="OneStopService" />
      <span class="title-text">OneStopService</span>
      <span class="title-subtitle">本地服务一条龙管理</span>
    </div>

    <div class="title-bar-center" data-tauri-drag-region />

    <div class="title-bar-right">
      <div class="window-btn minimize" @click="minimize" title="最小化">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <rect x="1" y="5.5" width="10" height="1" fill="currentColor" />
        </svg>
      </div>
      <div class="window-btn maximize" @click="toggleMaximize" :title="isMaximized ? '还原' : '最大化'">
        <!-- Maximize: single rect outline -->
        <svg v-if="!isMaximized" width="12" height="12" viewBox="0 0 12 12">
          <rect x="1.5" y="1.5" width="9" height="9" rx="0.5" fill="none" stroke="currentColor" stroke-width="1.1" />
        </svg>
        <!-- Restore: two overlapping rects -->
        <svg v-else width="12" height="12" viewBox="0 0 12 12">
          <rect x="2.5" y="0.5" width="9" height="9" rx="0.5" fill="none" stroke="currentColor" stroke-width="1" />
          <rect x="0.5" y="2.5" width="9" height="9" rx="0.5" fill="none" stroke="currentColor" stroke-width="1" />
        </svg>
      </div>
      <div class="window-btn close" @click="closeWindow" title="关闭">
        <svg width="12" height="12" viewBox="0 0 12 12">
          <line x1="2" y1="2" x2="10" y2="10" stroke="currentColor" stroke-width="1.2" />
          <line x1="10" y1="2" x2="2" y2="10" stroke="currentColor" stroke-width="1.2" />
        </svg>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const isMaximized = ref(false)
let unlisten = null

async function minimize() {
  const { getCurrentWindow } = await import('@tauri-apps/api/window')
  await getCurrentWindow().minimize()
}

async function toggleMaximize() {
  const { getCurrentWindow } = await import('@tauri-apps/api/window')
  await getCurrentWindow().toggleMaximize()
}

async function closeWindow() {
  const { getCurrentWindow } = await import('@tauri-apps/api/window')
  await getCurrentWindow().close()
}

onMounted(async () => {
  try {
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    const win = getCurrentWindow()
    isMaximized.value = await win.isMaximized()

    // Listen for resize events to update maximize/restore icon
    unlisten = await win.onResized(async () => {
      isMaximized.value = await win.isMaximized()
    })
  } catch {
    // Not running in Tauri environment (browser dev), silently skip
  }
})

onUnmounted(() => {
  if (unlisten) unlisten()
})
</script>

<style scoped>
.title-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 32px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color);
  user-select: none;
  flex-shrink: 0;
  padding: 0 0 0 12px;
  /* Prevent accidental text selection while dragging */
  -webkit-user-select: none;
}

.title-bar-left {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 100%;
  min-width: 0;
}

.app-icon {
  width: 18px;
  height: 18px;
  border-radius: 3px;
}

.title-text {
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
}

.title-subtitle {
  font-size: 11px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.title-bar-center {
  flex: 1;
  height: 100%;
}

.title-bar-right {
  display: flex;
  align-items: center;
  height: 100%;
}

/* ─── Window Control Buttons ─── */
.window-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 100%;
  cursor: pointer;
  color: var(--el-text-color-secondary);
  transition: background 0.12s, color 0.12s;
}

.window-btn:hover {
  background: var(--el-fill-color-light);
  color: var(--el-text-color-primary);
}

.window-btn.close:hover {
  background: #e81123;
  color: #fff;
}

/* Highlight when window is maximized — show the restore icon stands out */
.window-btn.maximize:hover {
  background: var(--el-fill-color-light);
}
</style>
