<template>
  <div class="scene-panel">
    <div class="panel-header">
      <h3>场景列表</h3>
      <div class="actions">
        <el-button 
          type="primary"
          :loading="extracting"
          :disabled="!canExtract"
          @click="handleExtractClick"
        >
          提取场景
        </el-button>
      </div>
    </div>

    <div class="scene-list">
      <el-empty v-if="scenes.length === 0" description="暂无场景，请先提取场景" />
      
      <el-collapse v-else v-model="activeScenes">
        <el-collapse-item 
          v-for="scene in scenes" 
          :key="scene.id"
          :name="scene.id"
        >
          <template #title>
            <div class="scene-title">
              <span class="scene-number">场景 {{ scene.order_index }}</span>
              <el-tag 
                v-for="char in scene.characters" 
                :key="char"
                size="small"
                type="info"
                style="margin-left: 8px"
              >
                {{ char }}
              </el-tag>
            </div>
          </template>
          
          <div class="scene-content">
            <p>{{ scene.scene }}</p>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- API Key选择对话框 -->
    <el-dialog
      v-model="showDialog"
      title="提取场景"
      width="500px"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="API Key">
          <el-select v-model="formData.apiKeyId" placeholder="请选择API Key" style="width: 100%">
            <el-option
              v-for="key in apiKeys"
              :key="key.id"
              :label="`${key.name} (${key.provider})`"
              :value="key.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="模型">
          <el-select 
            v-model="formData.model" 
            placeholder="选择模型" 
            style="width: 100%"
            :loading="loadingModels"
            filterable
            allow-create
            default-first-option
          >
            <el-option
              v-for="model in modelOptions"
              :key="model"
              :label="model"
              :value="model"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleDialogConfirm" :disabled="!formData.apiKeyId || !formData.model">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '@/services/api'

const props = defineProps({
  scenes: {
    type: Array,
    default: () => []
  },
  extracting: {
    type: Boolean,
    default: false
  },
  canExtract: {
    type: Boolean,
    default: true
  },
  apiKeys: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['extract-scenes'])

const activeScenes = ref([])
const showDialog = ref(false)
const formData = ref({
  apiKeyId: '',
  model: ''
})
const modelOptions = ref([])
const loadingModels = ref(false)

// 监听API Key变化，自动加载模型列表 - 完全照搬BatchGenerateImagesDialog
watch(() => formData.value.apiKeyId, async (newKeyId) => {
  if (!newKeyId) {
    modelOptions.value = []
    formData.value.model = ''
    return
  }
  
  loadingModels.value = true
  try {
    const models = await api.get(`/api-keys/${newKeyId}/models?type=text`)
    modelOptions.value = models || []
    if (modelOptions.value.length > 0) {
      formData.value.model = modelOptions.value[0]
    } else {
      formData.value.model = ''
    }
  } catch (error) {
    console.error('获取模型列表失败', error)
    ElMessage.warning('获取模型列表失败')
    modelOptions.value = []
    formData.value.model = ''
  } finally {
    loadingModels.value = false
  }
})

const handleExtractClick = () => {
  // 检查是否已有场景数据
  const hasScenes = props.scenes && props.scenes.length > 0
  
  if (hasScenes) {
    // 显示警告对话框
    ElMessageBox.confirm(
      '重新提取场景将删除所有现有场景及其关联的分镜、关键帧数据。此操作不可撤销！',
      '危险操作警告',
      {
        confirmButtonText: '确认提取',
        cancelButtonText: '取消',
        type: 'warning',
        dangerouslyUseHTMLString: true
      }
    ).then(() => {
      // 用户确认后打开对话框
      openDialog()
    }).catch(() => {
      // 用户取消
    })
  } else {
    // 没有数据，直接打开对话框
    openDialog()
  }
}

const openDialog = () => {
  formData.value = {
    apiKeyId: props.apiKeys[0]?.id || '',
    model: ''
  }
  showDialog.value = true
}

const handleDialogConfirm = () => {
  if (!formData.value.apiKeyId || !formData.value.model) {
    return
  }
  emit('extract-scenes', formData.value.apiKeyId, formData.value.model)
  showDialog.value = false
}
</script>

<style scoped>
.scene-panel {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #eee;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.scene-title {
  display: flex;
  align-items: center;
  flex: 1;
}

.scene-number {
  font-weight: 600;
  color: #409eff;
}

.scene-content {
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
  line-height: 1.6;
}

.scene-content p {
  margin: 0;
  white-space: pre-wrap;
}
</style>
