<template>
  <div class="setting-section">
    <h2>个人资料</h2>
    <p>管理您的个人信息和头像</p>

    <div class="profile-section">
      <div class="avatar-section">
        <div class="avatar-container" @click="triggerFileSelect" :class="{ 'uploading': isUploadingAvatar }">
          <el-avatar :size="80" :src="previewAvatar || userForm.avatar_url" class="user-avatar">
            <el-icon size="40"><User /></el-icon>
          </el-avatar>
          <div v-if="isUploadingAvatar" class="upload-overlay">
            <el-progress type="circle" :percentage="uploadProgress" :width="60" />
          </div>
          <div v-else class="avatar-hover-overlay">
            <el-icon><Camera /></el-icon>
            <span>点击更换头像</span>
          </div>
        </div>
        <div class="avatar-actions">
          <input
            ref="avatarFileInput"
            type="file"
            accept="image/jpeg,image/jpg,image/png"
            style="display: none"
            @change="handleAvatarSelect"
          />
          <el-button
            type="primary"
            plain
            @click="triggerFileSelect"
            :loading="isUploadingAvatar"
            :disabled="isUploadingAvatar"
          >
            {{ isUploadingAvatar ? '上传中...' : '更换头像' }}
          </el-button>
          <el-button
            v-if="previewAvatar || userForm.avatar_url"
            type="danger"
            plain
            size="small"
            @click="removeAvatar"
            :disabled="isUploadingAvatar"
          >
            移除头像
          </el-button>
          <p class="upload-tip">支持 JPG、PNG 格式，建议尺寸 200x200px，最大5MB</p>
        </div>
      </div>

      <el-form :model="userForm" label-width="120px" class="profile-form">
        <el-form-item label="用户名">
          <el-input v-model="userForm.username" disabled>
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="显示名称">
          <el-input
            v-model="userForm.display_name"
            placeholder="请输入显示名称"
            maxlength="50"
            show-word-limit
          >
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="邮箱地址">
          <el-input v-model="userForm.email" disabled>
            <template #prefix>
              <el-icon><Message /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item label="注册时间">
          <el-input :value="formatDate(userForm.created_at, {}, userTimezone)" disabled>
            <template #prefix>
              <el-icon><Clock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            @click="saveProfile"
            :loading="profileLoading"
          >
            保存更改
          </el-button>
          <el-button @click="resetProfileForm">重置</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { User, Message, Clock, Camera } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { formatDate, getUserTimezone } from '@/utils/dateUtils'

const authStore = useAuthStore()
const profileLoading = ref(false)

// 头像上传相关
const avatarFileInput = ref(null)
const isUploadingAvatar = ref(false)
const uploadProgress = ref(0)
const previewAvatar = ref('')

// 用户表单数据
const userForm = reactive({
  username: '',
  display_name: '',
  email: '',
  avatar_url: '',
  created_at: new Date().toISOString()
})

// 用户时区
const userTimezone = computed(() => {
  return getUserTimezone(authStore.user);
})

// 初始化用户数据
const initUserData = async () => {
  try {
    if (authStore.user) {
      userForm.username = authStore.user.username || ''
      userForm.display_name = authStore.user.display_name || ''
      userForm.email = authStore.user.email || ''
      userForm.avatar_url = authStore.user.avatar_url || ''
      userForm.created_at = authStore.user.created_at || new Date().toISOString()
    } else {
      await authStore.getCurrentUser()
      initUserData()
    }
  } catch (error) {
    console.error('获取用户信息失败:', error)
    ElMessage.error('获取用户信息失败')
  }
}

// 保存个人资料
const saveProfile = async () => {
  if (!userForm.display_name.trim()) {
    ElMessage.warning('请输入显示名称')
    return
  }

  profileLoading.value = true
  try {
    const updateData = {
      display_name: userForm.display_name.trim()
    }

    await authStore.updateProfile(updateData)
    ElMessage.success('个人资料更新成功')
  } catch (error) {
    console.error('更新个人资料失败:', error)
    ElMessage.error('更新个人资料失败，请重试')
  } finally {
    profileLoading.value = false
  }
}

// 重置个人资料表单
const resetProfileForm = () => {
  initUserData()
  ElMessage.info('表单已重置')
}

// 触发文件选择
const triggerFileSelect = () => {
  if (isUploadingAvatar.value) return
  avatarFileInput.value?.click()
}

// 处理头像选择
const handleAvatarSelect = (event) => {
  const file = event.target.files[0]
  if (!file) return

  if (!file.type.match(/^image\/(jpeg|jpg|png)$/)) {
    ElMessage.error('请选择 JPG 或 PNG 格式的图片文件')
    return
  }

  if (file.size > 5 * 1024 * 1024) {
    ElMessage.error('图片文件大小不能超过 5MB')
    return
  }

  const reader = new FileReader()
  reader.onload = (e) => {
    previewAvatar.value = e.target.result
  }
  reader.readAsDataURL(file)

  uploadAvatar(file)
}

// 上传头像
const uploadAvatar = async (file) => {
  isUploadingAvatar.value = true
  uploadProgress.value = 0

  try {
    const response = await authStore.uploadAvatar(file, (progressEvent) => {
      const percentCompleted = Math.round(
        (progressEvent.loaded * 100) / progressEvent.total
      )
      uploadProgress.value = percentCompleted
    })

    if (response.user) {
      Object.assign(userForm, {
        avatar_url: response.user.avatar_url
      })
    }

    ElMessage.success('头像上传成功！')

    setTimeout(() => {
      previewAvatar.value = ''
      uploadProgress.value = 0
    }, 1000)

  } catch (error) {
    console.error('头像上传失败:', error)

    if (error.response?.status === 413) {
      ElMessage.error('图片文件过大，请选择小于5MB的图片')
    } else if (error.response?.status === 415) {
      ElMessage.error('不支持的图片格式，请选择JPG或PNG格式')
    } else if (error.response?.status === 400) {
      ElMessage.error(error.response?.data?.detail || '图片文件验证失败')
    } else {
      ElMessage.error('头像上传失败，请重试')
    }

    previewAvatar.value = ''
    uploadProgress.value = 0
  } finally {
    isUploadingAvatar.value = false
    if (avatarFileInput.value) {
      avatarFileInput.value.value = ''
    }
  }
}


// 移除头像
const removeAvatar = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要移除当前头像吗？移除后将恢复默认头像。',
      '移除头像',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )

    profileLoading.value = true
    try {
      const response = await authStore.removeAvatar()
      
      if (response.user) {
        Object.assign(userForm, {
          avatar_url: response.user.avatar_url
        })
      } else {
        userForm.avatar_url = ''
      }
      
      previewAvatar.value = ''
      ElMessage.success('头像已移除')
    } catch (error) {
      console.error('移除头像失败:', error)
      ElMessage.error('移除头像失败，请重试')
    } finally {
      profileLoading.value = false
    }
  } catch (error) {
    // 用户取消操作
    if (error !== 'cancel') {
      console.error('操作异常:', error)
    }
  }
}

onMounted(() => {
  initUserData()
})
</script>

<style scoped>
.setting-section {
  animation: fadeIn 0.3s ease-in-out;
  max-width: 900px;
}

.setting-section h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-primary);
  letter-spacing: -0.5px;
}

.setting-section > p {
  color: var(--text-secondary);
  margin-bottom: 40px;
  font-size: 14px;
}

.profile-section {
  display: flex;
  gap: 60px;
  align-items: flex-start;
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  width: 240px;
  flex-shrink: 0;
  padding-top: 10px;
}

.avatar-container {
  position: relative;
  cursor: pointer;
  border-radius: 50%;
  overflow: hidden;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-md);
  border: 4px solid var(--bg-primary);
}

.avatar-container:hover {
  box-shadow: var(--shadow-lg);
  transform: translateY(-2px);
}

.avatar-container:hover .avatar-hover-overlay {
  opacity: 1;
}

.avatar-hover-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(32, 33, 36, 0.6);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  opacity: 0;
  transition: opacity 0.3s ease;
  backdrop-filter: blur(2px);
}

.avatar-hover-overlay span {
  font-size: 12px;
  margin-top: 8px;
  font-weight: 500;
}

.upload-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
  width: 100%;
}

.upload-tip {
  font-size: 12px;
  color: var(--text-tertiary);
  text-align: center;
  margin: 0;
  line-height: 1.5;
  max-width: 200px;
}

.profile-form {
  flex: 1;
  max-width: 520px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: var(--text-primary);
}

:deep(.el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--border-primary) inset;
}

:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--primary-color) inset;
}

@media (max-width: 768px) {
  .profile-section {
    flex-direction: column;
    align-items: center;
    gap: 40px;
  }

  .avatar-section {
    width: 100%;
    padding-top: 0;
  }

  .profile-form {
    width: 100%;
    max-width: 100%;
  }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
