import { ref, computed } from 'vue'
import { videoTasksAPI } from '@/services/videoTasks'
import { ElMessage } from 'element-plus'

export function useVideoTasks() {
    const tasks = ref([])
    const total = ref(0)
    const loading = ref(false)
    const currentTask = ref(null)
    const stats = ref({
        total: 0,
        pending: 0,
        processing: 0,
        completed: 0,
        failed: 0,
        success_rate: 0
    })

    // 获取任务列表
    const fetchTasks = async (params = {}) => {
        loading.value = true
        try {
            const response = await videoTasksAPI.list(params)
            tasks.value = response.tasks
            total.value = response.total
            return response
        } catch (error) {
            console.error('获取视频任务列表失败:', error)
            ElMessage.error('获取视频任务列表失败')
            throw error
        } finally {
            loading.value = false
        }
    }

    // 获取单个任务详情
    const fetchTaskById = async (id) => {
        try {
            const task = await videoTasksAPI.getById(id)
            currentTask.value = task
            return task
        } catch (error) {
            console.error('获取视频任务详情失败:', error)
            ElMessage.error('获取视频任务详情失败')
            throw error
        }
    }

    // 创建任务
    const createTask = async (data) => {
        try {
            const task = await videoTasksAPI.create(data)
            ElMessage.success('视频生成任务已提交')
            // 刷新统计数据
            fetchStats()
            return task
        } catch (error) {
            console.error('创建视频任务失败:', error)
            ElMessage.error('创建视频任务失败: ' + (error.response?.data?.detail || error.message))
            throw error
        }
    }

    // 删除任务
    const deleteTask = async (id) => {
        try {
            await videoTasksAPI.delete(id)
            ElMessage.success('任务删除成功')
            // 重新获取列表以确保数据一致性
            await fetchTasks()
            // 刷新统计数据
            fetchStats()
        } catch (error) {
            console.error('删除视频任务失败:', error)
            ElMessage.error('删除视频任务失败: ' + (error.response?.data?.detail || error.message))
            throw error
        }
    }

    // 重试任务
    const retryTask = async (id) => {
        try {
            const response = await videoTasksAPI.retry(id)
            ElMessage.success('任务已重新提交')
            // 更新列表中的状态
            const index = tasks.value.findIndex(t => t.id === id)
            if (index !== -1) {
                tasks.value[index] = response.task
            }
            // 刷新统计数据
            fetchStats()
            return response.task
        } catch (error) {
            console.error('重试视频任务失败:', error)
            ElMessage.error('重试视频任务失败: ' + (error.response?.data?.detail || error.message))
            throw error
        }
    }

    // 获取统计数据
    const fetchStats = async () => {
        try {
            const data = await videoTasksAPI.getStats()
            stats.value = data
            return data
        } catch (error) {
            console.error('获取任务统计失败:', error)
            // 不显示错误消息，以免干扰主流程
        }
    }

    // 轮询任务状态
    let pollTimer = null
    const startPolling = (interval = 3000, params = {}) => {
        stopPolling()
        pollTimer = setInterval(async () => {
            // 如果正在加载中，跳过这次轮询
            if (loading.value) return

            try {
                // 静默更新列表，不显示loading
                const response = await videoTasksAPI.list(params)

                // 智能更新：只更新有变化的项，避免UI闪烁
                response.tasks.forEach(newTask => {
                    const index = tasks.value.findIndex(t => t.id === newTask.id)
                    if (index !== -1) {
                        // 如果状态或进度有变化，则更新
                        if (tasks.value[index].status !== newTask.status ||
                            tasks.value[index].progress !== newTask.progress) {
                            tasks.value[index] = newTask
                        }
                    } else {
                        // 新任务，添加到列表头部（假设按时间倒序）
                        tasks.value.unshift(newTask)
                    }
                })

                // 更新统计
                fetchStats()
            } catch (error) {
                console.error('轮询更新失败:', error)
                // 连续失败多次可以考虑停止轮询
            }
        }, interval)
    }

    const stopPolling = () => {
        if (pollTimer) {
            clearInterval(pollTimer)
            pollTimer = null
        }
    }

    return {
        tasks,
        total,
        loading,
        currentTask,
        stats,
        fetchTasks,
        fetchTaskById,
        createTask,
        deleteTask,
        retryTask,
        fetchStats,
        startPolling,
        stopPolling
    }
}
