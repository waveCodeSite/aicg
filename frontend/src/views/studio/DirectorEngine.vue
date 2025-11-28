<template>
  <div class="director-mode">
    <div class="toolbar">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="选择章节" style="width: 300px">
          <el-select v-model="selectedChapterId" placeholder="请选择已确认的章节" @change="loadSentences">
            <el-option
              v-for="chapter in chapters"
              :key="chapter.id"
              :label="`第${chapter.chapter_number}章: ${chapter.title} (${chapter.status})`"
              :value="chapter.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item v-if="selectedChapterId">
          <el-button type="primary" @click="dialogVisible = true">
            批量生成图片提示词
          </el-button>
          <el-button type="warning" v-if="chapters.find(c => c.id === selectedChapterId)?.status === 'generated_prompts'" @click="batchGenerateImagesVisible = true">
            批量生成图片
          </el-button>
        </el-form-item>
      </el-form>
      
      <!-- 生成提示词对话框 -->
      <el-dialog
        v-model="dialogVisible"
        title="生成图片提示词"
        width="500px"
      >
        <el-form :inline="false" class="dialog-form">
          <el-form-item label="API Key" style="width: 100%">
            <el-select v-model="selectedApiKey" placeholder="选择API Key" style="width: 100%">
              <el-option
                v-for="key in apiKeys"
                :key="key.id"
                :label="`${key.name} (${key.provider})`"
                :value="key.id"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="风格" style="width: 100%">
            <el-select v-model="selectedStyle" placeholder="选择风格" style="width: 100%">
              <el-option label="电影质感 (Cinematic)" value="cinematic" />
              <el-option label="二次元 (Anime)" value="anime" />
              <el-option label="插画 (Illustration)" value="illustration" />
              <el-option label="水墨 (Ink)" value="ink" />
            </el-select>
          </el-form-item>
        </el-form>
        
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="dialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="generating" @click="generatePrompts">
              生成
            </el-button>
          </span>
        </template>
      </el-dialog>
      
      <!-- 重新生成提示词对话框 -->
      <el-dialog
        v-model="regenerateDialogVisible"
        title="重新生成提示词"
        width="500px"
      >
        <el-form :inline="false" class="dialog-form">
          <el-form-item label="API Key" style="width: 100%">
            <el-select v-model="regenerateApiKey" placeholder="选择API Key" style="width: 100%">
              <el-option
                v-for="key in apiKeys"
                :key="key.id"
                :label="`${key.name} (${key.provider})`"
                :value="key.id"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="风格" style="width: 100%">
            <el-select v-model="regenerateStyle" placeholder="选择风格" style="width: 100%">
              <el-option label="电影质感 (Cinematic)" value="cinematic" />
              <el-option label="二次元 (Anime)" value="anime" />
              <el-option label="插画 (Illustration)" value="illustration" />
              <el-option label="水墨 (Ink)" value="ink" />
            </el-select>
          </el-form-item>
        </el-form>
        
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="regenerateDialogVisible = false">取消</el-button>
            <el-button type="primary" :loading="regenerating" @click="regeneratePrompts">
              重新生成
            </el-button>
          </span>
        </template>
      </el-dialog>
      
      <!-- 批量生成图片对话框 -->
      <el-dialog
        v-model="batchGenerateImagesVisible"
        title="批量生成图片"
        width="500px"
      >
        <el-form :inline="false" class="dialog-form">
          <el-form-item label="API Key" style="width: 100%">
            <el-select v-model="batchGenerateImagesApiKey" placeholder="选择API Key" style="width: 100%">
              <el-option
                v-for="key in apiKeys"
                :key="key.id"
                :label="`${key.name} (${key.provider})`"
                :value="key.id"
              />
            </el-select>
          </el-form-item>
        </el-form>
        
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="batchGenerateImagesVisible = false">取消</el-button>
            <el-button type="primary" :loading="batchGeneratingImages" @click="batchGenerateImages">
              生成
            </el-button>
          </span>
        </template>
      </el-dialog>
    </div>

    <div class="content-area" v-loading="loading">
      <el-empty v-if="!sentences.length" description="请选择章节以开始" />
      
      <div v-else class="card-grid">
        <el-card
          v-for="(sentence, index) in sentences"
          :key="sentence.id"
          class="sentence-card"
          shadow="hover"
        >
          <template #header>
            <div class="card-header">
              <span class="card-index">#{{ index + 1 }}</span>
              <el-dropdown @command="handlePromptAction($event, sentence)">
                <span class="el-dropdown-link">
                  <el-icon><Setting /></el-icon>
                </span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="view">查看提示词</el-dropdown-item>
                    <el-dropdown-item command="edit">编辑提示词</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
          
          <div class="card-content">
            <p class="sentence-text">{{ sentence.content }}</p>
          </div>
          
          <div class="card-actions">
            <el-button
              type="primary"
              :loading="loadingStates[sentence.id]?.generatingPrompt"
              @click="handleRegeneratePrompt(sentence)"
              size="small"
              v-show="sentence.image_prompt"
            >
              <el-icon><MagicStick /></el-icon>
              重新生成提示词
            </el-button>
            
            <el-button
              type="success"
              :loading="loadingStates[sentence.id]?.generatingAudio"
              :disabled="!sentence.image_prompt"
              @click="generateSingleAudio(sentence)"
              size="small"
            >
              <el-icon><Microphone /></el-icon>
              生成音频
            </el-button>
            
            <el-button
              type="warning"
              :loading="loadingStates[sentence.id]?.generatingImage"
              :disabled="!sentence.image_prompt"
              @click="generateSingleImage(sentence)"
              size="small"
            >
              <el-icon><Camera /></el-icon>
              生成图片
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
    
    <!-- 查看/编辑提示词对话框 - 使用新组件 -->
    <PromptDialog
      v-model:visible="promptDialogVisible"
      v-model:sentence="currentSentence"
      :is-editing="isEditingPrompt"
      :dialog-title="promptDialogTitle"
      @save="handlePromptSave"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, MagicStick, Microphone, Camera } from '@element-plus/icons-vue'
import chaptersService from '@/services/chapters'
import apiKeysService from '@/services/apiKeys'
import api from '@/services/api'
import PromptDialog from '@/components/studio/PromptDialog.vue'

const route = useRoute()

// Props
const props = defineProps({
  projectId: {
    type: String,
    required: true
  }
})

const chapters = ref([])
const apiKeys = ref([])
const sentences = ref([])
const selectedChapterId = ref('')
const selectedApiKey = ref('')
const selectedStyle = ref('cinematic')
const loading = ref(false)
const generating = ref(false)
const dialogVisible = ref(false)

// 新添加的状态变量
const promptDialogVisible = ref(false)
const promptDialogTitle = ref('')
const currentSentence = ref({})
const isEditingPrompt = ref(false)
const loadingStates = ref({})

// 重新生成提示词相关状态
const regenerateDialogVisible = ref(false)
const regenerateApiKey = ref('')
const regenerateStyle = ref('cinematic')
const regenerating = ref(false)
const selectedSentenceIds = ref([])

// 批量生成图片相关状态
const batchGenerateImagesVisible = ref(false)
const batchGenerateImagesApiKey = ref('')
const batchGeneratingImages = ref(false)

// 加载已确认的章节
const loadChapters = async () => {
  try {
    const res = await chaptersService.getConfirmedChapters(props.projectId)
    chapters.value = res.chapters || []

    // 如果URL中有chapterId参数，自动选中该章节
    const chapterIdFromQuery = route.query.chapterId
    if (chapterIdFromQuery) {
      selectedChapterId.value = chapterIdFromQuery
      // 自动加载该章节的句子
      await loadSentences()
    }
  } catch (error) {
    console.error('加载章节失败', error)
  }
}

// 加载API Keys (模拟，实际应从API获取)
const loadApiKeys = async () => {
  const res = await apiKeysService.getAPIKeys()
  apiKeys.value = res.api_keys || []
}

// 加载句子 - 使用优化的批量接口
const loadSentences = async () => {
  if (!selectedChapterId.value) return
  
  loading.value = true
  try {
    // 使用新的批量接口，一次性获取所有句子
    const response = await api.get(`/chapters/${selectedChapterId.value}/sentences`)
    sentences.value = response.sentences || []
    
    // 初始化加载状态
    const initialLoadingStates = {}
    sentences.value.forEach(sentence => {
      initialLoadingStates[sentence.id] = {
        generatingPrompt: false,
        generatingAudio: false,
        generatingImage: false
      }
    })
    loadingStates.value = initialLoadingStates
  } catch (error) {
    console.error('加载句子失败', error)
    ElMessage.error('加载句子失败')
  } finally {
    loading.value = false
  }
}

// 生成提示词
const generatePrompts = async () => {
  if (!selectedChapterId.value || !selectedApiKey.value) {
    ElMessage.warning('请选择章节和API Key')
    return
  }
  
  generating.value = true
  try {
    // 调用新API - 使用正确的端点和请求格式
    const response = await api.post('/prompt/generate-prompts', {
      chapter_id: selectedChapterId.value,
      api_key_id: selectedApiKey.value,
      style: selectedStyle.value
    })
    
    if (response.success) {
      ElMessage.success(response.message)
      dialogVisible.value = false // 关闭对话框
      await loadChapters() // 重新加载章节列表以显示更新后的状态
      await loadSentences() // 重新加载以显示生成的Prompt
    }
  } catch (error) {
    console.error('生成失败', error)
    ElMessage.error('生成失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    generating.value = false
  }
}

// 处理提示词操作（查看/编辑）
const handlePromptAction = async (action, sentence) => {
  try {
    // 从接口获取最新的句子数据
    const response = await api.get(`/sentences/${sentence.id}`)
    const latestSentence = response
    
    currentSentence.value = { ...latestSentence }
    if (action === 'view') {
      promptDialogTitle.value = '查看提示词'
      isEditingPrompt.value = false
    } else if (action === 'edit') {
      promptDialogTitle.value = '编辑提示词'
      isEditingPrompt.value = true
    }
    promptDialogVisible.value = true
  } catch (error) {
    console.error('获取句子数据失败', error)
    ElMessage.error('获取句子数据失败，请稍后重试')
  }
}

// 生成单个句子的音频
const generateSingleAudio = async (sentence) => {
  // 更新加载状态
  loadingStates.value[sentence.id].generatingAudio = true
  
  try {
    const response = await api.post('/audio/generate-audio', {
      sentence_id: sentence.id
    })
    
    if (response.success) {
      ElMessage.success('音频生成成功')
      // 更新句子的音频URL
      sentence.audio_url = response.audio_url
    }
  } catch (error) {
    console.error('生成单个音频失败', error)
    ElMessage.error('生成音频失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    // 重置加载状态
    loadingStates.value[sentence.id].generatingAudio = false
  }
}

// 生成单个句子的图片
const generateSingleImage = async (sentence) => {
  // 更新加载状态
  loadingStates.value[sentence.id].generatingImage = true
  
  try {
    const response = await api.post('/image/generate-image', {
      sentence_id: sentence.id
    })
    
    if (response.success) {
      ElMessage.success('图片生成成功')
      // 更新句子的图片URL
      sentence.image_url = response.image_url
    }
  } catch (error) {
    console.error('生成单个图片失败', error)
    ElMessage.error('生成图片失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    // 重置加载状态
    loadingStates.value[sentence.id].generatingImage = false
  }
}

// 处理重新生成提示词
const handleRegeneratePrompt = (sentence) => {
  // 设置当前句子ID
  selectedSentenceIds.value = [sentence.id]
  // 打开重新生成提示词对话框
  regenerateDialogVisible.value = true
}

// 批量生成提示词
const regeneratePrompts = async () => {
  if (!regenerateApiKey.value || selectedSentenceIds.value.length === 0) {
    ElMessage.warning('请选择API Key和要重新生成的句子')
    return
  }
  
  regenerating.value = true
  try {
    // 调用新的后端接口
    const response = await api.post('/prompt/generate-prompts-ids', {
      api_key_id: regenerateApiKey.value,
      sentence_ids: selectedSentenceIds.value,
      style: regenerateStyle.value
    })
    
    if (response.success) {
      ElMessage.success(response.message)
      regenerateDialogVisible.value = false // 关闭对话框
      await loadSentences() // 重新加载以显示生成的Prompt
    }
  } catch (error) {
    console.error('重新生成失败', error)
    ElMessage.error('重新生成失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    regenerating.value = false
  }
}

// 批量生成图片
const batchGenerateImages = async () => {
  if (!batchGenerateImagesApiKey.value) {
    ElMessage.warning('请选择API Key')
    return
  }
  
  batchGeneratingImages.value = true
  try {
    // 调用批量生成图片的后端接口
    const response = await api.post('/image/generate-images', {
      chapter_id: selectedChapterId.value,
      api_key_id: batchGenerateImagesApiKey.value
    })
    
    if (response.success) {
      ElMessage.success(response.message)
      batchGenerateImagesVisible.value = false // 关闭对话框
      await loadChapters() // 重新加载章节列表以显示更新后的状态
    }
  } catch (error) {
    console.error('批量生成图片失败', error)
    ElMessage.error('批量生成图片失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    batchGeneratingImages.value = false
  }
}

// 处理提示词保存
const handlePromptSave = (updatedSentence) => {
  // 更新原句子的提示词
  const index = sentences.value.findIndex(s => s.id === updatedSentence.id)
  if (index !== -1) {
    sentences.value[index].image_prompt = updatedSentence.image_prompt
  }
}

onMounted(() => {
  loadChapters()
  loadApiKeys()
})</script>

<style scoped>
/* 页面基础样式 */
.director-mode {
  padding: var(--space-lg);
}

/* 工具栏样式 */
.toolbar {
  background: var(--bg-primary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  margin-bottom: var(--space-lg);
  box-shadow: var(--shadow-sm);
}

/* 内容区域样式 */
.content-area {
  margin-top: var(--space-lg);
}

/* 卡片网格样式 */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: var(--space-lg);
}

/* 卡片基础样式 */
.sentence-card {
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 16px;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 3px rgba(0, 0, 0, 0.06);
}

.sentence-card:hover {
  border-color: #c0c0c0;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08), 0 4px 12px rgba(0, 0, 0, 0.06);
  transform: translateY(-2px);
}

/* 卡片头部样式 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 22px;
  background: linear-gradient(135deg, #fafafa 0%, #f5f5f5 100%);
  border-bottom: 1px solid #e8e8e8;
  position: relative;
}

.card-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #202124;
  background: #ffffff;
  width: 24px;
  height: 24px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12);
  border: 1px solid #e0e0e0;
  font-family: 'Google Sans', 'Roboto', sans-serif;
}

/* 下拉菜单样式 */
.el-dropdown-link {
  color: #5f6368;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: #ffffff;
  border: 1px solid #e0e0e0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.el-dropdown-link:hover {
  color: #1a73e8;
  background: #f8f9fa;
  border-color: #1a73e8;
  box-shadow: 0 1px 3px rgba(26, 115, 232, 0.15);
}

/* 卡片内容样式 */
.card-content {
  padding: var(--space-lg);
}

.sentence-text {
  color: var(--text-primary);
  font-size: var(--text-base);
  line-height: var(--leading-relaxed);
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 卡片操作区域样式 */
.card-actions {
  display: flex;
  gap: var(--space-sm);
  padding: var(--space-md) var(--space-lg);
  background: var(--bg-primary);
  border-top: 1px solid var(--border-primary);
}

.card-actions .el-button {
  flex: 1;
  height: 36px;
  font-size: var(--text-sm);
  font-weight: 500;
  border-radius: var(--radius-base);
  border: 1px solid var(--border-primary);
  background: var(--bg-primary);
  color: var(--text-primary);
  box-shadow: none;
  transition: all var(--transition-fast);
}

.card-actions .el-button:hover {
  background: var(--bg-secondary);
  border-color: var(--border-secondary);
  box-shadow: none;
}

.card-actions .el-button--primary {
  background: var(--primary-color);
  border-color: var(--primary-color);
  color: white;
}

.card-actions .el-button--primary:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
}

.card-actions .el-button--success {
  background: var(--success-color);
  border-color: var(--success-color);
  color: white;
}

.card-actions .el-button--success:hover {
  background: var(--success-dark);
  border-color: var(--success-dark);
}

.card-actions .el-button--warning {
  background: var(--warning-color);
  border-color: var(--warning-color);
  color: white;
}

.card-actions .el-button--warning:hover {
  background: var(--warning-dark);
  border-color: var(--warning-dark);
}

.card-actions .el-button:disabled {
  background: var(--bg-tertiary);
  border-color: var(--border-primary);
  color: var(--text-tertiary);
  box-shadow: none;
}

/* 表单样式 */
.filter-form {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  flex-wrap: wrap;
}

.filter-form .el-form-item {
  margin-bottom: 0;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .card-grid {
    grid-template-columns: 1fr;
    gap: var(--space-md);
  }

  .filter-form {
    flex-direction: column;
    align-items: stretch;
  }

  .card-actions {
    flex-direction: column;
  }
}
</style>