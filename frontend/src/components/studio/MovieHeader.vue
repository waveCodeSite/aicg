<template>
  <div class="studio-header">
    <div class="header-left">
      <el-button @click="$emit('back')" icon="ArrowLeft">返回项目</el-button>
      <div class="header-info">
        <span class="chapter-title">{{ chapter?.title || '未选择章节' }}</span>
        <el-tag v-if="chapter" :type="getChapterStatusType(chapter.status)" size="small" class="status-badge">
          {{ getChapterStatusLabel(chapter.status) }}
        </el-tag>
      </div>
    </div>
    <div class="header-right">
      <el-space>
        <!-- 状态检测与流转 -->
        <div class="completion-status" v-if="completionStatus">
          <el-progress 
            type="circle" 
            :percentage="completionStatus.completion_rate" 
            :width="40" 
            :stroke-width="4"
            :status="completionStatus.is_complete ? 'success' : ''"
          >
            <template #default="{ percentage }">
              <span class="progress-text">{{ percentage }}%</span>
            </template>
          </el-progress>
        </div>

        <!-- 批量操作进度 -->
        <div v-if="isPolling" class="batch-progress-container">
           <div class="progress-row">
             <el-progress 
               :percentage="taskProgressPercentage" 
               :indeterminate="!taskStatistics && !taskResult?.percent"
               :status="taskStatus === 'SUCCESS' ? 'success' : ''"
               style="width: 120px"
               :stroke-width="18"
               :text-inside="true"
             />
             <el-button 
               link 
               type="danger" 
               size="small" 
               class="cancel-btn" 
               @click="$emit('terminate')"
               icon="Close"
               title="终止任务"
             />
           </div>
           <span class="progress-label">
             {{ progressTitle }}
             <template v-if="taskStatistics">
               ({{ taskStatistics.success + taskStatistics.failed }}/{{ taskStatistics.total }})
             </template>
             <template v-else-if="taskResult?.message">
               : {{ taskResult.message }}
             </template>
           </span>
        </div>

        <el-button 
          type="primary" 
          plain 
          icon="Refresh" 
          @click="$emit('check-completion')" 
          :loading="checkingCompletion"
          v-if="script"
          size="small"
        >
          检测进度
        </el-button>

        <el-button 
          type="success" 
          icon="Check" 
          @click="$emit('prepare-materials')" 
          :disabled="!canPrepareMaterials"
          v-if="script"
          size="small"
        >
          准备素材
        </el-button>

        <el-divider direction="vertical" />

        <el-select 
          :model-value="genConfig.api_key_id" 
          @update:model-value="(val) => $emit('update-api-key', val)"
          placeholder="选择 Key" 
          style="width: 150px" 
          size="small"
        >
          <el-option v-for="k in apiKeys" :key="k.id" :label="k.name" :value="k.id" />
        </el-select>
        
        <el-button @click="$emit('toggle-cast')" :type="showCastManager ? 'primary' : 'default'" size="small" plain>
          {{ showCastManager ? '剧组' : '显示剧组' }}
        </el-button>
        <el-button type="success" icon="Picture" @click="$emit('generate-keyframes')" :disabled="!script" :loading="loadingKeyframes" size="small">批量绘图</el-button>
        <el-button type="warning" icon="VideoPlay" @click="$emit('produce-batch')" :disabled="!script || !allCharactersReady" :loading="batchProducing" size="small">批量视频</el-button>
        <el-button type="danger" icon="Film" @click="$emit('generate-video')" :disabled="!completionStatus?.is_complete" size="small">生成视频</el-button>
        <el-button type="primary" @click="$emit('generate-script')" :loading="loadingScript" size="small">
          {{ script ? '重制剧本' : '生成 AI 剧本' }}
        </el-button>
      </el-space>
    </div>
  </div>
</template>

<script setup>
import { ArrowLeft, Refresh, Check, Picture, VideoPlay, Film } from '@element-plus/icons-vue'

const props = defineProps({
  chapter: Object,
  script: Object,
  completionStatus: Object,
  checkingCompletion: Boolean,
  canPrepareMaterials: Boolean,
  genConfig: Object,
  apiKeys: Array,
  showCastManager: Boolean,
  loadingKeyframes: Boolean,
  batchProducing: Boolean,
  allCharactersReady: Boolean,
  isPolling: Boolean,
  taskStatus: String,
  taskStatistics: Object,
  taskResult: Object
})

const emit = defineEmits([
  'back', 'check-completion', 'prepare-materials', 'update-api-key',
  'toggle-cast', 'generate-keyframes', 'produce-batch', 'generate-script',
  'terminate', 'generate-video'
])

import { computed } from 'vue'
import { Close } from '@element-plus/icons-vue'

const taskProgressPercentage = computed(() => {
  if (props.taskStatistics) {
    return Math.round((props.taskStatistics.success + props.taskStatistics.failed) / props.taskStatistics.total * 100)
  }
  if (props.taskResult?.percent) {
    return Math.round(props.taskResult.percent * 100)
  }
  return 100 
})

const progressTitle = computed(() => {
  if (props.loadingScript) return '剧本生成'
  if (props.loadingKeyframes) return '批量绘图'
  if (props.batchProducing) return '视频制作'
  return '任务执行'
})

const getChapterStatusType = (status) => {
  switch (status) {
    case 'completed': return 'success'
    case 'materials_prepared': return 'warning'
    case 'script_generated': return 'primary'
    default: return 'info'
  }
}

const getChapterStatusLabel = (status) => {
  const map = {
    draft: '草稿',
    script_generated: '已生成剧本',
    materials_prepared: '素材准备完成',
    completed: '制作完成'
  }
  return map[status] || status
}
</script>

<style scoped>
.studio-header {
  background: #fff;
  padding: 12px 20px;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chapter-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.completion-status {
  display: flex;
  align-items: center;
}

.progress-text {
  font-size: 10px;
  font-weight: bold;
}

.batch-progress-container {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  min-width: 150px;
}

.progress-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.cancel-btn {
  padding: 0;
  height: auto;
}

.progress-label {
  font-size: 10px;
  color: #909399;
  white-space: nowrap;
}
</style>
