<template>
  <div class="project-creator">
    <!-- 创建方式选择 -->
    <el-tabs v-model="activeTab" class="creator-tabs">
      <!-- 文件上传方式 -->
      <el-tab-pane label="上传文件" name="file">
        <!-- 文件上传区域 -->
        <div v-if="!selectedFile" class="upload-section">
          <el-upload
            ref="uploadRef"
            class="upload-dragger"
            drag
            :auto-upload="false"
            :show-file-list="false"
            :accept="acceptedTypes"
            :limit="1"
            :on-change="handleFileChange"
            :before-upload="beforeUpload"
          >
            <div class="upload-content">
              <el-icon class="upload-icon">
                <UploadFilled />
              </el-icon>
              <div class="upload-text">
                <h3>拖拽文件到此处上传</h3>
                <p>或点击选择文件</p>
                <p class="upload-hint">支持 TXT、MD、DOCX、EPUB 格式，最大 100MB</p>
              </div>
            </div>
          </el-upload>
        </div>

        <!-- 上传进度 -->
        <div v-else-if="uploading" class="upload-progress">
          <div class="progress-content">
            <el-icon class="progress-icon">
              <Loading />
            </el-icon>
            <div class="progress-text">
              <h3>正在上传文件...</h3>
              <p>{{ selectedFile.name }}</p>
              <div class="progress-bar">
                <el-progress :percentage="0" status="active" />
              </div>
            </div>
          </div>
        </div>

        <!-- 文件信息表单 -->
        <div v-else class="form-section">
          <!-- 文件预览卡片 -->
          <div class="file-preview">
            <div class="file-card">
              <el-icon class="file-icon">
                <Document />
              </el-icon>
              <div class="file-info">
                <div class="file-name">{{ selectedFile.name }}</div>
                <div class="file-meta">
                  {{ formatFileSize(selectedFile.size) }} · {{ getFileTypeText(selectedFile.name) }}
                </div>
              </div>
              <el-button
                type="text"
                :icon="Delete"
                @click="removeFile"
                class="remove-btn"
              />
            </div>
          </div>

          <!-- 项目类型选择 -->
          <div class="type-selection">
            <div class="selection-label">项目类型</div>
            <div class="type-cards">
              <div
                class="type-card"
                :class="{ active: formData.type === 'picture_narrative' }"
                @click="formData.type = 'picture_narrative'"
              >
                <div class="type-img">
                  <el-icon :size="48"><VideoCamera /></el-icon>
                </div>
                <div class="type-info">
                  <div class="type-title">解说视频</div>
                  <div class="type-desc">图文解说，快速出片</div>
                </div>
                <div class="active-badge">
                  <el-icon><Check /></el-icon>
                </div>
              </div>
              <div
                class="type-card"
                :class="{ active: formData.type === 'ai_movie' }"
                @click="formData.type = 'ai_movie'"
              >
                <div class="type-img">
                  <el-icon :size="48"><Collection /></el-icon>
                </div>
                <div class="type-info">
                  <div class="type-title">AI 电影</div>
                  <div class="type-desc">影视级别，角色一致</div>
                </div>
                <div class="active-badge">
                  <el-icon><Check /></el-icon>
                </div>
              </div>
            </div>
          </div>

          <!-- 项目信息表单 -->
          <el-form
            ref="formRef"
            :model="formData"
            :rules="formRules"
            label-position="top"
            @submit.prevent="handleSubmit"
          >
            <el-form-item label="项目标题" prop="title">
              <el-input
                v-model="formData.title"
                placeholder="请输入项目标题"
                maxlength="200"
                show-word-limit
                clearable
              />
            </el-form-item>

            <el-form-item label="项目描述" prop="description">
              <el-input
                v-model="formData.description"
                type="textarea"
                :rows="3"
                placeholder="请输入项目描述（可选）"
                maxlength="1000"
                show-word-limit
              />
            </el-form-item>

            <el-form-item>
              <el-checkbox v-model="formData.auto_process">
                自动处理文件（上传后立即开始文件内容分析）
              </el-checkbox>
            </el-form-item>

            <div class="form-actions">
              <el-button @click="handleCancel">取消</el-button>
              <el-button
                type="primary"
                native-type="submit"
                :loading="submitting"
              >
                创建项目
              </el-button>
            </div>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- 文本导入方式 -->
      <el-tab-pane label="导入文本" name="text">
        <!-- 项目类型选择 -->
        <div class="type-selection" style="margin-bottom: 20px;">
          <div class="selection-label">项目类型</div>
          <div class="type-cards">
            <div
              class="type-card"
              :class="{ active: textFormData.type === 'picture_narrative' }"
              @click="textFormData.type = 'picture_narrative'"
            >
              <div class="type-img">
                <el-icon :size="48"><VideoCamera /></el-icon>
              </div>
              <div class="type-info">
                <div class="type-title">解说视频</div>
                <div class="type-desc">图文解说，快速出片</div>
              </div>
              <div class="active-badge">
                <el-icon><Check /></el-icon>
              </div>
            </div>
            <div
              class="type-card"
              :class="{ active: textFormData.type === 'ai_movie' }"
              @click="textFormData.type = 'ai_movie'"
            >
              <div class="type-img">
                <el-icon :size="48"><Collection /></el-icon>
              </div>
              <div class="type-info">
                <div class="type-title">AI 电影</div>
                <div class="type-desc">影视级别，角色一致</div>
              </div>
              <div class="active-badge">
                <el-icon><Check /></el-icon>
              </div>
            </div>
          </div>
        </div>

        <el-form
          ref="textFormRef"
          :model="textFormData"
          :rules="textFormRules"
          label-position="top"
          @submit.prevent="handleTextSubmit"
        >
          <el-form-item label="项目标题" prop="title">
            <el-input
              v-model="textFormData.title"
              placeholder="请输入项目标题"
              maxlength="200"
              show-word-limit
              clearable
            />
          </el-form-item>

          <el-form-item label="项目描述" prop="description">
            <el-input
              v-model="textFormData.description"
              type="textarea"
              :rows="2"
              placeholder="可选，描述项目内容"
              maxlength="1000"
              show-word-limit
            />
          </el-form-item>

          <el-form-item label="文本内容" prop="content">
            <el-input
              v-model="textFormData.content"
              type="textarea"
              :rows="15"
              placeholder="请粘贴或输入文本内容（至少100字符）..."
              show-word-limit
              :maxlength="500000"
            />
          </el-form-item>

          <div class="word-count">
            <el-icon><Document /></el-icon>
            字数统计: {{ wordCount }} 字
          </div>

          <div class="form-actions">
            <el-button @click="handleCancel">取消</el-button>
            <el-button
              type="primary"
              native-type="submit"
              :loading="submitting"
            >
              创建项目
            </el-button>
          </div>
        </el-form>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Document, Delete, Loading, Check, VideoCamera, Collection } from '@element-plus/icons-vue'
import { fileService } from '@/services/upload'
import { projectsService } from '@/services/projects'

// Props定义
const props = defineProps({
  // 表单提交loading状态
  loading: {
    type: Boolean,
    default: false
  }
})

// Emits定义
const emit = defineEmits([
  'submit',
  'cancel',
  'error'
])

// 响应式数据
const uploadRef = ref()
const formRef = ref()
const textFormRef = ref()
const uploading = ref(false)
const submitting = ref(false)
const selectedFile = ref(null)
const uploadedFileInfo = ref(null)
const activeTab = ref('file')

// 文件上传表单数据
const formData = reactive({
  title: '',
  description: '',
  type: 'picture_narrative',
  auto_process: true
})

// 文本导入表单数据
const textFormData = reactive({
  title: '',
  description: '',
  content: '',
  type: 'picture_narrative'
})

// 文件上传表单验证规则
const formRules = {
  title: [
    { required: true, message: '请输入项目标题', trigger: 'blur' },
    { min: 1, max: 200, message: '标题长度应在1-200个字符之间', trigger: 'blur' }
  ],
  description: [
    { max: 1000, message: '描述长度不能超过1000个字符', trigger: 'blur' }
  ]
}

// 文本导入表单验证规则
const textFormRules = {
  title: [
    { required: true, message: '请输入项目标题', trigger: 'blur' },
    { min: 1, max: 200, message: '标题长度应在1-200个字符之间', trigger: 'blur' }
  ],
  description: [
    { max: 1000, message: '描述长度不能超过1000个字符', trigger: 'blur' }
  ],
  content: [
    { required: true, message: '请输入文本内容', trigger: 'blur' },
    { min: 100, message: '文本内容至少需要100字符', trigger: 'blur' },
    { max: 500000, message: '文本内容不能超过500,000字符', trigger: 'blur' }
  ]
}

// 支持的文件类型
const acceptedTypes = '.txt,.md,.docx,.epub'

// 计算属性
const getFileTypeText = (filename) => {
  const ext = filename.split('.').pop().toLowerCase()
  const typeMap = {
    'txt': 'TXT文档',
    'md': 'Markdown文档',
    'docx': 'Word文档',
    'epub': 'EPUB电子书'
  }
  return typeMap[ext] || '未知文件类型'
}

const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 字数统计
const wordCount = computed(() => {
  if (!textFormData.content) return 0
  // 移除空白字符后计算长度
  return textFormData.content.replace(/\s/g, '').length
})

// 监听loading状态
const loading = computed(() => props.loading)
watch(loading, (newLoading) => {
  submitting.value = newLoading
})

// 方法
const handleFileChange = async (file) => {
  try {
    selectedFile.value = file.raw
    uploading.value = true

    // 创建FormData并上传文件
    const uploadFormData = new FormData()
    uploadFormData.append('file', file.raw)

    const uploadResult = await fileService.uploadFile(uploadFormData, (percent) => {
      console.log(`上传进度: ${percent}%`)
    })

    if (uploadResult.success) {
      uploadedFileInfo.value = uploadResult.data

      // 自动从文件名提取标题（在上传成功后设置）
      if (file.raw && file.raw.name) {
        // 移除文件扩展名
        let nameWithoutExt = file.raw.name.replace(/\.[^/.]+$/, "")
        // 替换常见的分隔符为空格
        nameWithoutExt = nameWithoutExt.replace(/[-_]/g, " ")
        // 移除多余的空格
        nameWithoutExt = nameWithoutExt.replace(/\s+/g, " ").trim()
        // 设置为表单标题
        formData.title = nameWithoutExt
      }

      ElMessage.success('文件上传成功')
    } else {
      throw new Error(uploadResult.message || '文件上传失败')
    }

  } catch (error) {
    console.error('文件上传失败:', error)
    ElMessage.error('文件上传失败: ' + error.message)
    // 上传失败，重置状态
    selectedFile.value = null
    uploadedFileInfo.value = null
    if (uploadRef.value) {
      uploadRef.value.clearFiles()
    }
  } finally {
    uploading.value = false
  }

  // 清除之前的验证结果
  if (formRef.value) {
    formRef.value.clearValidate()
  }
}

const beforeUpload = (file) => {
  // 验证文件类型
  const allowedTypes = ['txt', 'md', 'docx', 'epub']
  const fileExt = file.name.split('.').pop().toLowerCase()

  if (!allowedTypes.includes(fileExt)) {
    ElMessage.error('不支持的文件类型，请上传 TXT、MD、DOCX 或 EPUB 格式的文件')
    return false
  }

  // 验证文件大小 (100MB)
  const maxSize = 100 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过 100MB')
    return false
  }

  return false // 阻止自动上传
}

const removeFile = async () => {
  try {
    // 清理状态，删除逻辑暂时简化
    selectedFile.value = null
    uploadedFileInfo.value = null
    formData.title = ''
    if (uploadRef.value) {
      uploadRef.value.clearFiles()
    }
    ElMessage.info('文件已移除')
  } catch (error) {
    console.error('移除文件失败:', error)
  }
}

const handleSubmit = async () => {
  try {
    // 验证表单
    const valid = await formRef.value.validate()
    if (!valid) return

    // 检查是否上传了文件
    if (!uploadedFileInfo.value || !uploadedFileInfo.value.storage_key) {
      ElMessage.warning('请先上传文件')
      return
    }

    submitting.value = true

    // 准备项目数据 - 使用文件信息创建项目
    const projectData = {
      title: formData.title.trim(),
      description: formData.description.trim(),
      file_name: uploadedFileInfo.value.original_filename,
      file_size: uploadedFileInfo.value.file_size,
      file_type: uploadedFileInfo.value.file_type,
      file_path: uploadedFileInfo.value.storage_key,
      file_hash: uploadedFileInfo.value.file_info?.file_hash,
      type: formData.type
    }

    // 调用项目API创建项目
    const result = await projectsService.createProject(projectData)

    ElMessage.success('项目创建成功')
    emit('submit', result)

  } catch (error) {
    console.error('项目创建失败:', error)
    ElMessage.error(error.message || '项目创建失败')
    emit('error', error)
  } finally {
    submitting.value = false
  }
}

const handleTextSubmit = async () => {
  try {
    // 验证表单
    const valid = await textFormRef.value.validate()
    if (!valid) return

    submitting.value = true

    // 准备文本数据
    const textData = {
      title: textFormData.title.trim(),
      description: textFormData.description.trim(),
      content: textFormData.content,
      type: textFormData.type
    }

    // 调用文本导入API创建项目
    const result = await projectsService.createProjectFromText(textData)

    ElMessage.success('项目创建成功，正在解析文本内容')
    emit('submit', result)

  } catch (error) {
    console.error('项目创建失败:', error)
    ElMessage.error(error.message || '项目创建失败')
    emit('error', error)
  } finally {
    submitting.value = false
  }
}

const handleCancel = () => {
  emit('cancel')
}

const resetForm = async () => {
  // 重置文件上传表单状态
  selectedFile.value = null
  uploadedFileInfo.value = null
  formData.title = ''
  formData.description = ''
  formData.type = 'picture_narrative'
  formData.auto_process = true

  // 重置文本导入表单状态
  textFormData.title = ''
  textFormData.description = ''
  textFormData.content = ''
  textFormData.type = 'picture_narrative'

  // 重置选项卡
  activeTab.value = 'file'

  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }

  if (formRef.value) {
    formRef.value.clearValidate()
  }

  if (textFormRef.value) {
    textFormRef.value.clearValidate()
  }
}

// 暴露给父组件的方法
defineExpose({
  resetForm,
  validate: () => formRef.value?.validate()
})
</script>

<style scoped>
.project-creator {
  width: 100%;
}

.creator-tabs {
  margin-bottom: var(--space-md);
}

.creator-tabs :deep(.el-tabs__header) {
  margin-bottom: var(--space-lg);
}

.type-selection {
  margin-bottom: var(--space-xl);
}

.selection-label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: var(--space-sm);
}

.type-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-md);
}

.type-card {
  position: relative;
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
  border: 2px solid var(--border-primary);
  border-radius: var(--radius-lg);
  overflow: hidden;
  cursor: pointer;
  transition: all var(--transition-base);
}

.type-card:hover {
  border-color: var(--primary-color);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.type-card.active {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.05);
}

.type-img {
  width: 100%;
  height: 100px;
  overflow: hidden;
  background: var(--bg-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.type-img .el-icon {
  color: var(--primary-color);
}

.type-img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.5s ease;
}

.type-card:hover .type-img img {
  transform: scale(1.05);
}

.type-info {
  padding: var(--space-md);
}

.type-title {
  font-weight: 700;
  color: var(--text-primary);
  font-size: var(--text-base);
  margin-bottom: 2px;
}

.type-desc {
  font-size: var(--text-xs);
  color: var(--text-secondary);
}

.active-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  background: var(--primary-color);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  transform: scale(0);
  transition: transform var(--transition-base);
}

.type-card.active .active-badge {
  transform: scale(1);
}

.word-count {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-md);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  margin-bottom: var(--space-md);
}

.word-count .el-icon {
  color: var(--primary-color);
}

.upload-section,
.upload-progress {
  margin-bottom: var(--space-lg);
}

.upload-dragger {
  width: 100%;
}

.upload-dragger :deep(.el-upload-dragger) {
  width: 100%;
  height: 200px;
  border: 2px dashed var(--border-primary);
  border-radius: var(--radius-xl);
  background: var(--bg-secondary);
  transition: all var(--transition-base);
}

.upload-dragger :deep(.el-upload-dragger:hover) {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.05);
}

.upload-content,
.progress-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: var(--space-xl);
}

.upload-icon,
.progress-icon {
  font-size: 48px;
  color: var(--primary-color);
  margin-bottom: var(--space-md);
  opacity: 0.8;
}

.progress-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.upload-text h3,
.progress-text h3 {
  margin: 0 0 var(--space-sm) 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--text-primary);
}

.upload-text p,
.progress-text p {
  margin: 0 0 var(--space-xs) 0;
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.upload-hint {
  font-size: var(--text-xs) !important;
  color: var(--text-tertiary) !important;
  margin-top: var(--space-sm) !important;
}

.progress-bar {
  width: 100%;
  margin-top: var(--space-md);
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
}

.file-preview {
  margin-bottom: var(--space-md);
}

.file-card {
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-lg);
  background: var(--bg-secondary);
  border: 1px solid var(--border-primary);
  border-radius: var(--radius-lg);
  transition: all var(--transition-base);
}

.file-card:hover {
  border-color: var(--primary-color);
  background: rgba(99, 102, 241, 0.05);
}

.file-icon {
  width: 40px;
  height: 40px;
  color: var(--primary-color);
  background: rgba(99, 102, 241, 0.1);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 2px;
  word-break: break-all;
}

.file-meta {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.remove-btn {
  color: var(--text-secondary);
  transition: color var(--transition-base);
}

.remove-btn:hover {
  color: var(--danger-color);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-md);
  margin-top: var(--space-lg);
  padding-top: var(--space-lg);
  border-top: 1px solid var(--border-primary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .upload-dragger :deep(.el-upload-dragger) {
    height: 160px;
  }

  .upload-content {
    padding: var(--space-md);
  }

  .upload-icon {
    font-size: 36px;
  }

  .upload-text h3 {
    font-size: var(--text-base);
  }

  .file-card {
    padding: var(--space-md);
  }

  .file-info {
    flex: 1;
    min-width: 0;
  }

  .file-name {
    font-size: var(--text-sm);
    word-break: break-all;
  }

  .file-meta {
    font-size: var(--text-xs);
  }
}
</style>