<template>
  <div class="transition-panel">
    <div class="panel-header">
      <h3>过渡视频</h3>
      <div class="actions">
        <el-button 
          type="primary"
          :loading="creating"
          :disabled="!canCreate"
          @click="handleCreateClick"
        >
          批量创建
        </el-button>
        <el-button 
          type="success"
          :loading="generating"
          :disabled="transitions.length === 0"
          @click="handleBatchGenerateClick"
        >
          批量生成视频
        </el-button>
      </div>
    </div>

    <div class="transition-list">
      <el-empty v-if="transitions.length === 0" description="暂无过渡，请先创建过渡" />
      
      <div v-else class="transition-grid">
        <div 
          v-for="transition in transitions" 
          :key="transition.id"
          class="transition-card"
        >
          <div class="transition-header">
            <span class="transition-number">过渡 {{ transition.order_index }}</span>
            <div class="transition-actions">
              <el-button
                v-if="!transition.video_url"
                type="primary"
                size="small"
                :loading="generatingIds.has(transition.id)"
                :disabled="generatingIds.has(transition.id) || transition.status === 'processing'"
                @click="handleGenerateVideo(transition)"
              >
                生成视频
              </el-button>
              <el-button
                v-else
                type="warning"
                size="small"
                :loading="generatingIds.has(transition.id)"
                :disabled="generatingIds.has(transition.id) || transition.status === 'processing'"
                @click="handleRegenerateVideo(transition)"
              >
                重新生成
              </el-button>
              <el-button
                v-if="transition.status === 'processing'"
                type="info"
                size="small"
                :loading="refreshingIds.has(transition.id)"
                :icon="Refresh"
                @click="handleRefreshStatus(transition)"
              >
                刷新状态
              </el-button>
              <el-button
                v-if="transition.video_url"
                type="info"
                size="small"
                @click="handleShowHistory(transition)"
              >
                <el-icon><Clock /></el-icon>
              </el-button>
              <el-button
                type="primary"
                size="small"
                @click="handleEditPrompt(transition)"
              >
                编辑提示词
              </el-button>
              <el-button
                type="danger"
                size="small"
                @click="handleDelete(transition)"
              >
                删除
              </el-button>
            </div>
          </div>
          
          <div class="transition-content">
            <!-- 场景信息 -->
            <div v-if="transition.from_shot && transition.to_shot" class="scene-info">
              <el-tag size="small" type="info">
                场景 {{ transition.from_shot.scene_order }} 
                <template v-if="transition.from_shot.scene_order !== transition.to_shot.scene_order">
                  → 场景 {{ transition.to_shot.scene_order }}
                </template>
              </el-tag>
            </div>

            <!-- 起始分镜 -->
            <div class="shot-info">
              <span class="label">起始分镜:</span>
              <div class="shot-detail">
                <p class="shot-description">{{ transition.from_shot?.shot || getShotDescription(transition.from_shot_id) }}</p>
                <p v-if="transition.from_shot?.dialogue" class="shot-dialogue">
                  💬 "{{ transition.from_shot.dialogue }}"
                </p>
              </div>
            </div>

            <!-- 结束分镜 -->
            <div class="shot-info">
              <span class="label">结束分镜:</span>
              <div class="shot-detail">
                <p class="shot-description">{{ transition.to_shot?.shot || getShotDescription(transition.to_shot_id) }}</p>
                <p v-if="transition.to_shot?.dialogue" class="shot-dialogue">
                  💬 "{{ transition.to_shot.dialogue }}"
                </p>
              </div>
            </div>

            <!-- 提示词预览 -->
            <div class="prompt-preview">
              <span class="label">视频提示词:</span>
              <p class="prompt-text">{{ transition.video_prompt || '未生成' }}</p>
            </div>
          </div>

          <div v-if="transition.video_url" class="transition-video" @click="handlePreviewVideo(transition.video_url)">
            <video :src="transition.video_url" controls @click.stop />
            <div class="video-overlay">
              <el-icon :size="30"><ZoomIn /></el-icon>
              <span>点击放大</span>
            </div>
          </div>
          <div v-else-if="transition.status === 'processing'" class="transition-placeholder">
            <el-icon :size="40"><Loading /></el-icon>
            <p>生成中...</p>
          </div>
          <div v-else-if="transition.status === 'failed'" class="transition-placeholder error">
            <el-icon :size="40" color="#f56c6c"><CircleClose /></el-icon>
            <p class="error-text">生成失败</p>
            <p v-if="transition.error_message" class="error-message">{{ formatErrorMessage(transition.error_message) }}</p>
          </div>
          <div v-else class="transition-placeholder">
            <el-icon :size="40"><VideoCamera /></el-icon>
            <p>待生成</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 批量创建对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="批量创建过渡"
      width="500px"
    >
      <el-form :model="createFormData" label-width="100px">
        <el-form-item label="API Key">
          <el-select v-model="createFormData.apiKeyId" placeholder="请选择API Key" style="width: 100%">
            <el-option
              v-for="key in apiKeys"
              :key="key.id"
              :label="`${key.name} (${key.provider})`"
              :value="key.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="文本模型">
          <el-select 
            v-model="createFormData.model" 
            placeholder="选择模型" 
            style="width: 100%"
            :loading="loadingTextModels"
            filterable
            allow-create
            default-first-option
          >
            <el-option
              v-for="model in textModelOptions"
              :key="model"
              :label="model"
              :value="model"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleCreateConfirm" :disabled="!createFormData.apiKeyId || !createFormData.model">确定</el-button>
      </template>
    </el-dialog>

    <!-- 批量生成视频对话框 -->
    <el-dialog
      v-model="showBatchGenerateDialog"
      title="批量生成过渡视频"
      width="500px"
    >
      <el-form :model="batchGenerateFormData" label-width="100px">
        <el-form-item label="API Key">
          <el-select v-model="batchGenerateFormData.apiKeyId" placeholder="请选择API Key" style="width: 100%">
            <el-option
              v-for="key in apiKeys"
              :key="key.id"
              :label="`${key.name} (${key.provider})`"
              :value="key.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="视频模型">
          <el-select 
            v-model="batchGenerateFormData.videoModel" 
            placeholder="选择模型" 
            style="width: 100%"
            :loading="loadingVideoModels"
            filterable
            allow-create
            default-first-option
          >
            <el-option
              v-for="model in videoModelOptions"
              :key="model"
              :label="model"
              :value="model"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBatchGenerateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleBatchGenerateConfirm" :disabled="!batchGenerateFormData.apiKeyId || !batchGenerateFormData.videoModel">确定</el-button>
      </template>
    </el-dialog>

    <!-- 编辑提示词对话框 -->
    <el-dialog
      v-model="showEditPromptDialog"
      title="编辑过渡提示词"
      width="700px"
    >
      <el-form :model="editPromptFormData" label-width="100px">
        <el-form-item label="API Key">
          <el-select
            v-model="editPromptFormData.apiKeyId"
            placeholder="选择API Key"
            style="width: 100%"
            @change="handleEditApiKeyChange"
          >
            <el-option
              v-for="key in apiKeys"
              :key="key.id"
              :label="`${key.provider} - ${key.name}`"
              :value="key.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="文本模型">
          <el-select
            v-model="editPromptFormData.model"
            placeholder="选择模型"
            style="width: 100%"
            :loading="loadingTextModels"
          >
            <el-option
              v-for="model in textModelOptions"
              :key="model"
              :label="model"
              :value="model"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="视频提示词">
          <div class="prompt-editor-header">
            <el-button
              size="small"
              type="primary"
              :loading="regeneratingPromptIds.has(editPromptFormData.transitionId)"
              :disabled="regeneratingPromptIds.has(editPromptFormData.transitionId) || !editPromptFormData.apiKeyId || !editPromptFormData.model"
              @click="handleRegeneratePrompt"
            >
              <el-icon><Refresh /></el-icon>
              重新生成提示词
            </el-button>
          </div>
          <el-input
            v-model="editPromptFormData.prompt"
            type="textarea"
            :rows="12"
            placeholder="视频生成提示词"
            style="font-family: monospace; font-size: 12px; margin-top: 8px;"
          />
          <div style="margin-top: 8px; color: #909399; font-size: 12px;">
            💡 提示词用于生成两个分镜之间的过渡视频。您可以根据需要调整。
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditPromptDialog = false">取消</el-button>
        <el-button type="primary" @click="handleEditPromptConfirm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 单个生成视频对话框 -->
    <el-dialog
      v-model="showSingleGenerateDialog"
      :title="singleGenerateDialogType === 'generate' ? '生成过渡视频' : '重新生成过渡视频'"
      width="700px"
    >
      <el-form :model="singleGenerateFormData" label-width="100px">
        <el-form-item label="API Key">
          <el-select v-model="singleGenerateFormData.apiKeyId" placeholder="请选择API Key" style="width: 100%">
            <el-option
              v-for="key in apiKeys"
              :key="key.id"
              :label="`${key.name} (${key.provider})`"
              :value="key.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="视频模型">
          <el-select 
            v-model="singleGenerateFormData.videoModel" 
            placeholder="选择模型" 
            style="width: 100%"
            :loading="loadingVideoModels"
            filterable
            allow-create
            default-first-option
          >
            <el-option
              v-for="model in videoModelOptions"
              :key="model"
              :label="model"
              :value="model"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="视频提示词">
          <el-input
            v-model="singleGenerateFormData.prompt"
            type="textarea"
            :rows="12"
            placeholder="视频生成提示词（可编辑调整）"
            style="font-family: monospace; font-size: 12px;"
          />
          <div style="margin-top: 8px; color: #909399; font-size: 12px;">
            💡 提示词用于生成两个分镜之间的过渡视频。您可以根据需要调整。
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSingleGenerateDialog = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="handleSingleGenerateConfirm" 
          :disabled="!singleGenerateFormData.apiKeyId || !singleGenerateFormData.videoModel"
        >
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 视频预览对话框 -->
    <el-dialog
      v-model="showVideoPreview"
      title="视频预览"
      width="80%"
      :close-on-click-modal="true"
    >
      <div class="video-preview-container">
        <video v-if="previewVideoUrl" :src="previewVideoUrl" controls autoplay style="width: 100%; max-height: 70vh;" />
      </div>
    </el-dialog>

    <!-- 历史记录面板 -->
    <GenerationHistoryPanel
      v-model="showHistory"
      resource-type="transition_video"
      :resource-id="currentHistoryTransitionId"
      media-type="video"
      @selected="handleHistorySelected"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, VideoCamera, CircleClose, Refresh, ZoomIn, Clock } from '@element-plus/icons-vue'
import { useTransitionWorkflow } from '@/composables/useTransitionWorkflow'
import GenerationHistoryPanel from '@/components/GenerationHistoryPanel.vue'
import { pollTaskStatus } from '@/utils/taskPoller'
import api from '@/services/api'

const props = defineProps({
  scriptId: String,
  apiKeys: Array
})

const {
  transitions,
  creating,
  generating,
  generatingIds,
  loadTransitions,
  createTransitions,
  generateTransitionVideos,
  updateTransitionPrompt,
  generateSingleVideo,
  deleteTransition
} = useTransitionWorkflow()

// 刷新状态
const refreshingIds = ref(new Set())

// 视频预览
const showVideoPreview = ref(false)
const previewVideoUrl = ref('')

// 对话框状态
const showCreateDialog = ref(false)
const showBatchGenerateDialog = ref(false)
const showEditPromptDialog = ref(false)
const showSingleGenerateDialog = ref(false)
const singleGenerateDialogType = ref('generate')

// 表单数据
const createFormData = ref({
  apiKeyId: '',
  model: ''
})

const batchGenerateFormData = ref({
  apiKeyId: '',
  videoModel: 'veo3.1-components'
})

const editPromptFormData = ref({
  transitionId: '',
  prompt: '',
  apiKeyId: '',
  model: ''
})

const singleGenerateFormData = ref({
  transitionId: '',
  apiKeyId: '',
  videoModel: 'veo3.1-components',
  prompt: ''
})

// 模型选项
const textModelOptions = ref([])
const videoModelOptions = ref([])
const loadingTextModels = ref(false)
const loadingVideoModels = ref(false)

// 历史记录相关
const showHistory = ref(false)
const currentHistoryTransitionId = ref('')

// 重新生成提示词相关 - 使用Set支持并发
const regeneratingPromptIds = ref(new Set())

// 计算属性
const canCreate = computed(() => {
  return props.apiKeys && props.apiKeys.length > 0
})

// 监听API Key变化加载模型
watch(() => createFormData.value.apiKeyId, async (newKeyId) => {
  if (!newKeyId) {
    textModelOptions.value = []
    createFormData.value.model = ''
    return
  }
  
  loadingTextModels.value = true
  try {
    const models = await api.get(`/api-keys/${newKeyId}/models?type=text`)
    textModelOptions.value = models || []
    if (textModelOptions.value.length > 0) {
      createFormData.value.model = textModelOptions.value[0]
    }
  } catch (error) {
    console.error('获取模型列表失败', error)
    ElMessage.warning('获取模型列表失败')
    textModelOptions.value = []
    createFormData.value.model = ''
  } finally {
    loadingTextModels.value = false
  }
})

watch(() => batchGenerateFormData.value.apiKeyId, async (newKeyId) => {
  if (!newKeyId) {
    videoModelOptions.value = []
    batchGenerateFormData.value.videoModel = 'veo_3_1-fast'
    return
  }
  
  loadingVideoModels.value = true
  try {
    const models = await api.get(`/api-keys/${newKeyId}/models?type=video`)
    videoModelOptions.value = models || []
    if (videoModelOptions.value.length > 0) {
      batchGenerateFormData.value.videoModel = videoModelOptions.value[0]
    }
  } catch (error) {
    console.error('获取模型列表失败', error)
    ElMessage.warning('获取模型列表失败')
    videoModelOptions.value = ['veo_3_1-fast']
    batchGenerateFormData.value.videoModel = 'veo_3_1-fast'
  } finally {
    loadingVideoModels.value = false
  }
})

watch(() => singleGenerateFormData.value.apiKeyId, async (newKeyId) => {
  if (!newKeyId) {
    videoModelOptions.value = []
    singleGenerateFormData.value.videoModel = 'veo_3_1-fast'
    return
  }
  
  loadingVideoModels.value = true
  try {
    const models = await api.get(`/api-keys/${newKeyId}/models?type=video`)
    // API直接返回数组
    videoModelOptions.value = Array.isArray(models) ? models : []
    if (videoModelOptions.value.length > 0) {
      singleGenerateFormData.value.videoModel = videoModelOptions.value[0]
    }
  } catch (error) {
    console.error('获取模型列表失败', error)
    ElMessage.warning('获取模型列表失败')
    videoModelOptions.value = ['veo_3_1-fast']
    singleGenerateFormData.value.videoModel = 'veo_3_1-fast'
  } finally {
    loadingVideoModels.value = false
  }
})

// 加载文本模型列表
const loadTextModels = async (apiKeyId) => {
  if (!apiKeyId) return
  
  loadingTextModels.value = true
  try {
    const response = await api.get(`/api-keys/${apiKeyId}/models`, {
      params: { model_type: 'text' }
    })
    // API直接返回数组
    textModelOptions.value = Array.isArray(response) ? response : []
  } catch (error) {
    console.error('加载文本模型失败:', error)
    textModelOptions.value = []
  } finally {
    loadingTextModels.value = false
  }
}

// 加载transitions
watch(() => props.scriptId, (newId) => {
  if (newId) {
    loadTransitions(newId)
  }
}, { immediate: true })

// 辅助函数
const getShotDescription = (shotId) => {
  // TODO: 从shots数据中获取描述
  return `镜头 ${shotId.substring(0, 8)}...`
}

// 批量创建
const handleCreateClick = () => {
  createFormData.value = {
    apiKeyId: props.apiKeys[0]?.id || '',
    model: ''
  }
  showCreateDialog.value = true
}

const handleCreateConfirm = async () => {
  if (!createFormData.value.apiKeyId || !createFormData.value.model) {
    return
  }
  await createTransitions(props.scriptId, createFormData.value.apiKeyId, createFormData.value.model)
  showCreateDialog.value = false
}

// 批量生成
const handleBatchGenerateClick = () => {
  batchGenerateFormData.value = {
    apiKeyId: props.apiKeys[0]?.id || '',
    videoModel: 'veo3.1-components'
  }
  showBatchGenerateDialog.value = true
}

const handleBatchGenerateConfirm = async () => {
  if (!batchGenerateFormData.value.apiKeyId || !batchGenerateFormData.value.videoModel) {
    return
  }
  await generateTransitionVideos(props.scriptId, batchGenerateFormData.value.apiKeyId, batchGenerateFormData.value.videoModel)
  showBatchGenerateDialog.value = false
}

// 编辑提示词
const handleEditPrompt = (transition) => {
  editPromptFormData.value = {
    transitionId: transition.id,
    prompt: transition.video_prompt || '',
    apiKeyId: props.apiKeys?.[0]?.id || '',
    model: textModelOptions.value[0] || ''
  }
  
  // 如果有API Key，加载模型列表
  if (editPromptFormData.value.apiKeyId) {
    loadTextModels(editPromptFormData.value.apiKeyId)
  }
  
  showEditPromptDialog.value = true
}

// API Key变化时加载模型
const handleEditApiKeyChange = async (apiKeyId) => {
  if (apiKeyId) {
    await loadTextModels(apiKeyId)
    // 自动选择第一个模型
    if (textModelOptions.value.length > 0) {
      editPromptFormData.value.model = textModelOptions.value[0]
    }
  }
}

const handleEditPromptConfirm = async () => {
  const success = await updateTransitionPrompt(
    editPromptFormData.value.transitionId,
    editPromptFormData.value.prompt
  )
  if (success) {
    await loadTransitions(props.scriptId)
    showEditPromptDialog.value = false
  }
}

// 单个生成
const handleGenerateVideo = (transition) => {
  singleGenerateDialogType.value = 'generate'
  singleGenerateFormData.value = {
    transitionId: transition.id,
    apiKeyId: props.apiKeys[0]?.id || '',
    videoModel: 'veo_3_1-fast',
    prompt: transition.video_prompt || ''
  }
  showSingleGenerateDialog.value = true
}

const handleRegenerateVideo = (transition) => {
  singleGenerateDialogType.value = 'regenerate'
  singleGenerateFormData.value = {
    transitionId: transition.id,
    apiKeyId: props.apiKeys[0]?.id || '',
    videoModel: 'veo_3_1-fast',
    prompt: transition.video_prompt || ''
  }
  showSingleGenerateDialog.value = true
}

const handleSingleGenerateConfirm = async () => {
  if (!singleGenerateFormData.value.apiKeyId || !singleGenerateFormData.value.videoModel) {
    return
  }
  
  // 防止重复点击
  if (generatingIds.value.has(singleGenerateFormData.value.transitionId)) {
    ElMessage.warning('视频正在生成中，请勿重复提交')
    return
  }

  try {
    await generateSingleVideo(
      singleGenerateFormData.value.transitionId,
      props.scriptId,
      singleGenerateFormData.value.apiKeyId,
      singleGenerateFormData.value.videoModel,
      singleGenerateFormData.value.prompt
    )
    ElMessage.success('视频生成任务已提交')
    await loadTransitions(props.scriptId)
  } catch (error) {
    console.error('生成失败:', error)
    ElMessage.error('生成失败: ' + (error.response?.data?.detail || error.message))
  }
  showSingleGenerateDialog.value = false
}

// 刷新单个过渡状态
const handleRefreshStatus = async (transition) => {
  try {
    refreshingIds.value.add(transition.id)
    
    // 调用API获取最新状态
    const response = await api.get(`/movie/transitions/${transition.id}`)
    
    // 更新本地数据
    const index = transitions.value.findIndex(t => t.id === transition.id)
    if (index !== -1) {
      transitions.value[index] = response
      
      // 显示状态信息
      if (response.status === 'completed') {
        ElMessage.success('视频已生成完成！')
      } else if (response.status === 'failed') {
        ElMessage.error(`生成失败: ${response.error_message || '未知错误'}`)
      } else if (response.status === 'processing') {
        ElMessage.info('视频仍在生成中...')
      }
    }
  } catch (error) {
    console.error('刷新状态失败:', error)
    ElMessage.error('刷新状态失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    refreshingIds.value.delete(transition.id)
  }
}

// 预览视频
const handlePreviewVideo = (videoUrl) => {
  previewVideoUrl.value = videoUrl
  showVideoPreview.value = true
}

// 格式化错误信息
const formatErrorMessage = (errorMsg) => {
  if (!errorMsg) return '未知错误'
  
  try {
    // 尝试解析JSON格式的错误
    const errorObj = JSON.parse(errorMsg)
    if (errorObj.message) {
      return errorObj.message
    }
    return JSON.stringify(errorObj, null, 2)
  } catch {
    // 不是JSON，直接返回
    return errorMsg
  }
}

// 显示历史记录
const handleShowHistory = (transition) => {
  currentHistoryTransitionId.value = transition.id
  showHistory.value = true
}

// 历史记录选择后的处理
const handleHistorySelected = async (history) => {
  ElMessage.success('已切换到选中的历史版本')
  await loadTransitions(props.scriptId)
}

// 重新生成提示词
const handleRegeneratePrompt = async () => {
  if (!editPromptFormData.value.transitionId) {
    ElMessage.error('未找到过渡ID')
    return
  }

  if (!editPromptFormData.value.apiKeyId) {
    ElMessage.error('请选择API Key')
    return
  }

  if (!editPromptFormData.value.model) {
    ElMessage.error('请选择文本模型')
    return
  }

  const transitionId = editPromptFormData.value.transitionId
  
  // 检查是否已在重新生成中
  if (regeneratingPromptIds.value.has(transitionId)) {
    ElMessage.warning('该过渡正在重新生成提示词，请稍候')
    return
  }

  regeneratingPromptIds.value.add(transitionId)

  try {
    const response = await api.post(
      `/movie/transitions/${transitionId}/regenerate-prompt`,
      {
        api_key_id: editPromptFormData.value.apiKeyId,
        model: editPromptFormData.value.model
      }
    )

    const taskId = response.task_id
    ElMessage.info('正在重新生成提示词...')

    const result = await pollTaskStatus(taskId)

    if (result.success) {
      editPromptFormData.value.prompt = result.video_prompt
      ElMessage.success('提示词已重新生成')
    } else {
      throw new Error(result.error || '生成失败')
    }
  } catch (error) {
    console.error('重新生成提示词失败:', error)
    ElMessage.error('重新生成失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    regeneratingPromptIds.value.delete(transitionId)
  }
}

// 删除
const handleDelete = async (transition) => {
  try {
    await ElMessageBox.confirm('确定要删除这个过渡吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteTransition(transition.id, props.scriptId)
  } catch (error) {
    // 用户取消
  }
}
</script>

<style scoped>
.transition-panel {
  padding: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 12px;
}

.transition-list {
  margin-top: 20px;
}

.transition-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.transition-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  transition: all 0.3s;
  background: white;
}

.transition-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transform: translateY(-2px);
}

.transition-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 8px;
}

.transition-number {
  font-weight: 600;
  color: #409eff;
  font-size: 14px;
  flex-shrink: 0;
}

.transition-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.transition-content {
  margin-bottom: 12px;
}

.scene-info {
  margin-bottom: 12px;
}

.shot-info {
  margin-bottom: 12px;
  font-size: 13px;
}

.shot-info .label {
  font-weight: 600;
  color: #606266;
  display: block;
  margin-bottom: 4px;
}

.shot-detail {
  padding-left: 12px;
  border-left: 3px solid #e4e7ed;
}

.shot-description {
  margin: 0 0 4px 0;
  color: #606266;
  line-height: 1.6;
}

.shot-dialogue {
  margin: 0;
  color: #909399;
  font-style: italic;
  font-size: 12px;
}

.shot-info .value {
  color: #909399;
}

.prompt-preview {
  margin-top: 12px;
}

.prompt-preview .label {
  font-weight: 600;
  color: #606266;
  display: block;
  margin-bottom: 4px;
}

.prompt-text {
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
  margin: 0;
  max-height: 150px;
  overflow-y: auto;
  font-family: monospace;
  background: #f5f7fa;
  padding: 8px;
  border-radius: 4px;
}

.transition-video {
  margin-top: 12px;
  position: relative;
  cursor: pointer;
  
  &:hover .video-overlay {
    opacity: 1;
  }
}

.transition-video video {
  width: 100%;
  border-radius: 4px;
  background: #000;
}

.video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0;
  transition: opacity 0.3s;
  border-radius: 4px;
  pointer-events: none;
  
  span {
    margin-top: 8px;
    font-size: 14px;
  }
}

.video-preview-container {
  display: flex;
  justify-content: center;
  align-items: center;
  background: #000;
  border-radius: 8px;
}

.prompt-editor-header {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 8px;
}

.transition-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  background: #f5f7fa;
  border-radius: 8px;
  color: #909399;
  
  p {
    margin-top: 12px;
    font-size: 14px;
  }
  
  &.error {
    background: #fef0f0;
    border: 1px solid #fde2e2;
    
    .error-text {
      color: #f56c6c;
      font-weight: 500;
    }
    
    .error-message {
      margin-top: 8px;
      padding: 8px 16px;
      background: #fff;
      border-radius: 4px;
      color: #606266;
      font-size: 12px;
      max-width: 80%;
      text-align: center;
      word-break: break-word;
    }
  }
}
</style>
