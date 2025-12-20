<template>
  <div class="project-card" @click="$emit('view', project)">
    <!-- 卡片头部 -->
    <div class="card-header">
      <div class="file-icon">
        <el-icon :size="24" :color="getFileTypeColor(project.file_type)">
          <component :is="getFileTypeIcon(project.file_type)" />
        </el-icon>
      </div>
      <div class="card-title">{{ project.title }}</div>
      <div v-if="project.type" class="type-tag">
        <el-tag
          :type="project.type === 'ai_movie' ? 'primary' : 'success'"
          size="small"
          effect="dark"
          class="type-badge"
        >
          {{ project.type === 'ai_movie' ? '电影' : '解说' }}
        </el-tag>
      </div>
    </div>

    <!-- 卡片内容 -->
    <div class="card-content">
      <!-- 文件信息 -->
      <div class="file-info">
        <div class="info-item">
          <el-text size="small" type="info">
            {{ project.file_type?.toUpperCase() || '-' }}
          </el-text>
          <el-text size="small" type="info">
            {{ projectsStore.formatFileSize(project.file_size) }}
          </el-text>
        </div>
      </div>

      <!-- 统计信息 -->
      <div class="stats-info">
        <div class="stat-item">
          <el-text size="small">{{ projectsStore.formatNumber(project.word_count) }}</el-text>
          <el-text size="small" type="info">字数</el-text>
        </div>
        <div class="stat-item">
          <el-text size="small">{{ projectsStore.formatNumber(project.paragraph_count) }}</el-text>
          <el-text size="small" type="info">段落</el-text>
        </div>
        <div class="stat-item">
          <el-text size="small">{{ projectsStore.formatNumber(project.chapter_count) }}</el-text>
          <el-text size="small" type="info">章节</el-text>
        </div>
      </div>

      <!-- 状态标签 -->
      <div class="status-section">
        <el-tag
          :type="projectsStore.getStatusType(project.status)"
          size="small"
          effect="plain"
        >
          {{ projectsStore.getStatusText(project.status) }}
        </el-tag>
        <el-text size="small" type="info">
          {{ projectsStore.formatDateTime(project.updated_at) }}
        </el-text>
      </div>

      <!-- 处理进度条 -->
      <div v-if="project.status === 'parsing' || project.status === 'generating'" class="progress-section">
        <el-progress
          :percentage="project.processing_progress || 0"
          :show-text="false"
          :stroke-width="3"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import {
  Document,
  VideoPlay,
  Microphone,
  Picture
} from '@element-plus/icons-vue'

import { useProjectsStore } from '@/stores/projects'

// Props定义
const props = defineProps({
  project: {
    type: Object,
    required: true
  }
})

// Store实例
const projectsStore = useProjectsStore()

// Emits定义
const emit = defineEmits([
  'view'
])

// 计算属性
const getFileTypeIcon = (fileType) => {
  const iconMap = {
    'txt': Document,
    'md': Document,
    'docx': Document,
    'epub': Document,
    'video': VideoPlay,
    'audio': Microphone,
    'image': Picture
  }
  return iconMap[fileType] || Document
}

const getFileTypeColor = (fileType) => {
  const colorMap = {
    'txt': '#606266',
    'md': '#409EFF',
    'docx': '#67C23A',
    'epub': '#E6A23C',
    'video': '#F56C6C',
    'audio': '#909399',
    'image': '#909399'
  }
  return colorMap[fileType] || '#606266'
}

// 使用store中的工具方法，避免重复代码
</script>

<style scoped>
.project-card {
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-primary);
  transition: all var(--transition-fast);
  cursor: pointer;
  overflow: hidden;
  height: 200px;
  display: flex;
  flex-direction: column;
}

.project-card:hover {
  border-color: var(--primary-color);
  box-shadow: var(--shadow-md);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-md);
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-primary);
}

.file-icon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(99, 102, 241, 0.1);
  flex-shrink: 0;
}

.card-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.type-tag {
  display: flex;
  align-items: center;
  margin-left: auto;
}

.type-badge {
  font-size: 10px;
  height: 20px;
  padding: 0 6px;
  border-radius: 4px;
}

.card-content {
  flex: 1;
  padding: var(--space-sm) var(--space-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.file-info {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.info-item {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.info-item .el-text {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.stats-info {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-sm);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}

.stat-item .el-text:first-child {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1;
}

.stat-item .el-text:last-child {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.status-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
  padding-top: var(--space-sm);
  border-top: 1px solid var(--border-primary);
}

.progress-section {
  margin-top: var(--space-xs);
}

.progress-section .el-progress {
  --el-progress-bg-color: var(--bg-secondary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .project-card {
    height: 180px;
  }

  .card-header {
    padding: var(--space-sm);
  }

  .card-content {
    padding: var(--space-xs) var(--space-sm);
  }

  .card-title {
    font-size: var(--text-sm);
  }

  .stats-info {
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-xs);
  }
}
</style>