/**
 * 项目管理状态管理 - 简洁实现，严格按照规范
 * 使用Pinia管理项目相关的状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { projectsService, projectUtils } from '@/services/projects'

export const useProjectsStore = defineStore('projects', () => {
  // 状态定义
  const projects = ref([])
  const currentProject = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // 分页状态
  const pagination = ref({
    page: 1,
    size: 20,
    total: 0,
    totalPages: 0
  })

  // 搜索和过滤状态
  const searchQuery = ref('')
  const statusFilter = ref('')
  const sortBy = ref('created_at')
  const sortOrder = ref('desc')

  // 计算属性
  const filteredProjects = computed(() => {
    let result = projects.value

    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      result = result.filter(project =>
        project.title.toLowerCase().includes(query) ||
        (project.description && project.description.toLowerCase().includes(query))
      )
    }

    if (statusFilter.value) {
      result = result.filter(project => project.status === statusFilter.value)
    }

    return result
  })

  const projectsByStatus = computed(() => {
    const groups = {}
    projects.value.forEach(project => {
      if (!groups[project.status]) {
        groups[project.status] = []
      }
      groups[project.status].push(project)
    })
    return groups
  })

  const recentProjects = computed(() => {
    return [...projects.value]
      .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
      .slice(0, 5)
  })

  const hasUnprocessedFiles = computed(() => {
    return projects.value.some(project =>
      !['completed', 'failed'].includes(project.status)
    )
  })

  // 方法
  /**
   * 获取项目列表
   * @param {Object} params - 查询参数
   */
  const fetchProjects = async (params = {}) => {
    try {
      loading.value = true
      error.value = null

      const queryParams = {
        page: pagination.value.page,
        size: pagination.value.size,
        search: searchQuery.value,
        project_status: statusFilter.value,
        sort_by: sortBy.value,
        sort_order: sortOrder.value,
        ...params
      }

      const response = await projectsService.getProjects(queryParams)

      projects.value = response.projects || []
      pagination.value = {
        page: response.page || queryParams.page,
        size: response.size || queryParams.size,
        total: response.total || 0,
        totalPages: response.total_pages || Math.ceil(response.total / queryParams.size)
      }

      return response

    } catch (err) {
      error.value = err.message || '获取项目列表失败'
      ElMessage.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取项目详情
   * @param {string} projectId - 项目ID
   */
  const fetchProjectById = async (projectId) => {
    try {
      loading.value = true
      error.value = null

      const project = await projectsService.getProjectById(projectId)
      currentProject.value = project

      // 更新列表中的项目数据
      const index = projects.value.findIndex(p => p.id === projectId)
      if (index !== -1) {
        projects.value[index] = project
      }

      return project

    } catch (err) {
      error.value = err.message || '获取项目详情失败'
      ElMessage.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建项目
   * @param {Object} projectData - 项目数据
   */
  const createProject = async (projectData) => {
    try {
      loading.value = true
      error.value = null

      const project = await projectsService.createProject(projectData)

      // 添加到列表开头
      projects.value.unshift(project)
      pagination.value.total += 1

      ElMessage.success('项目创建成功')
      return project

    } catch (err) {
      error.value = err.message || '创建项目失败'
      ElMessage.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新项目
   * @param {string} projectId - 项目ID
   * @param {Object} updateData - 更新数据
   */
  const updateProject = async (projectId, updateData) => {
    try {
      loading.value = true
      error.value = null

      const updatedProject = await projectsService.updateProject(projectId, updateData)

      // 更新列表中的项目
      const index = projects.value.findIndex(p => p.id === projectId)
      if (index !== -1) {
        projects.value[index] = updatedProject
      }

      // 更新当前项目
      if (currentProject.value?.id === projectId) {
        currentProject.value = updatedProject
      }

      ElMessage.success('项目更新成功')
      return updatedProject

    } catch (err) {
      error.value = err.message || '更新项目失败'
      ElMessage.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除项目
   * @param {string} projectId - 项目ID
   */
  const deleteProject = async (projectId) => {
    try {
      loading.value = true
      error.value = null

      await projectsService.deleteProject(projectId)

      // 从列表中移除
      const index = projects.value.findIndex(p => p.id === projectId)
      if (index !== -1) {
        projects.value.splice(index, 1)
        pagination.value.total -= 1
      }

      // 清除当前项目
      if (currentProject.value?.id === projectId) {
        currentProject.value = null
      }

      ElMessage.success('项目删除成功')

    } catch (err) {
      error.value = err.message || '删除项目失败'
      ElMessage.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 设置搜索条件
   * @param {Object} filters - 过滤条件
   */
  const setFilters = (filters = {}) => {
    if (filters.search !== undefined) searchQuery.value = filters.search
    if (filters.status !== undefined) statusFilter.value = filters.status
    if (filters.sortBy !== undefined) sortBy.value = filters.sortBy
    if (filters.sortOrder !== undefined) sortOrder.value = filters.sortOrder
  }

  /**
   * 重置状态
   */
  const resetState = () => {
    projects.value = []
    currentProject.value = null
    loading.value = false
    error.value = null
    searchQuery.value = ''
    statusFilter.value = ''
    pagination.value = {
      page: 1,
      size: 20,
      total: 0,
      totalPages: 0
    }
  }

  return {
    // 状态
    projects,
    currentProject,
    loading,
    error,
    pagination,
    searchQuery,
    statusFilter,
    sortBy,
    sortOrder,

    // 计算属性
    filteredProjects,
    projectsByStatus,
    recentProjects,
    hasUnprocessedFiles,

    // 方法
    fetchProjects,
    fetchProjectById,
    createProject,
    updateProject,
    deleteProject,
    setFilters,
    resetState,

    // 工具函数
    getStatusText: projectUtils.getStatusText,
    getStatusType: projectUtils.getStatusType,
    getStatusIcon: projectUtils.getStatusIcon,
    calculateProgress: projectUtils.calculateProgress,
    isEditable: projectUtils.isEditable,
    isDeletable: projectUtils.isDeletable,
    formatFileSize: projectUtils.formatFileSize,
    formatDateTime: projectUtils.formatDateTime,
    formatNumber: projectUtils.formatNumber
  }
})