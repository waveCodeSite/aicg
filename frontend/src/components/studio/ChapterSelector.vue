<template>
  <div class="chapter-selector">
    <div class="selector-header">
      <h3>选择章节</h3>
      <el-input
        v-model="searchQuery"
        placeholder="搜索章节..."
        prefix-icon="Search"
        clearable
        size="small"
      />
    </div>

    <div class="filter-tabs">
      <span 
        v-for="status in statusOptions" 
        :key="status.value"
        class="filter-tab"
        :class="{ active: currentFilter === status.value }"
        @click="currentFilter = status.value"
      >
        {{ status.label }}
      </span>
    </div>

    <div v-loading="loading" class="chapter-list">
      <div 
        v-for="chapter in filteredChapters" 
        :key="chapter.id"
        class="chapter-item"
        :class="{ active: modelValue === chapter.id }"
        @click="$emit('update:modelValue', chapter.id); $emit('select', chapter)"
      >
        <div class="chapter-info">
          <span class="chapter-title">{{ chapter.title || '未命名章节' }}</span>
          <span class="chapter-preview">{{ getPreview(chapter.content) }}</span>
        </div>
        <div class="chapter-meta">
          <el-tag :type="getStatusType(chapter.status)" size="small">
            {{ getStatusLabel(chapter.status) }}
          </el-tag>
          <span class="chapter-date">{{ formatDate(chapter.updated_at) }}</span>
        </div>
      </div>
      
      <div v-if="filteredChapters.length === 0" class="empty-state">
        无匹配章节
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import api from '@/services/api'
import chaptersService from '@/services/chapters'

const props = defineProps({
  modelValue: String,
  projectId: String
})

const emit = defineEmits(['update:modelValue', 'select'])

const loading = ref(false)
const chapters = ref([])
const searchQuery = ref('')
const currentFilter = ref('all')

const statusOptions = [
  { label: '全部', value: 'all' },
  { label: '待准备', value: 'not_prepared' },
  { label: '准备就绪', value: 'prepared' }
]

const filteredChapters = computed(() => {
  let result = chapters.value

  if (currentFilter.value !== 'all') {
    if (currentFilter.value === 'prepared') {
        result = result.filter(c => ['materials_prepared', 'completed'].includes(c.status))
    } else {
        result = result.filter(c => !['materials_prepared', 'completed'].includes(c.status))
    }
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(c => 
      (c.title && c.title.toLowerCase().includes(query)) ||
      (c.content && c.content.toLowerCase().includes(query))
    )
  }

  return result
})

const getPreview = (content) => {
  if (!content) return ''
  return content.slice(0, 30) + (content.length > 30 ? '...' : '')
}

const getStatusType = (status) => {
  if (['materials_prepared', 'completed'].includes(status)) {
      return 'success'
  }
  return 'info'
}

const getStatusLabel = (status) => {
  if (['materials_prepared', 'completed'].includes(status)) {
      return '素材已就绪'
  }
  return '素材待准备'
}

const formatDate = (date) => {
  return dayjs(date).format('MM-DD HH:mm')
}

const fetchChapters = async () => {
  if (!props.projectId) return
  
  try {
    loading.value = true
    const response = await chaptersService.getChapters(props.projectId)
    chapters.value = response.chapters || []
  } catch (error) {
    console.error('Failed to fetch chapters:', error)
  } finally {
    loading.value = false
  }
}

watch(() => props.projectId, (newId) => {
  if (newId) {
    fetchChapters()
  }
}, { immediate: true })

onMounted(() => {
  if (props.projectId) {
    fetchChapters()
  }
})
</script>

<style scoped>
.chapter-selector {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-right: 1px solid #dcdfe6;
}

.selector-header {
  padding: 15px;
  border-bottom: 1px solid #ebeef5;
}

.selector-header h3 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #303133;
}

.filter-tabs {
  padding: 10px 15px;
  display: flex;
  gap: 15px;
  font-size: 12px;
  border-bottom: 1px solid #ebeef5;
  overflow-x: auto;
}

.filter-tab {
  cursor: pointer;
  color: #909399;
  white-space: nowrap;
}

.filter-tab.active {
  color: #409eff;
  font-weight: 500;
}

.chapter-list {
  flex: 1;
  overflow-y: auto;
}

.chapter-item {
  padding: 12px 15px;
  border-bottom: 1px solid #f2f6fc;
  cursor: pointer;
  transition: background-color 0.2s;
}

.chapter-item:hover {
  background-color: #f5f7fa;
}

.chapter-item.active {
  background-color: #ecf5ff;
  border-right: 3px solid #409eff;
}

.chapter-info {
  margin-bottom: 8px;
}

.chapter-title {
  display: block;
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.chapter-preview {
  font-size: 12px;
  color: #909399;
  display: block;
}

.chapter-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chapter-date {
  font-size: 11px;
  color: #c0c4cc;
}

.empty-state {
  padding: 30px;
  text-align: center;
  color: #909399;
  font-size: 13px;
}
</style>
