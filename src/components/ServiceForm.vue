<template>
  <el-dialog
    :model-value="visible"
    :title="isEdit ? '编辑服务' : '新增服务'"
    width="600px"
    :close-on-click-modal="false"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="85px"
      label-position="left"
      size="default"
    >
      <!-- ═══ 基本信息 ═══ -->
      <el-form-item label="服务名称" prop="name">
        <el-input v-model="form.name" placeholder="例: MySQL" @input="autoGenerateId" />
      </el-form-item>

      <el-form-item v-if="isEdit" label="标识">
        <el-input v-model="form.id" disabled />
      </el-form-item>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="分组">
            <el-select
              v-model="form.group"
              placeholder="选择分组"
              clearable
              allow-create
              filterable
              style="width: 100%"
              @change="onGroupChange"
            >
              <el-option
                v-for="g in groupOptions"
                :key="g.value"
                :label="g.label"
                :value="g.value"
              >
                <span class="group-dot" :style="{ background: g.color }"></span>
                {{ g.label }}
              </el-option>
            </el-select>
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="版本">
            <el-input v-model="form.version" placeholder="例: 8.0" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="访问地址">
        <el-input v-model="form.url" placeholder="例: http://localhost:8848/nacos  留空则自动使用端口" />
      </el-form-item>

      <el-form-item label="启动命令" prop="command">
        <el-input
          v-model="form.command"
          type="textarea"
          :rows="2"
          placeholder="例: D:\tool\mysql\bin\mysqld --defaults-file=D:\tool\mysql\my.ini"
        />
      </el-form-item>

      <!-- ═══ 高级选项 ═══ -->
      <el-divider content-position="left">
        <el-tag size="small" type="info" effect="plain">高级选项</el-tag>
      </el-divider>

      <el-row :gutter="12">
        <el-col :span="12">
          <el-form-item label="端口号">
            <el-input
              v-model="form.port"
              placeholder="例: 15672  留空自动"
            />
          </el-form-item>
        </el-col>
        <el-col :span="12">
          <el-form-item label="日志文件">
            <el-input v-model="form.log_file" placeholder="例: D:/tool/redis/redis.log" />
          </el-form-item>
        </el-col>
      </el-row>

      <el-form-item label="工作目录">
        <el-input v-model="form.cwd" placeholder="例: D:/tool/RabbitMQ  留空使用默认" />
      </el-form-item>

      <el-form-item label="环境变量">
        <div class="env-editor">
          <div
            v-for="(item, idx) in form.envList"
            :key="idx"
            class="env-row"
          >
            <el-input
              v-model="item.key"
              placeholder="变量名"
              class="env-key"
              size="small"
              @input="onEnvChange"
            />
            <span class="env-eq">=</span>
            <el-input
              v-model="item.value"
              placeholder="变量值"
              class="env-val"
              size="small"
              @input="onEnvChange"
            />
            <el-button
              type="danger"
              :icon="Delete"
              size="small"
              circle
              @click="removeEnv(idx)"
            />
          </div>
          <el-button
            type="primary"
            size="small"
            @click="addEnv"
          >
            + 添加环境变量
          </el-button>
          <div v-if="form.envList.length === 0" class="env-empty">
            暂无环境变量
          </div>
        </div>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="submit">
        {{ isEdit ? '保存' : '添加' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import { Delete } from '@element-plus/icons-vue'
import { GROUPS, getGroupColor } from '../constants.js'

const props = defineProps({
  visible: Boolean,
  service: { type: Object, default: null },
})

const emit = defineEmits(['update:visible', 'confirm'])

const formRef = ref(null)
const submitting = ref(false)

const isEdit = computed(() => !!props.service)

const form = ref(createEmptyForm())

const groupOptions = GROUPS.filter(g => g.value)

function createEmptyForm() {
  return {
    id: '', name: '', group: '', version: '',
    command: '', url: '', color: '',
    port: null, cwd: '', log_file: '',
    envList: [],
  }
}

/** env 对象 → 键值对数组 */
function envToList(env) {
  if (!env || typeof env !== 'object') return []
  return Object.entries(env).map(([key, value]) => ({ key, value: String(value) }))
}

/** 键值对数组 → env 对象 */
function listToEnv(list) {
  const pairs = list.filter(item => item.key.trim())
  if (pairs.length === 0) return null
  const obj = {}
  for (const item of pairs) {
    obj[item.key.trim()] = item.value
  }
  return obj
}

const rules = {
  name: [{ required: true, message: '请输入服务名称', trigger: 'blur' }],
  command: [{ required: true, message: '请输入启动命令', trigger: 'blur' }],
}

watch(() => props.visible, (v) => {
  if (v && props.service) {
    const svc = props.service
    form.value = {
      id: svc.id || '',
      name: svc.name || '',
      group: svc.group || '',
      version: svc.version || '',
      command: svc.command || '',
      url: svc.url || '',
      color: svc.color || getGroupColor(svc.group),
      port: svc.port ?? null,
      cwd: svc.cwd || '',
      log_file: svc.log_file || '',
      envList: envToList(svc.env),
    }
  } else if (v) {
    form.value = createEmptyForm()
  }
})

function onGroupChange(val) {
  if (val && !form.value.color) {
    form.value.color = getGroupColor(val)
  }
}

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^\w一-鿿]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .replace(/--+/g, '-')
    || 'service'
}

function autoGenerateId(val) {
  if (!isEdit.value && val) {
    form.value.id = slugify(val)
  }
}

// ─── 环境变量编辑器 ───

function addEnv() {
  form.value.envList.push({ key: '', value: '' })
}

function removeEnv(idx) {
  form.value.envList.splice(idx, 1)
}

function onEnvChange() {
  // no-op: 只是触发响应式更新
}


async function submit() {
  if (!formRef.value) return

  if (!form.value.id && form.value.name) {
    form.value.id = slugify(form.value.name) + '-' + Date.now().toString(36)
  }

  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true

  emit('confirm', {
    id: form.value.id,
    name: form.value.name,
    group: form.value.group || null,
    version: form.value.version || null,
    command: form.value.command,
    url: form.value.url || null,
    color: form.value.color || getGroupColor(form.value.group),
    port: form.value.port ? Number(form.value.port) : null,
    cwd: form.value.cwd || null,
    env: listToEnv(form.value.envList),
    log_file: form.value.log_file || null,
  }, isEdit.value)

  submitting.value = false
}
</script>

<style scoped>
.group-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}

/* ─── 环境变量编辑器 ─── */
.env-editor {
  width: 100%;
}

.env-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.env-key {
  flex: 2;
}

.env-eq {
  flex-shrink: 0;
  color: #909399;
  font-weight: bold;
}

.env-val {
  flex: 3;
}

.env-empty {
  color: #909399;
  font-size: 12px;
  margin-bottom: 6px;
}
</style>
