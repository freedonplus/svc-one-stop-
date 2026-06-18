<template>
  <el-dialog
    :model-value="visible"
    title="设置"
    width="480px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-tabs v-model="activeTab" class="settings-tabs">
      <!-- ═══ Theme ═══ -->
      <el-tab-pane label="主题" name="theme">
        <el-form label-width="0">
          <el-radio-group v-model="local.theme" class="theme-options">
            <el-radio v-for="t in themes" :key="t.key" :value="t.key" class="theme-option">
              <el-icon :size="18" style="margin-right:4px;vertical-align:middle"><component :is="t.icon" /></el-icon>
              {{ t.label }}
            </el-radio>
          </el-radio-group>
        </el-form>
      </el-tab-pane>

      <!-- ═══ Font ═══ -->
      <el-tab-pane label="字体" name="font">
        <el-form label-width="70px" label-position="left">
          <el-form-item label="字号">
            <el-radio-group v-model="local.fontSize">
              <el-radio-button v-for="s in fontSizes" :key="s.key" :value="s.key">
                {{ s.label }}
              </el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="字体">
            <el-select v-model="local.fontFamily" style="width:100%">
              <el-option v-for="f in fontFamilies" :key="f.key" :label="f.label" :value="f.key" />
            </el-select>
          </el-form-item>
        </el-form>

        <!-- Preview -->
        <div class="font-preview" :style="previewStyle">
          <p class="preview-title">预览</p>
          <p>OneStopService 本地服务一条龙管理</p>
          <p style="opacity:0.65">ABCDEFGHIJKLMNOPQRSTUVWXYZ</p>
          <p style="opacity:0.65">abcdefghijklmnopqrstuvwxyz 0123456789</p>
        </div>
      </el-tab-pane>

      <!-- ═══ Data ═══ -->
      <el-tab-pane label="数据" name="data">
        <div class="data-actions">
          <el-button type="primary" @click="exportServices" class="data-btn" :loading="exporting">
            <el-icon v-if="!exporting" style="margin-right:4px"><Download /></el-icon>
            {{ exporting ? '正在导出...' : '导出服务配置' }}
          </el-button>
          <el-button @click="triggerImport" class="data-btn">
            <el-icon style="margin-right:4px"><Upload /></el-icon>
            导入服务配置
          </el-button>
          <input ref="fileInput" type="file" accept=".json" hidden @change="onFileChange" />
        </div>
        <p class="data-hint">导出所有服务定义（名称/命令/分组等），便于备份和迁移。</p>
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="confirm">应用</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { THEMES, FONT_SIZES, FONT_FAMILIES } from '../constants.js'
import * as api from '../api/index.js'

const props = defineProps({
  visible: Boolean,
  settings: { type: Object, required: true },
})
const emit = defineEmits(['update:visible', 'update:settings', 'services-imported'])

const themes = THEMES
const fontSizes = FONT_SIZES
const fontFamilies = FONT_FAMILIES

const activeTab = ref('theme')
const fileInput = ref(null)
const exporting = ref(false)

// Local copy for editing
const local = reactive({
  theme: props.settings.theme,
  fontSize: props.settings.fontSize,
  fontFamily: props.settings.fontFamily,
})

// Sync from props when dialog opens
watch(() => props.visible, (v) => {
  if (v) {
    local.theme = props.settings.theme
    local.fontSize = props.settings.fontSize
    local.fontFamily = props.settings.fontFamily
  }
})

// Preview style
const previewStyle = computed(() => {
  const f = fontFamilies.find(x => x.key === local.fontFamily)
  return {
    fontFamily: f?.value || 'inherit',
    fontSize: fontSizes.find(x => x.key === local.fontSize)?.value || '14px',
  }
})

function confirm() {
  emit('update:settings', { ...local })
  emit('update:visible', false)
}

async function exportServices() {
  exporting.value = true
  try {
    const res = await api.fetchServices()
    const services = res.services || []
    const name = `services-backup-${Date.now()}.json`
    const jsonStr = JSON.stringify(services, null, 2)

    // 方案 1: showSaveFilePicker (WebView2 / Chrome)
    try {
      const handle = await window.showSaveFilePicker({
        suggestedName: name,
        types: [{ description: 'JSON', accept: { 'application/json': ['.json'] } }],
      })
      const blob = new Blob([jsonStr], { type: 'application/json' })
      const writable = await handle.createWritable()
      await writable.write(blob)
      await writable.close()
      ElMessage.success(`已导出 ${services.length} 个服务`)
      exporting.value = false
      return
    } catch {
      // 用户取消或 API 不可用 → 方案 2
    }

    // 方案 2: data URL + anchor download
    const dataUrl = 'data:application/json;charset=utf-8,' + encodeURIComponent(jsonStr)
    const a = document.createElement('a')
    a.href = dataUrl
    a.download = name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    ElMessage.success(`已导出 ${services.length} 个服务`)
  } catch (e) {
    ElMessage.error('导出失败: ' + e.message)
  } finally {
    exporting.value = false
  }
}

function triggerImport() {
  fileInput.value?.click()
}

async function onFileChange(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async (ev) => {
    try {
      const services = JSON.parse(ev.target.result)
      if (!Array.isArray(services) || !services.length) {
        ElMessage.warning('文件中没有有效的服务配置')
        return
      }
      let added = 0, skipped = 0
      for (const svc of services) {
        try {
          await api.addService(svc)
          added++
        } catch {
          skipped++ // 已存在的服务跳过
        }
      }
      ElMessage.success(`导入完成：新增 ${added} 个${skipped ? `，跳过 ${skipped} 个（已存在）` : ''}`)
      // 通知父组件刷新
      emit('services-imported')
    } catch {
      ElMessage.error('文件格式无效，请选择正确的 JSON 文件')
    }
  }
  reader.readAsText(file)
  e.target.value = ''
}
</script>

<style scoped>
.settings-tabs { min-height: 260px; }

/* ─── Theme ─── */
.theme-options {
  display: flex;
  flex-direction: row;
  gap: 10px;
  width: 100%;
}
.theme-option {
  margin-right: 0 !important;
  padding: 10px 14px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s, background 0.2s;
}
.theme-option:hover {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}
.theme-option:has(.el-radio__input.is-checked) {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

/* ─── Font ─── */
.font-preview {
  margin-top: 16px;
  padding: 14px;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  background: var(--el-fill-color-lighter);
  line-height: 1.7;
  color: var(--el-text-color-primary);
}
.preview-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* ─── Data ─── */
.data-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.data-btn { width: 100%; justify-content: center; }
.data-hint {
  margin-top: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  text-align: center;
}
</style>
