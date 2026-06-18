export const GROUPS = [
  { label: '全部', value: '' },
  { label: '数据库', value: '数据库' },
  { label: '中间件', value: '中间件' },
  { label: '微服务', value: '微服务' },
  { label: '前端', value: '前端' },
  { label: '后端', value: '后端' },
  { label: '工具', value: '工具' },
]

export const GROUP_COLORS = {
  '数据库': '#409eff',
  '中间件': '#67c23a',
  '微服务': '#e6a23c',
  '前端': '#f56c6c',
  '后端': '#909399',
  '工具': '#b37feb',
}

export function getGroupColor(group) {
  return GROUP_COLORS[group] || '#409eff'
}

// ─── Theme ───
export const THEMES = [
  { key: 'light',  label: '白天',   icon: 'Sunny' },
  { key: 'dark',   label: '黑夜',   icon: 'Moon' },
  { key: 'system', label: '跟随系统', icon: 'Monitor' },
]

// ─── Font Size ───
export const FONT_SIZES = [
  { key: 'small',  label: '小', value: '13px' },
  { key: 'medium', label: '中', value: '14px' },
  { key: 'large',  label: '大', value: '15px' },
]

// ─── Font Family ───
export const FONT_FAMILIES = [
  { key: 'system', label: '系统默认',  value: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif' },
  { key: 'yahei',  label: '微软雅黑',  value: '"Microsoft YaHei", "微软雅黑", sans-serif' },
  { key: 'songti', label: '宋体',      value: '"SimSun", "宋体", serif' },
]
