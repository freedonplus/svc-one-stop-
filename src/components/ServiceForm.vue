<template>
  <el-dialog
    :model-value="visible"
    :title="isEdit ? '编辑服务' : '新增服务'"
    width="540px"
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
          placeholder="例: mysqld --console"
        />
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
  }
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
</style>
