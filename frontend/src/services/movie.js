import { get, post, put } from './api'

export const movieService = {
    /**
     * 为章节启动剧本生成任务
     */
    generateScript(chapterId, data) {
        return post(`/movie/chapters/${chapterId}/script`, data)
    },

    /**
     * 获取章节关联的剧本详情
     */
    getScript(chapterId) {
        return get(`/movie/chapters/${chapterId}/script`)
    },

    /**
     * 从剧本中提取角色
     */
    extractCharacters(scriptId, data) {
        return post(`/movie/scripts/${scriptId}/extract-characters`, data)
    },

    /**
     * 获取项目下的角色列表
     */
    getCharacters(projectId) {
        return get(`/movie/projects/${projectId}/characters`)
    },

    /**
     * 启动分镜视频生产
     */
    produceShot(shotId, data) {
        return post(`/movie/shots/${shotId}/produce`, data)
    },

    /**
     * 生成角色头像
     */
    generateCharacterAvatar(characterId, data) {
        return post(`/movie/characters/${characterId}/generate`, data)
    },

    /**
     * 为剧本批量生成分镜首帧
     */
    generateKeyframes(scriptId, data) {
        return post(`/movie/scripts/${scriptId}/generate-keyframes`, data)
    },

    /**
     * 批量启动分镜视频生产
     */
    batchProduceVideos(scriptId, data) {
        return post(`/movie/scripts/${scriptId}/batch-produce`, data)
    },

    /**
     * 重新生成单个分镜首帧
     */
    regenerateKeyframe(shotId, data) {
        return post(`/movie/shots/${shotId}/regenerate-keyframe`, data)
    },

    /**
     * 重新生成单个分镜尾帧
     */
    regenerateLastFrame(shotId, data) {
        return post(`/movie/shots/${shotId}/regenerate-last-frame`, data)
    },

    /**
     * 重新生成单个分镜视频
     */
    regenerateVideo(shotId, data) {
        return post(`/movie/shots/${shotId}/regenerate-video`, data)
    },

    /**
     * 检查剧本完成度
     */
    checkScriptCompletion(scriptId) {
        return get(`/movie/scripts/${scriptId}/completion-status`)
    },

    /**
     * 准备章节素材（推进状态）
     */
    prepareChapterMaterials(chapterId) {
        return post(`/movie/chapters/${chapterId}/prepare-materials`)
    },

    /**
     * 更新分镜信息
     */
    updateShot(shotId, data) {
        return put(`/movie/shots/${shotId}`, data)
    }
}

export default movieService
