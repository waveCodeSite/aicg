<template>
  <div class="studio-sidebar">
    <div class="sidebar-header">
      <h3>剧组成员</h3>
      <el-button type="primary" link size="small" @click="$emit('detect')" :loading="extracting">
        <el-icon><MagicStick /></el-icon> 智能提取
      </el-button>
    </div>
    <div class="cast-list">
      <el-card v-for="char in characters" :key="char.id" class="char-card" :body-style="{ padding: '10px' }">
        <div class="char-header">
          <el-image 
            :src="char.avatar_url" 
            class="char-avatar" 
            :preview-src-list="char.avatar_url ? [char.avatar_url] : []"
            preview-teleported
            hide-on-click-modal
          >
            <template #placeholder>
              <div class="avatar-placeholder">
                <el-icon><User /></el-icon>
              </div>
            </template>
          </el-image>
          <div class="char-info">
            <div class="char-name">{{ char.name }}</div>
            <div class="char-status-row">
              <el-tag size="small" :type="char.avatar_url ? 'success' : 'info'">
                {{ char.avatar_url ? '已定妆' : '待定妆' }}
              </el-tag>
              <el-button 
                type="primary" 
                circle 
                size="small" 
                :icon="MagicStick" 
                @click="$emit('generate-avatar', char)"
                style="margin-left: 10px;"
                title="定妆/重绘形象"
              />
            </div>
          </div>
        </div>
        <div class="char-desc text-truncate">{{ char.description }}</div>
      </el-card>
      <div v-if="characters.length === 0" class="empty-cast">
        暂无角色，请点击智能提取
      </div>
    </div>
  </div>
</template>

<script setup>
import { MagicStick, User } from '@element-plus/icons-vue'

defineProps({
  characters: Array,
  extracting: Boolean
})

defineEmits(['detect', 'generate-avatar'])
</script>

<style scoped>
.studio-sidebar {
  width: 300px;
  background: #fff;
  border-left: 1px solid #dcdfe6;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.sidebar-header {
  padding: 15px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 15px;
  color: #303133;
}

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
  margin-bottom: 4px;
}

.char-status-row {
  display: flex;
  align-items: center;
}

.avatar-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  background: #f5f7fa;
  color: #909399;
}

.char-desc {
  font-size: 12px;
  color: #909399;
  line-height: 1.4;
}

.empty-cast {
  text-align: center;
  color: #909399;
  font-size: 13px;
  padding: 20px 0;
}
</style>
