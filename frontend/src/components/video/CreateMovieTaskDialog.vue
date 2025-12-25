<template>
  <el-dialog
    title="新建电影合成任务"
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event)"
    width="600px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      v-loading="loading"
    >
      <!-- 选择章节 -->
      <el-form-item label="选择章节" prop="chapter_id">
        <el-select
          v-model="form.chapter_id"
          placeholder="请选择已完成电影制作的章节"
          filterable
          remote
          :remote-method="searchChapters"
          :loading="chapterLoading"
          style="width: 100%"
        >
          <el-option
            v-for="item in chapters"
            :key="item.id"
            :label="item.title"
            :value="item.id"
          >
            <span style="float: left">{{ item.title }}</span>
            <span style="float: right; color: var(--el-text-color-secondary); font-size: 13px">
              {{ item.project_title }}
            </span>
          </el-option>
        </el-select>
        <div class="form-tip">
          仅显示状态为"素材已准备"且项目类型为"AI电影"的章节
        </div>
      </el-form-item>

      <el-divider content-position="left">生成设置</el-divider>

      <el-form-item label="分辨率" prop="gen_setting.resolution">
        <el-select v-model="form.gen_setting.resolution" style="width: 100%">
          <el-option label="竖屏 9:16 (1080x1920)" value="1080x1920" />
          <el-option label="横屏 16:9 (1920x1080)" value="1920x1080" />
          <el-option label="方形 1:1 (1080x1080)" value="1080x1080" />
        </el-select>
      </el-form-item>

      <el-form-item label="帧率" prop="gen_setting.fps">
        <el-radio-group v-model="form.gen_setting.fps">
          <el-radio-button :label="24">24 FPS</el-radio-button>
          <el-radio-button :label="30">30 FPS</el-radio-button>
          <el-radio-button :label="60">60 FPS</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-collapse v-model="activeCollapse">
        <el-collapse-item title="高级设置" name="advanced">
          <el-divider content-position="left">背景音乐</el-divider>
          <el-form-item label="BGM选择">
            <el-select 
              v-model="form.bgm_id" 
              placeholder="选择背景音乐（可选）"
              clearable
              filterable
              style="width: 100%"
            >
              <el-option
                v-for="bgm in bgmList"
                :key="bgm.id"
                :label="`${bgm.name} (${formatDuration(bgm.duration)})`"
                :value="bgm.id"
              />
            </el-select>
            <span class="form-tip">为视频添加背景音乐，将与原音频混合</span>
          </el-form-item>

          <el-form-item label="BGM音量" v-if="form.bgm_id">
            <el-slider 
              v-model="bgmVolumeDisplay" 
              :min="0" 
              :max="50" 
              :marks="{ 0: '0%', 15: '15%', 30: '30%', 50: '50%' }"
              :format-tooltip="val => `${val}%`"
              style="margin: 0 12px"
            />
            <span class="form-tip">BGM音量占比，默认15%不会盖过原音</span>
          </el-form-item>
        </el-collapse-item>
      </el-collapse>

    </el-form>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="$emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="submitting">
          开始合成
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch, computed } from 'vue'
import { useVideoTasks } from '@/composables/useVideoTasks'
import { chaptersService } from '@/services/chapters'
import bgmService from '@/services/bgm'
import { ElMessage } from 'element-plus'

const props = defineProps({
  modelValue: Boolean,
  chapterId: String  // 可选的预填充章节ID
})

const emit = defineEmits(['update:modelValue', 'success'])

const { createTask } = useVideoTasks()

// 状态
const formRef = ref(null)
const loading = ref(false)
const submitting = ref(false)
const chapterLoading = ref(false)
const chapters = ref([])
const bgmList = ref([])
const activeCollapse = ref([])
const bgmVolumeDisplay = ref(15) // 对应 0.15

const form = reactive({
  chapter_id: '',
  bgm_id: '',
  gen_setting: {
    resolution: '1920x1080',  // 电影默认横屏
    fps: 30,
    video_codec: 'libx264',
    audio_codec: 'aac',
    audio_bitrate: '192k',
    bgm_volume: 0.15,
  }
})

const rules = computed(() => ({
  chapter_id: [{ required: true, message: '请选择章节', trigger: 'change' }],
  'gen_setting.resolution': [{ required: true, message: '请选择分辨率', trigger: 'change' }],
  'gen_setting.fps': [{ required: true, message: '请选择帧率', trigger: 'change' }]
}))

// 监听器
watch(() => props.modelValue, (val) => {
  if (val) {
    loadData()
    // 如果有预填充的章节ID
    if (props.chapterId) {
      form.chapter_id = props.chapterId
    }
  } else {
    resetForm()
  }
})

watch(bgmVolumeDisplay, (val) => {
  form.gen_setting.bgm_volume = val / 100
})

// 方法
const loadData = async () => {
  loading.value = true
  try {
    // 加载BGM列表
    const bgmRes = await bgmService.getBGMs({ size: 100 })
    bgmList.value = bgmRes.bgms || []
    
    // 初始加载章节（materials_prepared状态 + ai_movie类型）
    await searchChapters('')
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const searchChapters = async (query) => {
  chapterLoading.value = true
  try {
    const res = await chaptersService.getChapters(null, {
      search: query,
      chapter_status: 'materials_prepared', // 只显示素材准备好的章节
      project_type: 'ai_movie', // 只显示AI电影项目的章节
      size: 50
    })
    chapters.value = res.chapters || []
  } catch (error) {
    console.error('搜索章节失败:', error)
  } finally {
    chapterLoading.value = false
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitting.value = true
      try {
        await createTask({
          task_type: 'movie_composition',  // 固定为电影合成类型
          chapter_id: form.chapter_id,
          bgm_id: form.bgm_id || null,
          gen_setting: form.gen_setting
        })
        emit('success')
        emit('update:modelValue', false)
      } catch (error) {
        // 错误已在composable中处理
      } finally {
        submitting.value = false
      }
    }
  })
}

const formatDuration = (seconds) => {
  if (!seconds) return '-'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
  form.chapter_id = ''
  form.bgm_id = ''
  form.gen_setting = {
    resolution: '1920x1080',
    fps: 30,
    video_codec: 'libx264',
    audio_codec: 'aac',
    audio_bitrate: '192k',
    bgm_volume: 0.15,
  }
  bgmVolumeDisplay.value = 15
}
</script>

<style scoped>
.form-tip {
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-top: 4px;
}
</style>
