import { get, post, del, upload } from './api'

/**
 * 文件管理服务 - 职责分离后的纯文件操作
 */
export const fileService = {
  /**
   * 纯文件上传，返回文件ID
   * @param {FormData} formData - 包含文件的表单数据
   * @param {Function} onProgress - 进度回调函数
   * @returns {Promise} 上传结果，包含file_id
   */
  async uploadFile(formData, onProgress) {
    return await upload('/files/upload', formData, {
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress(percentCompleted)
        }
      }
    })
  },

  /**
   * 删除文件
   * @param {string} fileId - 文件ID
   * @returns {Promise} 删除结果
   */
  async deleteFile(fileId) {
    return await del(`/files/${fileId}`)
  },

  /**
   * 获取文件信息
   * @param {string} fileId - 文件ID
   * @returns {Promise} 文件信息
   */
  async getFileInfo(fileId) {
    return await get(`/files/${fileId}`)
  },

  /**
   * 获取文件下载URL
   * @param {string} fileId - 文件ID
   * @returns {Promise} 下载URL信息
   */
  async getDownloadUrl(fileId) {
    return await get(`/files/${fileId}/download`)
  }
}


/**
 * 兼容性包装器 - 为了保持向后兼容
 * @deprecated 建议使用 fileService
 */
export const uploadService = {
  /**
   * 上传文件（兼容性方法）
   * @param {Object} data - 上传数据
   * @returns {Promise} 上传结果
   */
  async uploadFile(data) {
    const { formData, onProgress } = data
    return await fileService.uploadFile(formData, onProgress)
  }
}

/**
 * 文件验证工具
 */
export const fileValidator = {
  /**
   * 验证文件类型
   * @param {File} file - 文件对象
   * @param {Array} allowedTypes - 允许的文件类型
   * @returns {boolean} 是否有效
   */
  isValidFileType(file, allowedTypes = ['.txt', '.md', '.docx', '.epub']) {
    const extension = '.' + file.name.split('.').pop().toLowerCase()
    return allowedTypes.includes(extension)
  },

  /**
   * 验证文件大小
   * @param {File} file - 文件对象
   * @param {number} maxSize - 最大大小（字节）
   * @returns {boolean} 是否有效
   */
  isValidFileSize(file, maxSize = 100 * 1024 * 1024) {
    return file.size <= maxSize
  },

  /**
   * 获取文件类型描述
   * @param {string} filename - 文件名
   * @returns {string} 文件类型描述
   */
  getFileTypeDescription(filename) {
    const extension = '.' + filename.split('.').pop().toLowerCase()
    const typeMap = {
      '.txt': 'TXT文档',
      '.md': 'Markdown文档',
      '.docx': 'Word文档',
      '.epub': 'EPUB电子书'
    }
    return typeMap[extension] || '未知文件类型'
  },

  /**
   * 格式化文件大小
   * @param {number} bytes - 字节数
   * @returns {string} 格式化后的大小
   */
  formatFileSize(bytes) {
    if (!bytes) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  },

  /**
   * 验证文件完整性
   * @param {File} file - 文件对象
   * @returns {Promise<boolean>} 是否完整
   */
  async validateFileIntegrity(file) {
    return new Promise((resolve) => {
      try {
        // 简单的文件读取验证
        const reader = new FileReader()
        reader.onload = () => resolve(true)
        reader.onerror = () => resolve(false)
        reader.readAsArrayBuffer(file.slice(0, 1024)) // 只读取前1KB验证
      } catch (error) {
        resolve(false)
      }
    })
  }
}


// 导出单个函数以兼容现有导入
export const uploadFile = uploadService.uploadFile

export default uploadService