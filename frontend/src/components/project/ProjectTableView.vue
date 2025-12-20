<template>
  <div class="list-view">
    <el-table
      :data="projects"
      :row-key="(row) => row.id"
      @row-click="$emit('row-click', $event)"
      stripe
      highlight-current-row
    >
      <el-table-column prop="title" label="项目标题" min-width="200">
        <template #default="{ row }">
          <div class="project-title">
            <el-text class="title-text" truncated>{{ row.title }}</el-text>
            <el-tag
              v-if="row.type"
              :type="row.type === 'ai_movie' ? 'primary' : 'success'"
              size="small"
              effect="dark"
            >
              {{ row.type === 'ai_movie' ? '电影' : '解说' }}
            </el-tag>
            <el-tag
              v-if="row.is_public"
              type="info"
              size="small"
              effect="plain"
            >
              公开
            </el-tag>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="status" label="状态" width="120">
        <template #default="{ row }">
          <div class="status-cell">
            <el-tag
              :type="projectsStore.getStatusType(row.status)"
              size="small"
              effect="plain"
            >
              {{ projectsStore.getStatusText(row.status) }}
            </el-tag>
            <!-- 进度条 -->
            <div
              v-if="row.processing_progress > 0 && row.processing_progress < 100"
              class="progress-bar"
            >
              <div
                class="progress-fill"
                :style="{ width: row.processing_progress + '%' }"
              ></div>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="word_count" label="字数" width="100" align="right">
        <template #default="{ row }">
          <el-text>{{ projectsStore.formatNumber(row.word_count) }}</el-text>
        </template>
      </el-table-column>

      <el-table-column prop="paragraph_count" label="段落" width="100" align="right">
        <template #default="{ row }">
          <el-text>{{ projectsStore.formatNumber(row.paragraph_count) }}</el-text>
        </template>
      </el-table-column>

      <el-table-column prop="sentence_count" label="句子" width="100" align="right">
        <template #default="{ row }">
          <el-text>{{ projectsStore.formatNumber(row.sentence_count) }}</el-text>
        </template>
      </el-table-column>

      <el-table-column prop="chapter_count" label="章节" width="100" align="right">
        <template #default="{ row }">
          <el-text>{{ projectsStore.formatNumber(row.chapter_count) }}</el-text>
        </template>
      </el-table-column>

      <el-table-column prop="file_size" label="文件大小" width="120" align="right">
        <template #default="{ row }">
          <el-text>{{ projectsStore.formatFileSize(row.file_size) }}</el-text>
        </template>
      </el-table-column>

      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          <el-text>{{ projectsStore.formatDateTime(row.created_at) }}</el-text>
        </template>
      </el-table-column>

      <el-table-column prop="updated_at" label="更新时间" width="160">
        <template #default="{ row }">
          <el-text>{{ projectsStore.formatDateTime(row.updated_at) }}</el-text>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <div class="action-buttons">
            <el-button
              type="primary"
              size="small"
              :icon="View"
              link
              @click.stop="$emit('view-project', row)"
            >
              查看
            </el-button>
            <el-button
              v-if="row.status === 'failed'"
              size="small"
              :icon="RefreshRight"
              link
              @click.stop="$emit('retry-project', row)"
            >
              重试
            </el-button>
            <el-button
              v-if="projectsStore.isEditable(row)"
              type="default"
              size="small"
              :icon="Edit"
              link
              @click.stop="$emit('edit-project', row)"
            >
              编辑
            </el-button>
            <el-button
              v-if="projectsStore.isArchivable(row)"
              type="info"
              size="small"
              link
              @click.stop="$emit('archive-project', row)"
            >
              归档
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { View, Edit, RefreshRight } from '@element-plus/icons-vue'
import { useProjectsStore } from '@/stores/projects'

const props = defineProps({
  projects: {
    type: Array,
    default: () => [],
  }
})

const emit = defineEmits([
  'view-project',
  'retry-project',
  'edit-project',
  'archive-project',
  'row-click'
])

const projectsStore = useProjectsStore()
</script>

<style scoped>
.list-view {
  background: var(--bg-primary);
  border-radius: var(--radius-xl);
  border: 1px solid var(--border-primary);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
  padding: var(--space-lg);
}

:deep(.el-table) {
  --el-table-border-color: var(--border-primary);
  --el-table-header-bg-color: var(--bg-secondary);
  --el-table-row-hover-bg-color: rgba(32, 33, 36, 0.03);
  --el-table-text-color: var(--text-primary);
  --el-table-header-text-color: var(--text-primary);
  font-size: var(--text-sm);
}

:deep(.el-table th) {
  font-weight: 600;
  font-size: var(--text-sm);
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-primary) 100%);
  border-bottom: 2px solid var(--border-primary);
  padding: var(--space-md) var(--space-sm);
  color: var(--text-primary);
}

:deep(.el-table td) {
  border-bottom: 1px solid var(--border-primary);
  padding: var(--space-lg) var(--space-sm);
  vertical-align: middle;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: rgba(32, 33, 36, 0.02);
}

:deep(.el-table__body tr:hover > td) {
  background: rgba(32, 33, 36, 0.03) !important;
}

:deep(.el-table__row) {
  transition: all var(--transition-fast);
}

:deep(.el-table__row:hover) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.project-title {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.title-text {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  color: var(--text-primary);
}

.status-cell {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  align-items: flex-start;
}

.progress-bar {
  width: 100%;
  height: 4px;
  background-color: var(--bg-secondary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-color), var(--primary-hover));
  transition: width 0.3s ease;
  border-radius: var(--radius-full);
}

.action-buttons {
  display: flex;
  gap: var(--space-xs);
  align-items: center;
  justify-content: flex-end;
}

.action-buttons :deep(.el-button--link) {
  padding: var(--space-xs) var(--space-sm);
  margin: 0;
  min-height: auto;
  border: none;
  font-weight: 500;
  transition: all var(--transition-fast);
}

.action-buttons :deep(.el-button--link:hover) {
  transform: translateY(-1px);
  background: rgba(32, 33, 36, 0.05);
  border-radius: var(--radius-md);
}

.action-buttons :deep(.el-button--danger.is-link:hover) {
  background: rgba(245, 108, 108, 0.05);
  color: var(--danger-color);
}

/* 标签样式优化 */
:deep(.el-tag) {
  border-radius: var(--radius-full);
  font-weight: 600;
  font-size: var(--text-xs);
  padding: var(--space-xs) var(--space-sm);
  border: 1px solid var(--border-primary);
}

:deep(.el-tag--info) {
  background: rgba(32, 33, 36, 0.05);
  color: var(--text-secondary);
  border-color: var(--border-primary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .list-view {
    padding: var(--space-md);
  }

  :deep(.el-table) {
    font-size: var(--text-sm);
  }

  :deep(.el-table th),
  :deep(.el-table td) {
    padding: var(--space-sm);
  }
}

@media (max-width: 480px) {
  :deep(.el-table) {
    font-size: var(--text-xs);
  }

  :deep(.el-table th),
  :deep(.el-table td) {
    padding: var(--space-xs);
  }

  .project-title {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-xs);
  }

  .action-buttons {
    flex-direction: column;
    gap: var(--space-xs);
    align-items: flex-end;
  }

  .action-buttons :deep(.el-button--link) {
    padding: var(--space-xs) var(--space-xs);
    font-size: var(--text-xs);
    min-width: auto;
  }

  .list-view {
    padding: var(--space-sm);
  }
}
</style>
