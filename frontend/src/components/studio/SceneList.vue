<template>
  <div class="script-board">
    <div v-for="scene in script.scenes" :key="scene.order_index" class="scene-card">
      <div class="scene-header">
        <h3>场景 {{ scene.order_index }}: {{ scene.location }}</h3>
        <span class="scene-meta">{{ scene.time_of_day }} | {{ scene.atmosphere }}</span>
      </div>
      <p class="scene-desc">{{ scene.description }}</p>

      <div class="shots-grid">
        <el-card v-for="shot in scene.shots" :key="shot.order_index" class="shot-card-enhanced" shadow="hover">
          <!-- 1️⃣ 预览区域 -->
          <div class="shot-preview-zone">
            <!-- 视频模式 -->
            <div v-if="shot.video_url && (!showVideo || showVideo[shot.id] !== false)" class="video-preview">
              <video :src="shot.video_url" controls class="shot-video" :poster="shot.first_frame_url"></video>
              <div class="video-badge">
                <el-tag type="success" effect="dark">
                  <el-icon><VideoCamera /></el-icon>
                  视频已生成
                </el-tag>
              </div>
              <div class="video-actions">
                <el-button 
                  size="small" 
                  circle 
                  :icon="Picture"
                  @click="$emit('toggle-view', shot.id, false)"
                  title="查看首尾帧"
                />
              </div>
            </div>
            
            <!-- 首尾帧模式 -->
            <template v-else>
              <div class="keyframes-preview">
                <div class="keyframe-box">
                  <el-image 
                    :src="shot.first_frame_url" 
                    fit="cover"
                    :preview-src-list="shot.first_frame_url ? [shot.first_frame_url] : []"
                    preview-teleported
                    hide-on-click-modal
                  >
                    <template #placeholder>
                      <div class="frame-placeholder">
                        <el-icon :size="32"><Picture /></el-icon>
                        <p>首帧待生成</p>
                      </div>
                    </template>
                  </el-image>
                  <div class="frame-label start">START</div>
                  <div class="frame-actions">
                    <el-button 
                      size="small" 
                      type="primary" 
                      circle 
                      :icon="Refresh"
                      @click.stop="$emit('shot-command', 'regen-keyframe', shot)"
                      title="重新生成首帧"
                    />
                  </div>
                </div>
                
                <div class="keyframe-divider">
                  <el-icon><DArrowRight /></el-icon>
                </div>
                
                <div class="keyframe-box">
                  <el-image 
                    :src="shot.last_frame_url" 
                    fit="cover"
                    :preview-src-list="shot.last_frame_url ? [shot.last_frame_url] : []"
                    preview-teleported
                    hide-on-click-modal
                  >
                    <template #placeholder>
                      <div class="frame-placeholder">
                        <el-icon :size="32"><Picture /></el-icon>
                        <p>尾帧待生成</p>
                      </div>
                    </template>
                  </el-image>
                  <div class="frame-label end">END</div>
                  <div class="frame-actions">
                    <el-button 
                      size="small" 
                      type="primary" 
                      circle 
                      :icon="Refresh"
                      @click.stop="$emit('shot-command', 'regen-last-frame', shot)"
                      title="重新生成尾帧"
                    />
                  </div>
                </div>
              </div>
              
              <!-- 如果有视频,显示切换到视频的按钮 -->
              <div v-if="shot.video_url" class="switch-to-video">
                <el-button 
                  size="small" 
                  type="success"
                  :icon="VideoPlay"
                  @click="$emit('toggle-view', shot.id, true)"
                >
                  查看视频
                </el-button>
              </div>
            </template>
            
            <!-- 状态覆盖层 -->
            <div v-if="shot.status === 'processing'" class="status-overlay">
              <el-icon class="is-loading" :size="40"><Loading /></el-icon>
              <p>AI 创作中...</p>
            </div>
            
            <div v-if="shot.status === 'failed'" class="status-overlay error">
              <el-icon :size="40"><CircleClose /></el-icon>
              <p>生成失败</p>
              <el-text size="small" type="danger">{{ shot.last_error }}</el-text>
            </div>
          </div>
          
          <!-- 2️⃣ 信息区域 -->
          <div class="shot-info-zone">
            <div class="shot-header">
              <div class="shot-meta">
                <span class="shot-number">SHOT {{ shot.order_index }}</span>
                <el-tag v-if="shot.camera_movement" size="small" type="info">
                  <el-icon><VideoCamera /></el-icon>
                  {{ shot.camera_movement }}
                </el-tag>
              </div>
              <el-button 
                link 
                :icon="Edit" 
                size="small"
                @click="toggleEdit(shot.id)"
              >
                编辑提示词
              </el-button>
            </div>
            
            <div class="shot-description">
              <el-text line-clamp="3" :title="shot.visual_description">
                {{ shot.visual_description }}
              </el-text>
            </div>
            
            <div v-if="shot.dialogue" class="shot-dialogue">
              <el-icon><Mic /></el-icon>
              <span class="dialogue-text">"{{ shot.dialogue }}"</span>
            </div>
            
            <!-- 角色标签 -->
            <div v-if="getShotCharacters(shot).length" class="shot-characters">
              <span class="label">出场角色:</span>
              <el-space :size="4">
                <el-tooltip 
                  v-for="char in getShotCharacters(shot)" 
                  :key="char.id"
                  :content="char.name"
                  placement="top"
                >
                  <el-avatar 
                    :size="28" 
                    :src="char.avatar_url"
                    :class="{ 'no-avatar': !char.avatar_url }"
                  >
                    {{ char.name.charAt(0) }}
                  </el-avatar>
                </el-tooltip>
              </el-space>
            </div>
          </div>
          
          <!-- 3️⃣ 操作区域 -->
          <div class="shot-action-zone">
            <div class="primary-action">
              <el-tooltip 
                :content="getActionTooltip(shot)" 
                placement="top"
                :disabled="canProduceShot(shot)"
              >
                <el-button 
                  type="primary" 
                  :disabled="!canProduceShot(shot)"
                  :loading="shot.status === 'processing'"
                  @click="$emit('produce-shot', shot)"
                  style="width: 100%;"
                >
                  <el-icon><VideoPlay /></el-icon>
                  {{ shot.video_url ? '重新生成视频' : '生成视频' }}
                </el-button>
              </el-tooltip>
            </div>
            
            <div class="secondary-actions">
              <el-dropdown trigger="click" @command="(cmd) => $emit('shot-command', cmd, shot)" style="width: 100%;">
                <el-button style="width: 100%;">
                  <el-icon><MoreFilled /></el-icon>
                  更多操作
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="regen-keyframe">
                      <el-icon><Picture /></el-icon>
                      重新生成首帧
                    </el-dropdown-item>
                    <el-dropdown-item command="regen-last-frame">
                      <el-icon><Picture /></el-icon>
                      重新生成尾帧
                    </el-dropdown-item>
                    <el-dropdown-item command="regen-video" divided :disabled="!shot.video_url">
                      <el-icon><VideoPlay /></el-icon>
                      重新生成视频
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
          
          <!-- 4️⃣ Prompt编辑器 -->
          <el-collapse-transition>
            <div v-if="activeShotId === shot.id" class="prompt-editor">
              <el-divider content-position="left">
                <el-icon><Edit /></el-icon>
                提示词编辑
              </el-divider>
              
              <div class="editor-section">
                <div class="editor-label">
                  <el-icon><Picture /></el-icon>
                  首帧提示词
                </div>
                <el-input 
                  v-model="shot.first_frame_prompt" 
                  type="textarea" 
                  :rows="3"
                  placeholder="描述首帧画面..."
                  @change="$emit('update-prompt', shot.id, 'first', shot.first_frame_prompt)"
                />
              </div>
              
              <div class="editor-section">
                <div class="editor-label">
                  <el-icon><Picture /></el-icon>
                  尾帧提示词
                </div>
                <el-input 
                  v-model="shot.last_frame_prompt" 
                  type="textarea" 
                  :rows="3"
                  placeholder="描述尾帧画面..."
                  @change="$emit('update-prompt', shot.id, 'last', shot.last_frame_prompt)"
                />
              </div>
            </div>
          </el-collapse-transition>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { 
  Picture, VideoPlay, MoreFilled, Mic, Loading, Edit, 
  VideoCamera, Refresh, DArrowRight, CircleClose 
} from '@element-plus/icons-vue'

const props = defineProps({
  script: Object,
  showVideo: Object,
  characters: Array
})

defineEmits(['toggle-view', 'produce-shot', 'shot-command', 'update-prompt'])

const activeShotId = ref(null)

const toggleEdit = (id) => {
  activeShotId.value = activeShotId.value === id ? null : id
}

const getShotCharacters = (shot) => {
  return props.characters.filter(char => 
    shot.visual_description.includes(char.name) || 
    (shot.dialogue && shot.dialogue.includes(char.name))
  )
}

const canProduceShot = (shot) => {
  if (!shot.first_frame_url) return false
  for (const char of props.characters) {
    if (shot.visual_description.includes(char.name) && !char.avatar_url) {
      return false
    }
  }
  return true
}

const getActionTooltip = (shot) => {
  if (!shot.first_frame_url) {
    return '请先生成首帧图'
  }
  const missingChars = props.characters.filter(char => 
    shot.visual_description.includes(char.name) && !char.avatar_url
  )
  if (missingChars.length > 0) {
    return `角色 ${missingChars.map(c => c.name).join(', ')} 的形象缺失，请先生成`
  }
  return ''
}
</script>

<style scoped>
.script-board {
  max-width: 1000px;
  margin: 0 auto;
}

.scene-card {
  background: #fff;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 30px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
}

.scene-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
  padding-bottom: 10px;
}

.scene-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.scene-meta {
  font-size: 13px;
  color: #909399;
}

.scene-desc {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 20px;
  background: #fdf6ec;
  padding: 10px;
  border-radius: 4px;
}

.shots-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
}

/* ========== 增强版卡片 ========== */
.shot-card-enhanced {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: all 0.3s;
  border-radius: 8px;
}

.shot-card-enhanced:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0,0,0,0.12) !important;
}

/* 1️⃣ 预览区域 */
.shot-preview-zone {
  position: relative;
  height: 200px;
  background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
  overflow: hidden;
}

/* 首尾帧预览 */
.keyframes-preview {
  display: flex;
  height: 100%;
}

.keyframe-box {
  flex: 1;
  position: relative;
  cursor: pointer;
  overflow: hidden;
  transition: transform 0.3s;
}

.keyframe-box:hover {
  transform: scale(1.05);
  z-index: 2;
}

.keyframe-box:hover .frame-actions {
  opacity: 1;
}

.keyframe-box :deep(.el-image) {
  width: 100%;
  height: 100%;
}

.frame-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #909399;
  background: #2b2b2b;
}

.frame-placeholder p {
  margin-top: 8px;
  font-size: 12px;
}

.frame-label {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.8), transparent);
  color: #fff;
  text-align: center;
  padding: 8px 4px 4px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 1px;
}

.frame-label.start {
  background: linear-gradient(to top, rgba(64, 158, 255, 0.8), transparent);
}

.frame-label.end {
  background: linear-gradient(to top, rgba(103, 194, 58, 0.8), transparent);
}

.frame-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transition: opacity 0.3s;
}

.keyframe-divider {
  width: 2px;
  background: rgba(255,255,255,0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,0.5);
}

/* 视频预览 */
.video-preview {
  position: relative;
  height: 100%;
}

.video-badge {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 10;
}

.video-actions {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 10;
}

/* 切换到视频按钮 */
.switch-to-video {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10;
}

/* 状态覆盖层 */
.status-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.85);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #409eff;
  gap: 12px;
  z-index: 10;
}

.status-overlay.error {
  color: #f56c6c;
}

.status-overlay p {
  font-size: 14px;
  margin: 0;
}

/* 2️⃣ 信息区域 */
.shot-info-zone {
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.shot-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.shot-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.shot-number {
  font-size: 14px;
  font-weight: 700;
  color: #409eff;
  letter-spacing: 0.5px;
}

.shot-description {
  font-size: 13px;
  line-height: 1.6;
  color: #606266;
}

.shot-dialogue {
  background: linear-gradient(135deg, #f0f9eb 0%, #e8f5e9 100%);
  border-left: 3px solid #67c23a;
  padding: 10px 12px;
  border-radius: 6px;
  display: flex;
  gap: 8px;
  align-items: flex-start;
  color: #67c23a;
  font-size: 12px;
}

.dialogue-text {
  font-style: italic;
  flex: 1;
  line-height: 1.5;
}

.shot-characters {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-top: 1px dashed #ebeef5;
}

.shot-characters .label {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.shot-characters .no-avatar {
  background: #f56c6c;
  border: 2px dashed #fff;
}

/* 3️⃣ 操作区域 */
.shot-action-zone {
  padding: 16px;
  background: #fafafa;
  border-top: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.primary-action {
  width: 100%;
}

.secondary-actions {
  width: 100%;
}

/* 4️⃣ Prompt编辑器 */
.prompt-editor {
  padding: 16px;
  background: #f8f9fa;
  border-top: 1px solid #ebeef5;
}

.editor-section {
  margin-bottom: 16px;
}

.editor-section:last-child {
  margin-bottom: 0;
}

.editor-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #606266;
  font-weight: 600;
  margin-bottom: 8px;
}

/* 响应式 */
@media (min-width: 1400px) {
  .shots-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1000px) and (max-width: 1399px) {
  .shots-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 999px) {
  .shots-grid {
    grid-template-columns: 1fr;
  }
  
  .shot-preview-zone {
    height: 180px;
  }
}

.shot-card {
  display: flex;
  flex-direction: column;
  transition: all 0.3s;
}

.shot-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 8px 16px rgba(0,0,0,0.1);
}

.shot-visual {
  height: 160px;
  background: #000;
  border-radius: 4px;
  margin-bottom: 12px;
  position: relative;
  overflow: hidden;
}

.dual-keyframes {
  display: flex;
  height: 100%;
}

.keyframe-item {
  flex: 1;
  position: relative;
  border-right: 1px solid rgba(255,255,255,0.2);
}

.keyframe-item:last-child {
  border-right: none;
}

.frame-tag {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  background: rgba(0,0,0,0.6);
  color: #fff;
  font-size: 10px;
  text-align: center;
  padding: 2px 0;
}

.image-placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: #2b2b2b;
  color: #909399;
}

.placeholder-text {
  font-size: 10px;
  margin-top: 4px;
}

.shot-preview {
  width: 100%;
  height: 100%;
  display: block;
}

.processing-status {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: rgba(0,0,0,0.8);
  color: #409eff;
  gap: 8px;
}

.shot-actions {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.shot-visual:hover .shot-actions {
  opacity: 1;
}

.shot-info {
  padding: 0 4px;
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
  font-size: 13px;
  line-height: 1.4;
  color: #2c3e50;
  margin-bottom: 8px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.shot-dialogue {
  background: #f0f9eb;
  padding: 6px;
  border-radius: 4px;
  display: flex;
  align-items: flex-start;
  gap: 6px;
  color: #67c23a;
  font-size: 12px;
}

.dialogue-text {
  font-style: italic;
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
  top: 5px;
  right: 5px;
  opacity: 0.6;
  transition: opacity 0.3s;
  z-index: 10;
}

.view-image-btn:hover {
  opacity: 1;
}

.error-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 5;
}

.is-loading {
  animation: rotating 2s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.prompt-editor {
  margin-top: 10px;
  background: #f8f9fa;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #ebeef5;
}

.editor-row {
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
}

.editor-row:last-child {
  margin-bottom: 0;
}

.editor-row .label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
  font-weight: bold;
}

.shot-references {
  margin-top: 8px;
  padding: 4px 0;
  border-top: 1px dashed #ebeef5;
}

.reference-avatars {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.reference-avatars :deep(.el-avatar) {
  border: 1px solid #fff;
  box-shadow: 0 0 2px rgba(0,0,0,0.1);
  background-color: #409eff;
  color: #fff;
  font-size: 10px;
}
</style>
