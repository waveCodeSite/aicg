<template>
  <div class="movie-studio">
    <!-- 顶部导航栏 -->
    <div class="studio-header">
      <div class="header-left">
        <el-button @click="goBack" icon="ArrowLeft">返回</el-button>
        <span class="chapter-title">{{ chapter?.title || '未命名章节' }}</span>
      </div>
      <div class="header-right">
        <el-space>
          <el-select v-model="genConfig.api_key_id" placeholder="选择 Key" style="width: 150px" size="small">
            <el-option v-for="k in apiKeys" :key="k.id" :label="k.name" :value="k.id" />
          </el-select>
          <el-button @click="showCastManager = !showCastManager" :type="showCastManager ? 'primary' : 'default'" size="small" plain>
            {{ showCastManager ? '剧组' : '显示剧组' }}
          </el-button>
          <el-button type="success" :icon="Image" @click="handleGenerateKeyframes" :disabled="!script" :loading="generatingKeyframes" size="small">批量绘图</el-button>
          <el-button type="warning" :icon="VideoPlay" @click="handleBatchProduceVideos" :disabled="!script || !allCharactersReady" :loading="batchProducing" size="small">批量视频</el-button>
          <el-button type="primary" @click="handleGenerateScript" :loading="generatingScript" size="small">
            {{ script ? '重制剧本' : '生成 AI 剧本' }}
          </el-button>
        </el-space>
      </div>
    </div>

    <!-- 主体区域 -->
    <div class="studio-body">
      <!-- 主工作区 -->
      <div class="studio-content" v-loading="loading || isPolling" :element-loading-text="isPolling ? 'AI正在创作剧本，请稍候...' : '加载中...'">
        <!-- 脚本看板 -->
        <div v-if="script" class="script-board">
          <div v-for="scene in script.scenes" :key="scene.order_index" class="scene-card">
            <div class="scene-header">
              <h3>场景 {{ scene.order_index }}: {{ scene.location }}</h3>
              <span class="scene-meta">{{ scene.time_of_day }} | {{ scene.atmosphere }}</span>
            </div>
            <p class="scene-desc">{{ scene.description }}</p>
  
            <div class="shots-grid">
              <el-card v-for="shot in scene.shots" :key="shot.order_index" class="shot-card" shadow="hover">
                <div class="shot-visual">
                  <!-- 视频播放器 (如果有视频) -->
                  <div v-if="shot.video_url && showVideo[shot.id]" class="video-container">
                    <video :src="shot.video_url" controls class="shot-video" :poster="shot.first_frame_url"></video>
                    <el-button class="view-image-btn" size="small" circle @click="toggleShotView(shot.id, false)">
                      <el-icon><Picture /></el-icon>
                    </el-button>
                  </div>
                  
                  <!-- 首帧图 -->
                  <template v-else>
                    <el-image :src="shot.first_frame_url" fit="cover" class="shot-preview">
                      <template #placeholder>
                        <div class="image-placeholder">
                          <el-icon><Picture /></el-icon>
                          <span>{{ shot.status === 'processing' ? '视频生成中...' : '等待生成首帧' }}</span>
                        </div>
                      </template>
                    </el-image>
                    <div class="shot-actions">
                      <el-tooltip v-if="!shot.first_frame_url" content="请先生成首帧图">
                        <el-button circle icon="VideoPlay" type="info" disabled></el-button>
                      </el-tooltip>
                      <el-tooltip v-else-if="!canProduceShot(shot)" content="部分角色形象缺失，请先生成">
                         <el-button circle icon="VideoPlay" type="info" disabled></el-button>
                      </el-tooltip>
                      <el-button v-else circle icon="VideoPlay" type="primary" @click="handleProduceShot(shot)" :loading="shot.status === 'processing'"></el-button>
                    </div>
                  </template>
                </div>
                <div class="shot-info">
                  <div class="shot-header-row">
                    <div class="shot-index">SHOT {{ shot.order_index }}</div>
                    <el-dropdown trigger="click" @command="(cmd) => handleShotCommand(cmd, shot)">
                        <el-button link><el-icon><MoreFilled /></el-icon></el-button>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item command="regenerate-keyframe">重新生成首帧</el-dropdown-item>
                            <el-dropdown-item v-if="shot.video_url" command="regenerate-video">重新生成视频</el-dropdown-item>
                            <el-dropdown-item v-if="shot.video_url && !showVideo[shot.id]" command="switch-video">切换到视频</el-dropdown-item>
                          </el-dropdown-menu>
                        </template>
                    </el-dropdown>
                  </div>
                  <div class="shot-desc">{{ shot.visual_description }}</div>
                  <div v-if="shot.dialogue" class="shot-dialogue">
                    <el-icon><Mic /></el-icon>
                    <span class="dialogue-text">"{{ shot.dialogue }}"</span>
                  </div>
                  <div v-if="shot.video_prompt" class="shot-prompt-tag">
                    <el-popover placement="top" title="Video Prompt (English)" :width="300" trigger="hover" :content="shot.video_prompt">
                      <template #reference>
                        <el-tag size="small" type="info" class="mt-2">PROMPT</el-tag>
                      </template>
                    </el-popover>
                  </div>
                </div>
              </el-card>
            </div>
          </div>
        </div>
  
        <!-- 空状态 -->
        <el-empty v-else description="尚未生成电影剧本，点击上方按钮开始适配" />
      </div>

      <!-- 侧边栏：角色管理 (Cast Manager) -->
      <transition name="slide-fade">
        <div v-if="showCastManager" class="studio-sidebar">
          <div class="sidebar-header">
            <h3>剧组角色</h3>
            <el-button type="primary" link :icon="Cpu" @click="handleExtractCharacters" :disabled="!script" :loading="extractingCharacters">同步角色</el-button>
          </div>
          <div class="cast-list">
            <el-card v-for="char in characters" :key="char.id" class="char-card" shadow="never">
              <div class="char-header">
                  <el-image 
                    :src="char.avatar_url" 
                    :preview-src-list="[char.avatar_url]" 
                    class="char-avatar"
                    preview-teleported
                    fit="cover"
                  >
                    <template #error>
                      <el-avatar :size="40" shape="square">{{ char.name[0] }}</el-avatar>
                    </template>
                  </el-image>
                  <div class="char-name">{{ char.name }}</div>
                  <el-button 
                    link 
                    type="primary" 
                    icon="MagicStick" 
                    @click="handleGenerateAvatar(char)"
                    :loading="generatingAvatarId === char.id"
                  >生成形象</el-button>
              </div>
              <p class="char-role">{{ char.role_description }}</p>
              <div class="char-traits">
                <el-tooltip :content="char.visual_traits" placement="top">
                    <el-tag size="small" effect="plain">视觉特征</el-tag>
                </el-tooltip>
                <el-tooltip :content="char.dialogue_traits" placement="top">
                    <el-tag size="small" type="success" effect="plain">对话风格</el-tag>
                </el-tooltip>
              </div>
            </el-card>
            <el-empty v-if="characters.length === 0" image-size="60" description="暂无角色" />
          </div>
        </div>
      </transition>
    </div>


    <!-- 统一生成配置弹窗 -->
    <el-dialog v-model="showGenerateDialog" :title="getDialogTitle()" width="400px">
      <el-form :model="genConfig">
        <el-form-item label="API Key">
          <el-select v-model="genConfig.api_key_id" placeholder="请选择 API Key" style="width: 100%">
            <el-option v-for="k in apiKeys" :key="k.id" :label="`${k.name} (${k.provider})`" :value="k.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="dialogMode === 'avatar'" label="艺术风格" style="width: 100%">
          <el-select v-model="genConfig.style" placeholder="请选择风格" style="width: 100%">
            <el-option label="电影质感 (Cinematic)" value="cinematic" />
            <el-option label="二次元 (Anime)" value="anime" />
            <el-option label="赛博朋克 (Cyberpunk)" value="cyberpunk" />
            <el-option label="复古油画 (Oil Painting)" value="oil_painting" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="dialogMode === 'avatar'" label="提示词" style="width: 100%">
          <el-input 
            v-model="genConfig.prompt" 
            type="textarea" 
            :rows="6" 
            placeholder="生成形象的提示词"
          />
        </el-form-item>
        <el-form-item label="选择模型">
          <el-select 
            v-model="genConfig.model" 
            placeholder="请选择或输入模型" 
            filterable 
            allow-create 
            :loading="loadingModels"
            style="width: 100%"
          >
            <el-option v-for="model in modelOptions" :key="model" :label="model" :value="model" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showGenerateDialog = false">取消</el-button>
          <el-button type="primary" @click="handleDialogConfirm" :loading="generatingScript || extractingCharacters || !!generatingAvatarId">
            {{ getConfirmText() }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Picture, Mic, VideoPlay, ArrowLeft, User, MagicStick, Cpu, MoreFilled } from '@element-plus/icons-vue'
import { useTaskPoller } from '@/composables/useTaskPoller'
import movieService from '@/services/movie'
import api from '@/services/api'
import { apiKeysService } from '@/services/apiKeys'

const route = useRoute()
const router = useRouter()
const chapterId = route.params.id

const chapter = ref(null)
const script = ref(null)
const characters = ref([])
const apiKeys = ref([])
const loading = ref(false)
const generatingScript = ref(false)
const extractingCharacters = ref(false)
const generatingKeyframes = ref(false)
const batchProducing = ref(false)
const generatingAvatarId = ref(null)
const selectedCharacter = ref(null)
const showCastManager = ref(true) // Default open
const showGenerateDialog = ref(false)
const dialogMode = ref('script') // 'script' | 'character' | 'avatar' | 'keyframes' | 'produce-single' | 'produce-batch' | 'regen-keyframe' | 'regen-video'
const modelOptions = ref([])
const loadingModels = ref(false)
const selectedShotId = ref(null)

// 视图切换控制
const showVideo = ref({}) // {shotId: boolean}
const activePollers = ref({}) // {shotId: timerId}

const genConfig = ref({
  api_key_id: '',
  model: '',
  style: 'cinematic',
  prompt: ''
})

const STYLE_PROMPTS = {
  cinematic: "Cinematic lighting, movie still, 8k, photorealistic, dramatic, highly detailed face",
  anime: "Anime style, vibrant colors, detailed line art, digital illustration, clean lines",
  cyberpunk: "Cyberpunk style, neon lights, high tech low life, futuristic atmosphere, blue and pink lighting",
  oil_painting: "Oil painting style, brush strokes, classical art, rich colors, textured canvas"
}

const { 
  startPolling, 
  isPolling 
} = useTaskPoller()

// 监听风格变化，自动更新提示词（仅当用户还未手动深度编辑时，此处简化为始终更新）
watch(() => genConfig.value.style, (newStyle) => {
  if (dialogMode.value === 'avatar' && selectedCharacter.value) {
    const stylePrompt = STYLE_PROMPTS[newStyle] || STYLE_PROMPTS.cinematic
    genConfig.value.prompt = `${stylePrompt}, ${selectedCharacter.value.visual_traits}`
  }
})

// 获取模型列表
const fetchModels = async () => {
  const newKeyId = genConfig.value.api_key_id
  if (!newKeyId) {
    modelOptions.value = []
    return
  }
  
  loadingModels.value = true
  try {
    // 根据模式确定模型类型
    const modelType = (dialogMode.value === 'avatar' || dialogMode.value === 'keyframes') ? 'image' : 'text'
    console.log(`Loading models for ${dialogMode.value} (type: ${modelType})`)
    
    const models = await apiKeysService.getAPIKeyModels(newKeyId, modelType)
    modelOptions.value = models || []
    
    // 如果当前模型不在列表中，选择第一个可用的
    if (modelOptions.value.length > 0 && !modelOptions.value.includes(genConfig.value.model)) {
      genConfig.value.model = modelOptions.value[0]
    } else if (modelOptions.value.length === 0) {
      genConfig.value.model = ''
    }
  } catch (err) {
    console.error('Failed to load models', err)
    modelOptions.value = []
  } finally {
    loadingModels.value = false
  }
}

// 计算角色是否全部就绪 (至少生成了头像)
const allCharactersReady = computed(() => {
  if (characters.value.length === 0) return false
  return characters.value.every(c => !!c.avatar_url)
})

// 检查某个分镜是否可以生产视频
const canProduceShot = (shot) => {
  if (!shot.first_frame_url) return false
  
  // 检查分镜中提到的角色是否有形象
  for (const char of characters.value) {
    if (shot.visual_description.includes(char.name) && !char.avatar_url) {
      return false
    }
  }
  return true
}

// 监听 API Key 变化
watch(() => genConfig.value.api_key_id, fetchModels)

// 监听对话框模式变化，动态切换模型列表类型
watch(() => dialogMode.value, fetchModels)

const loadData = async () => {
  loading.value = true
  try {
    const chapterData = await api.get(`/chapters/${chapterId}`)
    chapter.value = chapterData
    
    const scriptData = await movieService.getScript(chapterId).catch(() => null)
    script.value = scriptData

    const keys = await apiKeysService.getAPIKeys()
    apiKeys.value = keys.api_keys || []
    if (apiKeys.value.length > 0) genConfig.value.api_key_id = apiKeys.value[0].id

    if (chapter.value?.project_id) {
       characters.value = await movieService.getCharacters(chapter.value.project_id)
    }
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

const handleGenerateScript = () => {
  dialogMode.value = 'script'
  showGenerateDialog.value = true
}

const handleExtractCharacters = () => {
  if (!script.value) return
  dialogMode.value = 'character'
  showGenerateDialog.value = true
}

const handleDialogConfirm = () => {
  if (dialogMode.value === 'script') {
    confirmGenerate()
  } else if (dialogMode.value === 'character') {
    confirmExtract()
  } else if (dialogMode.value === 'keyframes') {
    confirmKeyframes()
  } else if (dialogMode.value === 'produce-single') {
    confirmProduceSingle()
  } else if (dialogMode.value === 'produce-batch') {
    confirmProduceBatch()
  } else if (dialogMode.value === 'regen-keyframe') {
    confirmRegenKeyframe()
  } else if (dialogMode.value === 'regen-video') {
    confirmRegenVideo()
  } else {
    confirmAvatar()
  }
}

const confirmRegenKeyframe = async () => {
    if (!genConfig.value.api_key_id) {
        ElMessage.warning('请选择 API Key')
        return
    }
    const shotId = selectedShotId.value
    if (!shotId) return

    showGenerateDialog.value = false
    try {
        await movieService.regenerateKeyframe(shotId, { 
            api_key_id: genConfig.value.api_key_id,
            model: genConfig.value.model
        })
        ElMessage.success('首帧重制任务已提交')
        loadData() // 刷新列表以显示 processing 状态
    } catch (err) {
        ElMessage.error('重制失败')
    }
}

const confirmRegenVideo = async () => {
    if (!genConfig.value.api_key_id) {
        ElMessage.warning('请选择 API Key')
        return
    }
    const shotId = selectedShotId.value
    if (!shotId) return

    showGenerateDialog.value = false
    try {
        await movieService.regenerateVideo(shotId, { 
            api_key_id: genConfig.value.api_key_id,
            model: genConfig.value.model
        })
        ElMessage.success('视频重制任务已提交')
        pollShotVideo(shotId)
    } catch (err) {
        ElMessage.error('重制失败')
    }
}

const confirmProduceSingle = async () => {
    if (!genConfig.value.api_key_id) {
        ElMessage.warning('请选择 API Key')
        return
    }
    const shotId = selectedShotId.value
    if (!shotId) return

    showGenerateDialog.value = false
    try {
        await movieService.produceShot(shotId, { 
            api_key_id: genConfig.value.api_key_id 
        })
        ElMessage.success('视频生产任务已提交')
        pollShotVideo(shotId)
    } catch (err) {
        ElMessage.error('视频生产失败')
    }
}

const confirmProduceBatch = async () => {
    if (!genConfig.value.api_key_id) {
        ElMessage.warning('请选择 API Key')
        return
    }
    showGenerateDialog.value = false
    try {
        batchProducing.value = true
        const response = await movieService.batchProduceVideos(script.value.id, {
            api_key_id: genConfig.value.api_key_id,
            model: 'veo3.1-fast'
        })
        ElMessage.success(response.message || '批量视频生产任务已启动')
        await loadData()
    } catch (err) {
        ElMessage.error('启动批量生产失败')
    } finally {
        batchProducing.value = false
    }
}

const getDialogTitle = () => {
  if (dialogMode.value === 'script') return '剧本适配配置'
  if (dialogMode.value === 'character') return '角色提取配置'
  if (dialogMode.value === 'keyframes') return '首帧批量生成'
  if (dialogMode.value === 'produce-single') return '生成分镜视频'
  if (dialogMode.value === 'produce-batch') return '批量生成视频'
  if (dialogMode.value === 'regen-keyframe') return '重新生成首帧'
  if (dialogMode.value === 'regen-video') return '重新生成视频'
  return '角色形象生成'
}

const getConfirmText = () => {
  if (dialogMode.value === 'script') return '开始生成'
  if (dialogMode.value === 'character') return '开始提取'
  if (dialogMode.value === 'keyframes') return '开始批量绘图'
  if (dialogMode.value.startsWith('produce') || dialogMode.value.startsWith('regen')) return '开始制作'
  return '开始绘图'
}

const confirmGenerate = async () => {
  if (!genConfig.value.api_key_id) {
    ElMessage.warning('请选择 API Key')
    return
  }

  showGenerateDialog.value = false
  generatingScript.value = true
  
  try {
    const response = await movieService.generateScript(chapterId, genConfig.value)
    
    if (response && response.task_id) {
       ElMessage.success('剧本生成任务已提交，正在后台处理...')
       
       startPolling(response.task_id, async () => {
           ElMessage.success('剧本生成完成！')
           await loadData()
           generatingScript.value = false
       }, (error) => {
           ElMessage.error(`剧本生成失败: ${error.message || '未知错误'}`)
           generatingScript.value = false
       })
    } else {
       // Fallback for immediate response
       await loadData()
       generatingScript.value = false
       ElMessage.success('操作完成')
    }
  } catch (err) {
    console.error(err)
    ElMessage.error('任务提交失败')
    generatingScript.value = false
  }
}

const confirmExtract = async () => {
  if (!genConfig.value.api_key_id) {
    ElMessage.warning('请选择 API Key')
    return
  }

  showGenerateDialog.value = false
  extractingCharacters.value = true
  
  try {
    const response = await movieService.extractCharacters(script.value.id, { 
        api_key_id: genConfig.value.api_key_id,
        model: genConfig.value.model
    })
    
    if (response && response.task_id) {
       ElMessage.success('角色同步任务已提交，正在后台分析...')
       
       startPolling(response.task_id, async (result) => {
           const count = result?.character_count || '若干'
           ElMessage.success(`角色提取完成，共找到 ${count} 名角色`)
           if (chapter.value?.project_id) {
               characters.value = await movieService.getCharacters(chapter.value.project_id)
           }
           extractingCharacters.value = false
       }, (error) => {
           ElMessage.error(`角色提取失败: ${error.message}`)
           extractingCharacters.value = false
       })
    } else {
        ElMessage.success('角色提取完成')
        extractingCharacters.value = false
        loadData()
    }
  } catch (err) {
    console.error(err)
    ElMessage.error('无法启动角色提取')
    extractingCharacters.value = false
  }
}

const handleGenerateAvatar = (char) => {
  selectedCharacter.value = char
  dialogMode.value = 'avatar'
  // 预填提示词
  const stylePrompt = STYLE_PROMPTS[genConfig.value.style] || STYLE_PROMPTS.cinematic
  genConfig.value.prompt = `${stylePrompt}, ${char.visual_traits}`
  showGenerateDialog.value = true
}

const confirmAvatar = async () => {
  if (!genConfig.value.api_key_id) {
    ElMessage.warning('请选择 API Key')
    return
  }

  const char = selectedCharacter.value
  showGenerateDialog.value = false
  generatingAvatarId.value = char.id
  
  try {
    const response = await movieService.generateCharacterAvatar(char.id, { 
        api_key_id: genConfig.value.api_key_id,
        model: genConfig.value.model,
        style: genConfig.value.style,
        prompt: genConfig.value.prompt
    })
    
    if (response && response.task_id) {
       ElMessage.success('人物绘图任务已提交...')
       
       startPolling(response.task_id, async (result) => {
           ElMessage.success('人物形象生成成功')
           if (chapter.value?.project_id) {
               characters.value = await movieService.getCharacters(chapter.value.project_id)
           }
           generatingAvatarId.value = null
       }, (error) => {
           ElMessage.error(`生成失败: ${error.message}`)
           generatingAvatarId.value = null
       })
    }
  } catch (err) {
    console.error(err)
    ElMessage.error('无法启动形象生成')
    generatingAvatarId.value = null
  }
}

const handleGenerateKeyframes = () => {
  if (!script.value) return
  dialogMode.value = 'keyframes'
  showGenerateDialog.value = true
}

const confirmKeyframes = async () => {
  if (!genConfig.value.api_key_id) {
    ElMessage.warning('请选择 API Key')
    return
  }

  showGenerateDialog.value = false
  generatingKeyframes.value = true
  
  try {
    const response = await movieService.generateKeyframes(script.value.id, { 
        api_key_id: genConfig.value.api_key_id,
        model: genConfig.value.model
    })
    
    if (response && response.task_id) {
       ElMessage.success('批量生成首帧任务已提交...')
       
       startPolling(response.task_id, async (result) => {
           if (result.failed > 0) {
               ElMessage.warning(`绘图部分完成: 成功 ${result.success}, 失败 ${result.failed}。${result.message || ''}`)
           } else {
               ElMessage.success(`批量绘图已全部完成: 共 ${result.success} 个分镜`)
           }
           loadData()
           generatingKeyframes.value = false
       }, (error) => {
           ElMessage.error(`任务失败: ${error.message}`)
           generatingKeyframes.value = false
       })
    }
  } catch (err) {
    console.error(err)
    ElMessage.error('无法启动批量绘图')
    generatingKeyframes.value = false
  }
}

const handleProduceShot = async (shot) => {
  selectedShotId.value = shot.id
  if (!genConfig.value.api_key_id) {
    dialogMode.value = 'produce-single'
    showGenerateDialog.value = true
    return
  }
  confirmProduceSingle()
}

// 批量生产视频
const handleBatchProduceVideos = async () => {
  if (!genConfig.value.api_key_id) {
    dialogMode.value = 'produce-batch'
    showGenerateDialog.value = true
    return
  }
  confirmProduceBatch()
}

// 视图切换
const toggleShotView = (shotId, visible) => {
  showVideo.value[shotId] = visible
}

// 下拉菜单处理
const handleShotCommand = async (command, shot) => {
  if (command === 'regenerate-keyframe') {
    handleRegenerateKeyframe(shot)
  } else if (command === 'regenerate-video') {
    handleRegenerateVideo(shot)
  } else if (command === 'switch-video') {
    showVideo.value[shot.id] = true
  }
}

const handleRegenerateKeyframe = (shot) => {
  selectedShotId.value = shot.id
  dialogMode.value = 'regen-keyframe'
  showGenerateDialog.value = true
}

const handleRegenerateVideo = (shot) => {
  selectedShotId.value = shot.id
  dialogMode.value = 'regen-video'
  showGenerateDialog.value = true
}

// --- 轮询逻辑 ---
const pollShotVideo = async (shotId) => {
  if (activePollers.value[shotId]) return

  const timer = setInterval(async () => {
    try {
      const { status } = await movieService.getShotStatus(shotId, { 
        api_key_id: genConfig.value.api_key_id 
      })
      
      if (status === 'completed' || status === 'failed') {
        clearInterval(timer)
        delete activePollers.value[shotId]
        if (status === 'completed') {
          ElMessage.success('分镜视频生成完成')
          showVideo.value[shotId] = true
        } else {
          ElMessage.error('分镜视频生成失败')
        }
        loadData()
      }
    } catch (err) {
      clearInterval(timer)
      delete activePollers.value[shotId]
    }
  }, 10000)

  activePollers.value[shotId] = timer
}

watch(() => script.value, (newScript) => {
  if (!newScript) return
  newScript.scenes.forEach(scene => {
    scene.shots.forEach(shot => {
      if (shot.status === 'processing' && !activePollers.value[shot.id]) {
        pollShotVideo(shot.id)
      }
      if (shot.video_url && showVideo.value[shot.id] === undefined) {
         showVideo.value[shot.id] = true
      }
    })
  })
}, { deep: true })

onUnmounted(() => {
  Object.values(activePollers.value).forEach(timer => clearInterval(timer))
})

const goBack = () => router.back()

onMounted(loadData)
</script>

<style scoped>
.movie-studio {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.studio-header {
  height: 60px;
  background: #fff;
  border-bottom: 1px solid #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
}

.chapter-title {
  margin-left: 15px;
  font-weight: 600;
  font-size: 18px;
}

.studio-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.studio-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.scene-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 30px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.05);
}

.scene-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 10px;
  margin-bottom: 15px;
}

.scene-header h3 {
  margin: 0;
  color: #303133;
}

.scene-meta {
  color: #909399;
  font-size: 14px;
}

.scene-desc {
  color: #606266;
  margin-bottom: 20px;
}

.shots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.shot-visual {
  height: 170px;
  position: relative;
  border-radius: 4px;
  overflow: hidden;
  background: #000;
}

.shot-preview {
  width: 100%;
  height: 100%;
  opacity: 0.8;
}

.image-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #606266;
  background: #f2f6fc;
}

.shot-actions {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: none;
}

.shot-visual:hover .shot-actions {
  display: block;
}

.shot-info {
  padding: 12px 0;
}

.shot-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.shot-index {
  font-size: 12px;
  color: #409eff;
  font-weight: bold;
}

.shot-desc {
  font-size: 14px;
  line-height: 1.5;
  color: #2c3e50;
  margin-bottom: 8px;
}

.shot-dialogue {
  background: #f0f9eb;
  padding: 8px;
  border-radius: 4px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  color: #67c23a;
  font-size: 13px;
}

.dialogue-text {
  font-style: italic;
}

.studio-sidebar {
  width: 320px;
  background: #fff;
  border-left: 1px solid #dcdfe6;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.sidebar-header {
  padding: 15px 20px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

/* Cast List Styles in Sidebar */
.cast-list {
  padding: 15px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.char-card {
  border: 1px solid #ebeef5;
}

.char-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.char-avatar {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  cursor: pointer;
  transition: transform 0.2s;
  overflow: hidden;
  flex-shrink: 0;
}

.char-avatar:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.char-name {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.video-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: #000;
}

.shot-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.view-image-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  opacity: 0.6;
  transition: opacity 0.3s;
  z-index: 10;
}

.view-image-btn:hover {
  opacity: 1;
}

.shot-more-actions {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 20;
}

.shot-prompt-tag {
  cursor: help;
  margin-top: 8px;
}

.char-traits {
  display: flex;
  gap: 6px;
}

/* Transitions */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease;
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateX(20px);
  opacity: 0;
  width: 0;
}
</style>
