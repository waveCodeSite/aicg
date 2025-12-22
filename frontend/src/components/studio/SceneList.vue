<template>
  <div class="script-board">
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
              <el-button class="view-image-btn" size="small" circle @click="$emit('toggle-view', shot.id, false)">
                <el-icon><Picture /></el-icon>
              </el-button>
            </div>
            
            <!-- 首尾帧图 -->
            <template v-else>
              <div class="dual-keyframes">
                <div class="keyframe-item">
                  <el-image :src="shot.first_frame_url" fit="cover" class="shot-preview">
                    <template #placeholder>
                      <div class="image-placeholder small">
                        <el-icon><Picture /></el-icon>
                        <span class="placeholder-text">START</span>
                      </div>
                    </template>
                  </el-image>
                  <div class="frame-tag">START</div>
                </div>
                <div class="keyframe-item">
                  <el-image :src="shot.last_frame_url" fit="cover" class="shot-preview">
                    <template #placeholder>
                      <div class="image-placeholder small">
                        <el-icon><Picture /></el-icon>
                        <span class="placeholder-text">END</span>
                      </div>
                    </template>
                  </el-image>
                  <div class="frame-tag">END</div>
                </div>
              </div>
              
              <div v-if="shot.status === 'failed' && shot.last_error" class="error-overlay">
                 <el-alert :title="shot.last_error" type="error" :closable="false" show-icon />
              </div>

              <div class="shot-actions">
                <div v-if="shot.status === 'processing'" class="processing-status">
                   <el-icon class="is-loading"><Loading /></el-icon>
                   <span>生产中...</span>
                </div>
                <template v-else>
                  <el-tooltip v-if="!shot.first_frame_url" content="请先生成首帧图">
                    <el-button circle icon="VideoPlay" type="info" disabled></el-button>
                  </el-tooltip>
                  <el-tooltip v-else-if="!canProduceShot(shot)" content="部分角色形象缺失，请先生成">
                     <el-button circle icon="VideoPlay" type="info" disabled></el-button>
                  </el-tooltip>
                  <el-button v-else circle icon="VideoPlay" type="primary" @click="$emit('produce-shot', shot)"></el-button>
                </template>
              </div>
            </template>
          </div>
          <div class="shot-info">
            <div class="shot-header-row">
              <div class="shot-index">SHOT {{ shot.order_index }}</div>
              <div class="shot-menu">
                 <el-button link size="small" @click="toggleEdit(shot.id)">
                    <el-icon><Edit /></el-icon>
                 </el-button>
                 <el-dropdown trigger="click" @command="(cmd) => $emit('shot-command', cmd, shot)">
                    <el-icon class="more-btn"><MoreFilled /></el-icon>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="regen-keyframe">生成/重绘首帧(Start)</el-dropdown-item>
                        <el-dropdown-item command="regen-last-frame">生成/重绘尾帧(End)</el-dropdown-item>
                        <el-dropdown-item command="regen-video" :disabled="!shot.video_url">重新生成视频</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
              </div>
            </div>
            <div class="shot-detail">
               <div class="shot-desc" :title="shot.visual_description">{{ shot.visual_description }}</div>
                <div v-if="shot.dialogue" class="shot-dialogue">
                    <el-icon><Mic /></el-icon> 
                    <span class="dialogue-text">"{{ shot.dialogue }}"</span>
                </div>
             </div>

             <div class="shot-references" v-if="getShotCharacters(shot).length > 0">
                <div class="reference-avatars">
                  <el-tooltip 
                    v-for="char in getShotCharacters(shot)" 
                    :key="char.id" 
                    :content="char.name"
                  >
                    <el-avatar :size="20" :src="char.avatar_url">
                      {{ char.name.charAt(0) }}
                    </el-avatar>
                  </el-tooltip>
                </div>
             </div>
            
            <div v-if="activeShotId === shot.id" class="prompt-editor" @click.stop>
                <div class="editor-row">
                    <span class="label">First:</span>
                    <el-input 
                        v-model="shot.first_frame_prompt" 
                        type="textarea" 
                        :rows="2" 
                        size="small"
                        @change="$emit('update-prompt', shot.id, 'first', shot.first_frame_prompt)"
                    />
                </div>
                <div class="editor-row">
                    <span class="label">Last:</span>
                    <el-input 
                        v-model="shot.last_frame_prompt" 
                        type="textarea" 
                        :rows="2" 
                        size="small"
                        @change="$emit('update-prompt', shot.id, 'last', shot.last_frame_prompt)"
                    />
                </div>
            </div>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { Picture, VideoPlay, MoreFilled, Mic, Loading, Edit } from '@element-plus/icons-vue'

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
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
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
