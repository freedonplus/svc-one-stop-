<template>
  <div :class="['svc-row', status, { selected }]" :style="{ borderLeftColor: resolvedColor }">
    <!-- 多选 checkbox -->
    <div v-if="batchMode" class="svc-check" @click.stop="$emit('toggle-select', service.id)">
      <svg v-if="selected" viewBox="0 0 24 24" width="16" height="16" fill="var(--el-color-primary)">
        <path d="M19 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V5a2 2 0 0 0-2-2zm-9 14l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
      </svg>
      <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="var(--el-text-color-placeholder)" stroke-width="2">
        <rect x="3" y="3" width="18" height="18" rx="3"/>
      </svg>
    </div>

    <!-- 状态灯 + 名称 -->
    <div class="svc-left">
      <span class="svc-dot" :class="status" :title="statusTitle"></span>
      <span class="svc-name">{{ service.name }}</span>
      <span v-if="service.group" class="svc-group-tag" :style="{ color: groupColor, background: groupColor + '18' }">{{ service.group }}</span>
      <span v-if="service.version" class="svc-tag">{{ service.version }}</span>
          <a v-if="displayPort" class="port-tag" :href="`http://localhost:${displayPort}`" target="_blank" title="在浏览器中打开">
        :{{ displayPort }}
      </a>
    </div>

    <!-- 访问地址 -->
    <div class="svc-mid">
      <a v-if="service.url && status === 'running'" class="svc-url" :href="service.url" target="_blank" title="在浏览器中打开">
        {{ service.url }}
      </a>
    </div>

    <!-- 操作按钮 -->
    <div class="svc-right">
      <el-tooltip :content="status === 'running' ? '停止' : (starting ? '启动中' : '启动')" placement="top">
        <button
          v-if="status === 'running'"
          class="row-btn stop" :disabled="disabled"
          @click="$emit('stop', service.id)"
        >
          <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
        </button>
        <button
          v-else class="row-btn start" :class="{ spinning: starting }"
          :disabled="disabled || starting"
          @click="$emit('start', service.id)"
        >
          <svg v-if="starting" class="spin" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.5">
            <circle cx="12" cy="12" r="10" stroke-dasharray="31.4 31.4" stroke-linecap="round"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" width="15" height="15" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>
        </button>
      </el-tooltip>

      <el-tooltip content="日志" placement="top">
        <button class="row-btn" :disabled="disabled" @click="$emit('toggleLog', service.id)">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
        </button>
      </el-tooltip>

      <el-dropdown trigger="click" @command="handleCommand" :disabled="disabled">
        <button class="row-btn" :disabled="disabled">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor"><circle cx="12" cy="5" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="12" cy="19" r="2"/></svg>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="edit" :icon="Edit">编辑</el-dropdown-item>
            <el-dropdown-item command="delete" :icon="Delete" divided style="color:var(--el-color-danger)">删除</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Edit, Delete } from '@element-plus/icons-vue'
import { getGroupColor } from '../constants.js'

const props = defineProps({
  service: { type: Object, required: true },
  status: { type: String, default: 'stopped' },
  detectedPort: { type: Number, default: null },
  showLogs: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  starting: { type: Boolean, default: false },
  batchMode: { type: Boolean, default: false },
  selected: { type: Boolean, default: false },
})

const emit = defineEmits(['start', 'stop', 'edit', 'delete', 'toggleLog', 'toggleSelect'])

const groupColor = computed(() => getGroupColor(props.service.group))

const resolvedColor = computed(() => {
  if (props.status === 'failed') return 'var(--el-color-danger)'
  if (props.status === 'running') return groupColor.value
  return props.service.color || groupColor.value || '#409eff'
})

const statusTitle = computed(() => {
  const map = { running: '运行中', stopped: '已停止', failed: '启动失败' }
  return map[props.status] || props.status
})

const displayPort = computed(() => {
  if (props.status !== 'running') return null
  return props.detectedPort || props.service.port || null
})

function handleCommand(cmd) {
  if (cmd === 'edit') emit('edit', props.service)
  else if (cmd === 'delete') emit('delete', props.service.id)
}
</script>

<style scoped>
.svc-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 14px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-left: 3px solid var(--el-border-color);
  border-radius: 6px;
  transition: box-shadow .12s;
}
.svc-row:hover { box-shadow: 0 1px 4px rgba(0,0,0,.05); }
.svc-row.running { border-left-color: v-bind('groupColor') !important; }
.svc-row.failed { border-left-color: var(--el-color-danger) !important; }
.svc-row.selected { background: var(--el-color-primary-light-9); border-color: var(--el-color-primary); }

/* 多选 */
.svc-check {
  display: flex; align-items: center; cursor: pointer; flex-shrink: 0;
}

/* 左 */
.svc-left { display: flex; align-items: center; gap: 6px; min-width: 140px; flex-shrink: 0; }
.svc-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.svc-dot.running { background: var(--el-color-success); }
.svc-dot.stopped { background: var(--el-color-info); }
.svc-dot.failed { background: var(--el-color-danger); }
.svc-group-tag { font-size: 11px; padding: 0 6px; border-radius: 3px; line-height: 18px; font-weight: 500; }
.svc-name { font-weight: 600; font-size: 13px; color: var(--el-text-color-primary); }
.svc-tag { font-size: 11px; color: var(--el-text-color-secondary); background: var(--el-fill-color); padding: 0 5px; border-radius: 3px; line-height: 18px; }
.port-tag {
  color: var(--el-color-primary); background: var(--el-color-primary-light-9);
  font-weight: 600; text-decoration: none; cursor: pointer;
  font-size: 11px; padding: 0 6px; border-radius: 3px; line-height: 18px;
  transition: all .12s;
}
.port-tag:hover { background: var(--el-color-primary); color: #fff; }

/* 中 */
.svc-mid { flex: 1; min-width: 0; }
.svc-url { font-size: 12px; color: var(--el-color-primary); font-weight: 500; letter-spacing: 0.3px; }

/* 右 */
.svc-right { display: flex; align-items: center; gap: 2px; flex-shrink: 0; }
.row-btn {
  width: 28px; height: 28px; border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  border: none; cursor: pointer; background: transparent;
  color: var(--el-text-color-secondary); transition: all .12s;
}
.row-btn:hover { background: var(--el-fill-color-light); color: var(--el-text-color-primary); }
.row-btn:disabled { opacity: .35; cursor: not-allowed; }
.row-btn.start { color: var(--el-color-success); }
.row-btn.stop { color: var(--el-color-danger); }
.spinning { color: var(--el-color-primary); }
.spin { animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
