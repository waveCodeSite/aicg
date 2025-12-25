<template>
  <div class="video-tasks-page">
    <div class="page-header">
      <div class="header-left">
        <h2>视频生成任务</h2>
        <p class="subtitle">管理您的视频生成任务，查看进度和下载结果</p>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="showCreateDialog = true">
          <el-icon><Plus /></el-icon>
          新建任务
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards">
      <el-card shadow="hover" class="stat-card">
        <div class="stat-content">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">总任务数</div>
        </div>
        <el-icon class="stat-icon"><VideoCamera /></el-icon>
      </el-card>
      <el-card shadow="hover" class="stat-card success">
        <div class="stat-content">
          <div class="stat-value">{{ stats.completed }}</div>
          <div class="stat-label">已完成</div>
        </div>
        <el-icon class="stat-icon"><CircleCheck /></el-icon>
      </el-card>
      <el-card shadow="hover" class="stat-card warning">
        <div class="stat-content">
          <div class="stat-value">{{ stats.processing }}</div>
          <div class="stat-label">处理中</div>
        </div>
        <el-icon class="stat-icon"><Loading /></el-icon>
      </el-card>
      <el-card shadow="hover" class="stat-card danger">
        <div class="stat-content">
          <div class="stat-value">{{ stats.failed }}</div>
          <div class="stat-label">失败</div>
        </div>
        <el-icon class="stat-icon"><CircleClose /></el-icon>
      </el-card>
    </div>

    <!-- 过滤器 -->
    <div class="filter-bar">
      <el-radio-group v-model="filterStatus" @change="handleFilterChange">
        <el-radio-button label="">全部</el-radio-button>
        <el-radio-button label="pending">等待中</el-radio-button>
        <el-radio-button label="processing">处理中</el-radio-button>
        <el-radio-button label="completed">已完成</el-radio-button>
        <el-radio-button label="failed">失败</el-radio-button>
      </el-radio-group>
      
      <div class="filter-right">
        <el-button @click="refreshList" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 任务列表 -->
    <el-card class="tasks-list-card" v-loading="loading">
      <el-table :data="tasks" style="width: 100%">
        <el-table-column prop="chapter_title" label="章节" min-width="200">
          <template #default="{ row }">
            <div class="chapter-info">
              <span class="chapter-title">{{ row.chapter_title || '未知章节' }}</span>
              <span class="project-title">{{ row.project_title || '未知项目' }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="进度" width="200">
          <template #default="{ row }">
            <div class="progress-cell">
              <el-progress 
                :percentage="row.progress" 
                :status="row.status === 'failed' ? 'exception' : (row.status === 'completed' ? 'success' : '')"
              />
              <span class="progress-text" v-if="row.status !== 'completed' && row.status !== 'failed'">
                {{ getProgressText(row) }}
              </span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-button 
                size="small" 
                @click="viewDetail(row)"
              >
                详情
              </el-button>
              <el-button 
                v-if="row.status === 'completed' && row.video_url"
                size="small" 
                type="success" 
                @click="previewVideo(row)"
              >
                预览
              </el-button>
              <el-button 
                v-if="row.status === 'completed' && row.video_url"
                size="small" 
                type="primary" 
                @click="downloadVideo(row)"
              >
                下载
              </el-button>
              <el-button 
                v-if="row.status === 'failed'"
                size="small" 
                type="warning" 
                @click="handleRetry(row)"
              >
                重试
              </el-button>
              <el-button 
                size="small" 
                type="danger" 
                @click="handleDelete(row)"
                :disabled="isProcessing(row.status)"
              >
                删除
              </el-button>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <!-- 对话框组件 -->
    <CreateVideoTaskDialog 
      v-model="showCreateDialog"
      @success="handleCreateSuccess"
    />
    
    <VideoTaskDetailDialog
      v-model="showDetailDialog"
      :task-id="selectedTaskId"
    />
    
    <VideoPreviewDialog
      v-model="showPreviewDialog"
      :video-url="previewUrl"
      :title="previewTitle"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { 
  Plus, 
  Refresh, 
  VideoCamera, 
  CircleCheck, 
  CircleClose, 
  Loading 
} from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useVideoTasks } from '@/composables/useVideoTasks'
import { formatDate } from '@/utils/dateUtils'
import CreateVideoTaskDialog from '@/components/video/CreateVideoTaskDialog.vue'
import VideoTaskDetailDialog from '@/components/video/VideoTaskDetailDialog.vue'
import VideoPreviewDialog from '@/components/video/VideoPreviewDialog.vue'

const route = useRoute()

const { 
  tasks, 
  total, 
  loading, 
  stats, 
  fetchTasks, 
  fetchStats, 
  deleteTask, 
  retryTask,
  startPolling,
  stopPolling
} = useVideoTasks()

// 状态
const currentPage = ref(1)
const pageSize = ref(20)
const filterStatus = ref('')
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const showPreviewDialog = ref(false)
const selectedTaskId = ref('')
const previewUrl = ref('')
const previewTitle = ref('')

// 生命周期
onMounted(() => {
  refreshList()
  startPolling(3000, getQueryParams())
})

onUnmounted(() => {
  stopPolling()
})

// 方法
const getQueryParams = () => {
  const params = {
    page: currentPage.value,
    size: pageSize.value
  }
  
  if (filterStatus.value) {
    // 处理前端过滤器到后端状态的映射
    if (filterStatus.value === 'processing') {
      // 后端API可能不支持直接传'processing'来匹配多个状态，这里可能需要特殊处理
      // 或者后端API已经支持了
    } else {
      params.status = filterStatus.value
    }
  }
  
  return params
}

const refreshList = async () => {
  await Promise.all([
    fetchTasks(getQueryParams()),
    fetchStats()
  ])
}

const handleFilterChange = () => {
  currentPage.value = 1
  refreshList()
}

const handleSizeChange = (val) => {
  pageSize.value = val
  refreshList()
}

const handleCurrentChange = (val) => {
  currentPage.value = val
  refreshList()
}

const handleCreateSuccess = () => {
  refreshList()
}

const viewDetail = (row) => {
  selectedTaskId.value = row.id
  showDetailDialog.value = true
}

const previewVideo = (row) => {
  if (row.video_url) {
    previewUrl.value = row.video_url
    previewTitle.value = row.chapter_title || '视频预览'
    showPreviewDialog.value = true
  } else {
    ElMessage.warning('视频地址不可用')
  }
}

const handleRetry = async (row) => {
  try {
    await ElMessageBox.confirm('确定要重试这个失败的任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await retryTask(row.id)
    refreshList()
  } catch (e) {
    // 取消或失败
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除这个任务吗？此操作不可恢复。', '警告', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteTask(row.id)
    refreshList()
  } catch (e) {
    // 取消或失败
  }
}

// 辅助函数
const getStatusType = (status) => {
  const map = {
    pending: 'info',
    validating: 'primary',
    downloading_materials: 'primary',
    generating_subtitles: 'primary',
    synthesizing_videos: 'warning',
    concatenating: 'warning',
    uploading: 'primary',
    completed: 'success',
    failed: 'danger'
  }
  return map[status] || 'info'
}

const getStatusText = (status) => {
  const map = {
    pending: '等待中',
    validating: '验证素材',
    downloading_materials: '下载素材',
    generating_subtitles: '生成字幕',
    synthesizing_videos: '合成视频',
    concatenating: '拼接视频',
    uploading: '上传结果',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

const getProgressText = (row) => {
  if (row.current_sentence_index !== null && row.total_sentences) {
    return `正在处理第 ${row.current_sentence_index}/${row.total_sentences} 句`
  }
  return ''
}

const isProcessing = (status) => {
  return [
    'validating',
    'downloading_materials',
    'generating_subtitles',
    'synthesizing_videos',
    'concatenating',
    'uploading'
  ].includes(status)
}

const downloadVideo = (row) => {
  if (row && row.video_url) {
    const a = document.createElement('a')
    a.href = row.video_url
    a.download = `video_${row.chapter_title || 'generated'}.mp4`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  } else {
    ElMessage.warning('视频地址不可用')
  }
}
</script>

<style scoped>
.video-tasks-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: var(--text-primary);
}

.subtitle {
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  position: relative;
  overflow: hidden;
}

.stat-content {
  position: relative;
  z-index: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  line-height: 1.2;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.stat-icon {
  position: absolute;
  right: 20px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 48px;
  opacity: 0.1;
}

.stat-card.success .stat-value { color: var(--success-color); }
.stat-card.success .stat-icon { color: var(--success-color); }

.stat-card.warning .stat-value { color: var(--warning-color); }
.stat-card.warning .stat-icon { color: var(--warning-color); }

.stat-card.danger .stat-value { color: var(--danger-color); }
.stat-card.danger .stat-icon { color: var(--danger-color); }

/* 过滤器 */
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

/* 列表样式 */
.chapter-info {
  display: flex;
  flex-direction: column;
}

.chapter-title {
  font-weight: 500;
  color: var(--text-primary);
}

.project-title {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}

.progress-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.progress-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
