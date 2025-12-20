import { get, post } from './api'

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
    }
}

export default movieService
