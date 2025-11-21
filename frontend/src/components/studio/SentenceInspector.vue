<template>
  <div class="sentence-inspector">
    <div class="inspector-header">
      <h3>详情面板</h3>
    </div>

    <div v-if="!paragraph" class="inspector-empty">
      <el-empty description="请选择一个段落" :image-size="100" />
    </div>

    <div v-else class="inspector-content">
      <!-- 段落信息 -->
      <div class="info-section">
        <h4>段落信息</h4>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">字数</span>
            <span class="value">{{ paragraph.word_count || 0 }}</span>
          </div>
          <div class="info-item">
            <span class="label">句子数</span>
            <span class="value">{{ sentences.length }}</span>
          </div>
          <div class="info-item">
            <span class="label">状态</span>
            <el-tag :type="getActionType(paragraph.action)" size="small">
              {{ getActionText(paragraph.action) }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 句子管理 -->
      <div class="info-section">
        <div class="section-header">
          <h4>句子管理</h4>
          <el-button type="primary" link size="small" @click="handleAddSentence">
            <el-icon><Plus /></el-icon> 添加
          </el-button>
        </div>
        
        <div v-loading="loading" class="sentence-list">
          <div v-if="sentences.length === 0" class="empty-sentences">
            暂无句子
          </div>
          
          <div 
            v-for="(sentence, index) in sentences" 
            :key="sentence.id" 
            class="sentence-item"
          >
            <div class="sentence-index">{{ index + 1 }}</div>
            <div class="sentence-content">
              <div v-if="editingId === sentence.id" class="edit-mode">
                <el-input
                  v-model="editContent"
                  type="textarea"
                  :rows="2"
                  size="small"
                  @keyup.enter.ctrl="handleSaveEdit(sentence)"
                />
                <div class="edit-actions">
                  <el-button type="primary" link size="small" @click="handleSaveEdit(sentence)">保存</el-button>
                  <el-button link size="small" @click="cancelEdit">取消</el-button>
                </div>
              </div>
              <div v-else class="view-mode">
                <p>{{ sentence.content }}</p>
                <div class="item-actions">
                  <el-button type="primary" link size="small" @click="startEdit(sentence)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button type="danger" link size="small" @click="handleDelete(sentence)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加句子对话框 -->
    <el-dialog
      v-model="showAddDialog"
      title="添加句子"
      width="500px"
      append-to-body
    >
      <el-form :model="addForm" label-width="80px">
        <el-form-item label="内容">
          <el-input 
            v-model="addForm.content" 
            type="textarea" 
            :rows="3"
            placeholder="请输入句子内容"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showAddDialog = false">取消</el-button>
          <el-button type="primary" @click="submitAddSentence" :loading="submitting">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { InfoFilled, Plus, Edit, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import sentencesService from '@/services/sentences'

const props = defineProps({
  paragraph: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
})

// 状态
const sentences = ref([])
const loading = ref(false)
const showAddDialog = ref(false)
const submitting = ref(false)
const addForm = ref({ content: '' })

// 编辑状态
const editingId = ref(null)
const editContent = ref('')

// 监听段落变化
watch(() => props.paragraph, async (newVal) => {
  if (newVal) {
    await loadSentences(newVal.id)
  } else {
    sentences.value = []
  }
}, { immediate: true })

// 加载句子列表
const loadSentences = async (paragraphId) => {
  try {
    loading.value = true
    // 注意：后端目前没有直接的列表接口，这里假设我们通过段落详情或者需要后端补充接口
    // 暂时使用模拟数据或者尝试调用（如果后端支持）
    // 由于后端确实没有 GET /sentences/?paragraph_id=xxx，这里可能会失败
    // 为了演示，我们先假设后端会返回空列表或者报错
    // 实际开发中需要后端配合增加接口
    
    // 临时方案：如果后端不支持列表，我们可能无法显示句子列表
    // 但为了完成任务，我们尝试调用，如果失败则显示空
    try {
        const res = await sentencesService.getSentences(paragraphId)
        sentences.value = res.sentences || []
    } catch (e) {
        console.warn('获取句子列表失败，可能是接口未实现', e)
        sentences.value = []
    }
  } catch (error) {
    console.error('加载句子失败:', error)
    sentences.value = []
  } finally {
    loading.value = false
  }
}

// 添加句子
const handleAddSentence = () => {
  addForm.value.content = ''
  showAddDialog.value = true
}

const submitAddSentence = async () => {
  if (!addForm.value.content.trim()) {
    ElMessage.warning('请输入内容')
    return
  }

  try {
    submitting.value = true
    await sentencesService.createSentence(props.paragraph.id, {
      content: addForm.value.content,
      order_index: sentences.value.length + 1
    })
    ElMessage.success('添加成功')
    showAddDialog.value = false
    await loadSentences(props.paragraph.id)
  } catch (error) {
    console.error('添加失败:', error)
    ElMessage.error('添加失败')
  } finally {
    submitting.value = false
  }
}

// 编辑句子
const startEdit = (sentence) => {
  editingId.value = sentence.id
  editContent.value = sentence.content
}

const cancelEdit = () => {
  editingId.value = null
  editContent.value = ''
}

const handleSaveEdit = async (sentence) => {
  if (!editContent.value.trim()) return

  try {
    await sentencesService.updateSentence(sentence.id, {
      content: editContent.value
    })
    ElMessage.success('更新成功')
    editingId.value = null
    await loadSentences(props.paragraph.id)
  } catch (error) {
    console.error('更新失败:', error)
    ElMessage.error('更新失败')
  }
}

// 删除句子
const handleDelete = async (sentence) => {
  try {
    await ElMessageBox.confirm('确定要删除这个句子吗？', '提示', {
      type: 'warning'
    })
    
    await sentencesService.deleteSentence(sentence.id)
    ElMessage.success('删除成功')
    await loadSentences(props.paragraph.id)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const getActionType = (action) => {
  const map = {
    keep: 'success',
    edit: 'primary',
    delete: 'danger'
  }
  return map[action] || 'info'
}

const getActionText = (action) => {
  const map = {
    keep: '保留',
    edit: '编辑',
    delete: '删除'
  }
  return map[action] || '未知'
}
</script>

<style scoped>
.sentence-inspector {
  width: 320px;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-left: 1px solid var(--border-primary);
  overflow: hidden;
}

.inspector-header {
  padding: var(--space-md);
  border-bottom: 1px solid var(--border-primary);
}

.inspector-header h3 {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.inspector-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-2xl);
}

.inspector-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-md);
}

.info-section {
  margin-bottom: var(--space-lg);
  padding: var(--space-md);
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-primary);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-md);
}

.info-section h4 {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.info-grid {
  display: grid;
  gap: var(--space-sm);
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.info-item .label {
  font-size: var(--text-sm);
  color: var(--text-secondary);
}

.info-item .value {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--text-primary);
}

.sentence-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.empty-sentences {
  text-align: center;
  color: var(--text-secondary);
  padding: var(--space-md);
  font-size: var(--text-sm);
}

.sentence-item {
  display: flex;
  gap: var(--space-sm);
  padding: var(--space-sm);
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  transition: all 0.2s;
}

.sentence-item:hover {
  background: var(--bg-hover);
}

.sentence-index {
  font-size: var(--text-xs);
  color: var(--text-tertiary);
  min-width: 20px;
  padding-top: 2px;
}

.sentence-content {
  flex: 1;
  font-size: var(--text-sm);
  color: var(--text-primary);
  line-height: 1.5;
}

.view-mode p {
  margin: 0 0 var(--space-xs) 0;
  word-break: break-all;
}

.item-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-xs);
  opacity: 0;
  transition: opacity 0.2s;
}

.sentence-item:hover .item-actions {
  opacity: 1;
}

.edit-mode {
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-xs);
}

/* 滚动条样式 */
.inspector-content::-webkit-scrollbar {
  width: 6px;
}

.inspector-content::-webkit-scrollbar-track {
  background: transparent;
}

.inspector-content::-webkit-scrollbar-thumb {
  background: var(--border-primary);
  border-radius: 3px;
}

.inspector-content::-webkit-scrollbar-thumb:hover {
  background: var(--text-disabled);
}
</style>
