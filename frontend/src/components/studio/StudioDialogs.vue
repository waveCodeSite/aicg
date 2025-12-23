<template>
  <div>
    <!-- 生成配置对话框 -->
    <el-dialog
      :model-value="visible"
      @update:model-value="(val) => $emit('update:visible', val)"
      :title="title"
      width="500px"
      destroy-on-close
    >
      <el-form :model="genConfig" label-width="100px">
        <el-form-item label="API Key" v-if="!genConfig.api_key_id">
            <el-select 
              :model-value="genConfig.api_key_id" 
              @update:model-value="(val) => $emit('update:genConfig', { ...genConfig, api_key_id: val })"
              placeholder="请选择 API Key" 
              style="width: 100%"
            >
              <el-option v-for="k in apiKeys" :key="k.id" :label="k.name" :value="k.id" />
            </el-select>
        </el-form-item>
        
        <el-form-item label="画面风格" v-if="['avatar', 'keyframes', 'regen-keyframe', 'regen-last-frame'].includes(mode)">
          <el-select 
            :model-value="genConfig.style" 
            @update:model-value="(val) => $emit('update:genConfig', { ...genConfig, style: val })"
            placeholder="选择风格"
          >
            <el-option label="电影质感 (Cinematic)" value="cinematic" />
            <el-option label="日漫风格 (Anime)" value="anime" />
            <el-option label="赛博朋克 (Cyberpunk)" value="cyberpunk" />
            <el-option label="油画风格 (Oil Painting)" value="oil_painting" />
          </el-select>
        </el-form-item>

        <el-form-item label="提示词" v-if="mode === 'avatar'">
          <el-input 
            :model-value="genConfig.prompt" 
            @update:model-value="(val) => $emit('update:genConfig', { ...genConfig, prompt: val })"
            type="textarea" 
            :rows="6" 
            placeholder="生成形象的提示词"
          />
        </el-form-item>

        <el-form-item label="选择模型">
          <el-select 
            :model-value="genConfig.model" 
            @update:model-value="(val) => $emit('update:genConfig', { ...genConfig, model: val })"
            placeholder="请选择或输入模型" 
            filterable 
            allow-create 
            :loading="loadingModels"
            style="width: 100%"
          >
            <el-option v-for="model in modelOptions" :key="model" :label="model" :value="model" />
          </el-select>
        </el-form-item>

        <!-- BGM选择 (仅视频生成时显示) -->
        <el-form-item label="背景音乐" v-if="mode === 'generate-video'">
          <el-select 
            :model-value="genConfig.background_id" 
            @update:model-value="(val) => $emit('update:genConfig', { ...genConfig, background_id: val })"
            placeholder="选择BGM(可选)" 
            clearable
            style="width: 100%"
          >
            <el-option label="无背景音乐" :value="null" />
            <!-- TODO: 从BGM列表加载 -->
          </el-select>
        </el-form-item>

        <el-form-item label="BGM音量" v-if="mode === 'generate-video' && genConfig.background_id">
          <el-slider 
            :model-value="genConfig.bgm_volume || 0.15" 
            @update:model-value="(val) => $emit('update:genConfig', { ...genConfig, bgm_volume: val })"
            :min="0" 
            :max="1" 
            :step="0.05"
            show-input
            :input-size="'small'"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="$emit('update:visible', false)">取消</el-button>
          <el-button type="primary" @click="$emit('confirm')" :loading="loading">
            {{ confirmText }}
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
const props = defineProps({
  visible: Boolean,
  mode: String,
  genConfig: Object,
  apiKeys: Array,
  modelOptions: Array,
  loadingModels: Boolean,
  loading: Boolean
})

const emit = defineEmits(['update:visible', 'update:genConfig', 'confirm'])

const getDialogTitle = () => {
  const titles = {
    'script': '剧本适配配置',
    'character': '角色提取配置',
    'keyframes': '批量生成首尾帧图',
    'produce-single': '生成分镜视频',
    'produce-batch': '批量生成视频',
    'generate-video': '生成章节视频',
    'regen-keyframe': '生成/重置首帧',
    'regen-last-frame': '生成/重置尾帧',
    'regen-video': '重新生成视频',
    'avatar': '角色形象生成'
  }
  return titles[props.mode] || '配置'
}

const getConfirmText = () => {
  const texts = {
    'script': '开始生成',
    'character': '开始提取',
    'keyframes': '开始批量绘图',
    'produce-single': '开始制作',
    'produce-batch': '开始制作',
    'generate-video': '开始生成',
    'regen-keyframe': '开始制作',
    'regen-last-frame': '开始制作',
    'regen-video': '开始制作',
    'avatar': '开始绘图'
  }
  return texts[props.mode] || '确定'
}

import { computed } from 'vue'
const title = computed(() => getDialogTitle())
const confirmText = computed(() => getConfirmText())
</script>
