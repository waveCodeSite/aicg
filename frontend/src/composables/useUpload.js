/**
 * 文件上传组合式API
 * 提供文件上传的通用逻辑和状态管理
 */

import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { fileService, fileValidator } from '@/services/upload'

export function useUpload(options = {}) {
  const {
    maxFileSize = 100 * 1024 * 1024, // 100MB
    allowedTypes = ['.txt', '.md', '.docx', '.epub'],
    onProgress = null,
    onSuccess = null,
    onError = null
  } = options

  // 状态定义
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const uploadError = ref(null)
  const uploadResult = ref(null)

  // 计算属性
  const isUploading = computed(() => uploading.value)
  const hasError = computed(() => !!uploadError.value)
  const isCompleted = computed(() => !!uploadResult.value && !uploading.value)

  // 方法
  /**
   * 验证文件
   * @param {File} file - 文件对象
   * @returns {Object} 验证结果
   */
  const validateFile = (file) => {
    const result = {
      valid: true,
      errors: []
    }

    // 检查文件类型
    if (!fileValidator.isValidFileType(file, allowedTypes)) {
      result.valid = false
      result.errors.push(`不支持的文件类型，仅支持: ${allowedTypes.join(', ')}`)
    }

    // 检查文件大小
    if (!fileValidator.isValidFileSize(file, maxFileSize)) {
      result.valid = false
      result.errors.push(`文件大小超过限制，最大允许: ${fileValidator.formatFileSize(maxFileSize)}`)
    }

    // 检查文件名
    if (!file.name || file.name.trim() === '') {
      result.valid = false
      result.errors.push('文件名不能为空')
    }

    return result
  }

  /**
   * 上传文件
   * @param {File} file - 文件对象
   * @returns {Promise} 上传结果
   */
  const uploadFile = async (file) => {
    if (!file) {
      ElMessage.warning('请选择文件')
      return
    }

    // 验证文件
    const validation = validateFile(file)
    if (!validation.valid) {
      const errorMessage = validation.errors.join('; ')
      uploadError.value = errorMessage
      ElMessage.error(errorMessage)

      if (onError) {
        onError(new Error(errorMessage))
      }
      return
    }

    // 重置状态
    uploading.value = true
    uploadProgress.value = 0
    uploadError.value = null
    uploadResult.value = null

    try {
      // 准备表单数据
      const formData = new FormData()
      formData.append('file', file)

      // 开始上传
      const result = await fileService.uploadFile(formData, (progress) => {
        uploadProgress.value = progress

        if (onProgress) {
          onProgress(progress)
        }
      })

      // 上传成功
      if (result.success) {
        uploadResult.value = result
        ElMessage.success('文件上传成功')

        if (onSuccess) {
          onSuccess(result)
        }

        return result
      } else {
        throw new Error(result.message || '上传失败')
      }

    } catch (error) {
      const errorMessage = error.message || '上传失败'
      uploadError.value = errorMessage
      ElMessage.error(errorMessage)

      if (onError) {
        onError(error)
      }

      throw error

    } finally {
      uploading.value = false
    }
  }

  /**
   * 重置状态
   */
  const reset = () => {
    uploading.value = false
    uploadProgress.value = 0
    uploadError.value = null
    uploadResult.value = null
  }

  /**
   * 清除错误
   */
  const clearError = () => {
    uploadError.value = null
  }

  return {
    // 状态
    uploading,
    uploadProgress,
    uploadError,
    uploadResult,

    // 计算属性
    isUploading,
    hasError,
    isCompleted,

    // 方法
    validateFile,
    uploadFile,
    reset,
    clearError,

    // 工具函数
    formatFileSize: fileValidator.formatFileSize,
    getFileTypeDescription: fileValidator.getFileTypeDescription
  }
}

export default useUpload