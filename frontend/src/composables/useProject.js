/**
 * 项目管理的组合式函数
 * 提供项目的通用功能，避免在多个组件中重复代码
 */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useProjectsStore } from '@/stores/projects'
import projectsService from '@/services/projects'

export function useProject(projectId, emit = null) {
  const router = useRouter()
  const projectsStore = useProjectsStore()

  // 响应式数据
  const refreshing = ref(false)

  /**
   * 处理返回操作
   */
  const handleBack = () => {
    if (emit) {
      // 如果有父组件，使用emit
      emit('back')
    } else {
      // 如果是独立路由，导航回项目列表
      router.push('/projects')
    }
  }

  /**
   * 处理刷新操作
   */
  const handleRefresh = async (fetchProjectData = null) => {
    refreshing.value = true
    try {
      if (emit && fetchProjectData) {
        // 如果有父组件，使用emit
        emit('refresh', projectId.value)
      } else if (fetchProjectData) {
        // 如果是独立路由，重新获取数据
        await fetchProjectData()
      }
    } finally {
      setTimeout(() => {
        refreshing.value = false
      }, 1000)
    }
  }

  /**
   * 处理编辑项目操作
   */
  const handleEdit = (project, showEditorDialog = null, editingProject = null) => {
    if (emit) {
      // 如果有父组件，使用emit
      emit('edit', project)
    } else if (showEditorDialog && editingProject) {
      // 如果是独立路由，直接显示编辑对话框
      editingProject.value = project
      showEditorDialog.value = true
    } else {
      // 否则显示提示
      ElMessage.info('编辑功能暂不可用')
    }
  }

  /**
   * 处理归档项目操作
   */
  const handleArchive = async (project, fetchProjectData = null) => {
    try {
      if (emit) {
        // 如果有父组件，使用emit
        emit('archive', project)
      } else {
        // 如果是独立路由，直接实现归档功能
        await ElMessageBox.confirm(
          `确定要归档项目"${project.title}"吗？归档后项目将变为只读状态。`,
          '确认归档',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await projectsService.archiveProject(projectId.value)
        ElMessage.success('项目归档成功')

        // 重新获取项目数据
        if (fetchProjectData) {
          await fetchProjectData()
        }
      }
    } catch (error) {
      if (error !== 'cancel') {
        ElMessage.error('归档项目失败')
        console.error('归档项目失败:', error)
      }
    }
  }

  /**
   * 处理重新处理项目操作
   */
  const handleReprocess = async (project, fetchProjectData = null, startStatusPolling = null) => {
    try {
      if (emit) {
        // 如果有父组件，使用emit
        emit('reprocess', project)
      } else {
        // 如果是独立路由，直接实现重新处理功能
        await ElMessageBox.confirm(
          `确定要重新处理项目"${project.title}"吗？这将重新解析文件内容。`,
          '确认重新处理',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        )

        await projectsService.retryProject(projectId.value)
        ElMessage.success('重新处理任务已提交')

        // 重新获取项目数据
        if (fetchProjectData) {
          await fetchProjectData()
        }
      }

      // 重新开始状态轮询
      if (startStatusPolling) {
        setTimeout(() => {
          startStatusPolling()
        }, 1000) // 延迟1秒后开始轮询，确保状态已更新
      }
    } catch (error) {
      if (error !== 'cancel') {
        ElMessage.error('重新处理失败')
        console.error('重新处理失败:', error)
      }
    }
  }

  /**
   * 处理开始视频生成操作
   */
  const handleStartGeneration = (project) => {
    if (!['completed', 'parsed'].includes(project.status)) {
      ElMessage.warning('文件处理完成后才能开始视频生成')
      return
    }

    if (emit) {
      // 如果有父组件，使用emit
      emit('start-generation', project)
    } else {
      // 如果是独立路由，显示提示
      ElMessage.info('视频生成功能开发中...')
    }
  }

  /**
   * 处理章节管理操作
   */
  const handleManageChapters = () => {
    if (!projectId.value) {
      console.error('projectId 为空')
      ElMessage.error('项目ID丢失，请重新进入页面')
      return
    }
    const targetRoute = `/projects/${projectId.value}/chapters`
    router.push(targetRoute).then(() => {
      console.log('路由跳转成功')
    })
  }

  return {
    refreshing,
    handleBack,
    handleRefresh,
    handleEdit,
    handleArchive,
    handleReprocess,
    handleStartGeneration,
    handleManageChapters
  }
}