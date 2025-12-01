import { ref, onUnmounted } from 'vue'
import api from '@/services/api'
import { ElMessage } from 'element-plus'

export function useTaskPoller() {
  const taskStatus = ref(null)
  const isPolling = ref(false)
  const pollInterval = ref(null)
  const taskResult = ref(null)
  const taskStatistics = ref(null)

  const stopPolling = () => {
    if (pollInterval.value) {
      clearInterval(pollInterval.value)
      pollInterval.value = null
    }
    isPolling.value = false
  }

  const startPolling = (taskId, onSuccess = null, onError = null) => {
    if (!taskId) return

    stopPolling()
    isPolling.value = true
    taskStatus.value = 'PENDING'
    taskStatistics.value = null

    pollInterval.value = setInterval(async () => {
      try {
        const response = await api.get(`/tasks/${taskId}`)
        taskStatus.value = response.status

        if (response.status === 'SUCCESS') {
          taskResult.value = response.result
          taskStatistics.value = response.statistics
          stopPolling()
          if (onSuccess) onSuccess(response.statistics)
        } else if (response.status === 'FAILURE' || response.status === 'REVOKED') {
          stopPolling()
          // Pass the error result to the error handler
          if (onError) {
            onError(response.result)
          } else {
            // Default error handling
            const errorMsg = response.result?.message || '任务执行失败'
            ElMessage.error(errorMsg)
          }
        }
      } catch (error) {
        console.error('Task polling error:', error)
        stopPolling()
        if (onError) onError(error)
      }
    }, 2000) // Poll every 2 seconds
  }

  onUnmounted(() => {
    stopPolling()
  })

  return {
    taskStatus,
    isPolling,
    taskResult,
    taskStatistics,
    startPolling,
    stopPolling
  }
}
