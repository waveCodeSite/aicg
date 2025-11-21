import api from './api'

/**
 * 句子管理服务
 */
export const sentencesService = {
    /**
     * 获取段落的句子列表
     * @param {string} paragraphId 段落ID
     * @returns {Promise<Object>}
     */
    async getSentences(paragraphId) {
        // 使用新的嵌套路由获取句子列表
        return await api.get(`/sentences/paragraphs/${paragraphId}/sentences`)
    },

    /**
     * 创建新句子
     * @param {string} paragraphId 段落ID
     * @param {Object} data 句子数据 {content, order_index}
     * @returns {Promise<Object>}
     */
    async createSentence(paragraphId, data) {
        // 使用新的嵌套路由创建句子
        return await api.post(`/sentences/paragraphs/${paragraphId}/sentences`, data)
    },

    /**
     * 获取单个句子详情
     * @param {string} id 句子ID
     * @returns {Promise<Object>}
     */
    async getSentence(id) {
        return await api.get(`/sentences/${id}`)
    },

    /**
     * 更新句子
     * @param {string} id 句子ID
     * @param {Object} data 更新数据 {content}
     * @returns {Promise<Object>}
     */
    async updateSentence(id, data) {
        return await api.put(`/sentences/${id}`, data)
    },

    /**
     * 删除句子
     * @param {string} id 句子ID
     * @returns {Promise<Object>}
     */
    async deleteSentence(id) {
        return await api.delete(`/sentences/${id}`)
    }
}

export default sentencesService
