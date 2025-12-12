# 🎬 AICG - AI驱动的智能视频创作平台

<div align="center">

**将长文本自动转换为高质量图文解说视频的一站式解决方案**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Node](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.3+-4FC08D.svg)](https://vuejs.org/)

[功能演示](#-产品演示) • [功能特性](#-核心功能) • [快速开始](#-快速开始) • [文档](#-文档)

</div>

---

## 📺 产品演示

<div align="center">

### 完整工作流程展示

#### 1️⃣ 项目管理与章节识别
![项目管理](docs/media/1.gif)
*上传文档 → 智能章节识别 → 可视化编辑*

#### 2️⃣ 导演引擎 - 批量生成素材
![导演引擎](docs/media/2.gif)
*批量生成提示词 → AI绘画 → TTS配音 → 实时预览*

#### 3️⃣ 单句精细调整
![单句调整](docs/media/3.gif)
*查看句子详情 → 重新生成 → 替换素材*

#### 4️⃣ 视频合成与配置
![视频合成](docs/media/4.gif)
*配置参数 → 选择BGM → 一键生成视频*

---

### 🎥 成果展示

**使用本项目生成的实际视频作品**：

[![B站视频](https://img.shields.io/badge/B站-观看成果视频-00A1D6?logo=bilibili&logoColor=white)](https://www.bilibili.com/video/BV1PgmjBqE7F)

> 点击上方链接观看使用AICG平台生成的完整视频作品，体验从文本到视频的全自动化流程效果。

</div>

---

## 🌟 项目亮点

### 💰 极致性价比
通过灵活的第三方API集成，实现**低至0.04元/张图片**的成本控制，让视频创作不再昂贵。

### 🎯 全自动化流程
从文本上传到视频生成，**一键完成**：
- 📝 智能章节识别
- 🎨 AI图片生成
- 🗣️ 情感化语音合成
- 🎬 自动视频剪辑
- 📊 精准字幕同步

### ⚡ 高效异步架构
基于Celery的异步任务处理，支持：
- 🚀 高并发批量生成
- 💾 智能增量缓存
- 📈 实时进度追踪
- 🔄 断点续传

### 🎛️ 专业级视频控制
- **Ken Burns效果**：动态缩放和平移
- **BGM混合**：可配置音量的背景音乐
- **视频加速**：0.5x-2.0x速度调整
- **LLM字幕纠错**：智能修正识别错误
- **多分辨率支持**：竖屏/横屏/方形

---

## ✨ 核心功能

### 📚 智能内容管理

<table>
<tr>
<td width="50%">

#### 📝 文本导入项目 🆕
- ✅ 支持TXT、DOCX、PDF、EPUB等多格式
- ✅ 智能章节识别与解析
- ✅ 可视化章节编辑器
- ✅ 章节合并/拆分/忽略
- ✅ 实时预览与调整

</td>
<td width="50%">

#### 🎯 导演引擎（Director Engine）
- ✅ 批量生成提示词
- ✅ 批量生成图片
- ✅ 批量生成音频
- ✅ 单句精细调整
- ✅ 素材预览与替换

</td>
</tr>
</table>

### 🎨 AI素材生成

<table>
<tr>
<td width="33%">

#### 🖼️ 图片生成
- Flux系列模型
- SDXL系列模型
- Sora_Image（低成本）
- 自定义模型支持
- 风格一致性控制

</td>
<td width="33%">

#### 🎤 语音合成
- 硅基流动 index-tts2
- 情感丰富的中文配音
- 多种音色选择
- 自然语音节奏
- 高保真音质

</td>
<td width="33%">

#### 🤖 LLM集成
- GPT-4o系列
- Claude 3.5系列
- DeepSeek系列
- 自定义模型
- 字幕智能纠错

</td>
</tr>
</table>

### 🎬 专业视频合成

| 功能 | 说明 | 配置项 |
|------|------|--------|
| **分辨率** | 竖屏(9:16)、横屏(16:9)、方形(1:1) | ✅ 可配置 |
| **帧率** | 24/30/60 FPS | ✅ 可配置 |
| **Ken Burns效果** | 动态缩放+平移，电影级运镜 | ✅ 可配置速度 |
| **字幕样式** | 字体大小、颜色、位置 | ✅ 可配置 |
| **BGM混合** | 背景音乐自动循环与混合 | ✅ 可配置音量(0-50%) |
| **视频加速** | 0.5x-2.0x速度调整，保持音调 | ✅ 可配置 |
| **LLM纠错** | 智能修正字幕错别字 | ✅ 可选启用 |

### 📤 导出与发布 🆕

<table>
<tr>
<td width="33%">

#### 🎬 剪映素材导出
- ✅ 一键导出剪映草稿格式
- ✅ 包含所有图片和音频素材
- ✅ 支持直接导入剪映专业版

</td>
<td width="33%">

#### 📺 B站账号管理
- ✅ 扫码登录B站账号
- ✅ 多账号管理
- ✅ Cookie自动维护
- ✅ 登录状态监控

</td>
<td width="33%">

#### 🚀 B站稿件发布
- ✅ 视频一键发布到B站
- ✅ 自定义分区、标签、封面
- ✅ 发布状态追踪

</td>
</tr>
</table>

### 🔐 API密钥管理

- ✅ 多供应商支持（OpenAI、Anthropic、硅基流动、自定义）
- ✅ 多密钥配置与切换
- ✅ 密钥状态监控
- ✅ 用量统计（即将推出）

---

## 🚀 快速开始

### 📋 前置要求

| 工具 | 版本要求 | 说明 |
|------|---------|------|
| **Node.js** | >= 18.0.0 | 前端运行环境 |
| **Python** | >= 3.11 | 后端运行环境 |
| **uv** | 最新版 | Python包管理器 |
| **FFmpeg** | 最新版 | 视频处理核心 |
| **Docker** | 最新版 | 基础设施服务 |

### 🔑 API平台注册

本项目依赖第三方AI模型，需要注册以下平台：

1. **[推荐] 硅基流动** (TTS/大模型)
   - 注册链接：[https://cloud.siliconflow.cn/i/63zI7Mdc](https://cloud.siliconflow.cn/i/63zI7Mdc)
   - 用途：高质量中文TTS、大模型服务

2. **[低成本] 第三方中转平台** (Sora_Image)
   - 注册链接：[https://api.vectorengine.ai/register?aff=YVx7](https://api.vectorengine.ai/register?aff=YVx7)
   - 用途：低成本图片生成（约0.04元/张）

### 📦 快速安装

```bash
# 1. 克隆项目
git clone https://github.com/869413421/aicon2.git
cd aicon2

# 2. 配置环境变量
cp .env.example .env
# 编辑.env文件，填入必要配置

# 3. 启动基础设施（PostgreSQL, Redis, MinIO）
docker-compose up -d

# 4. 启动后端
cd backend
uv sync
alembic upgrade head
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 5. 启动Celery Worker（新终端）
cd backend
uv run celery -A src.tasks.task worker --loglevel=info

# 6. 启动前端（新终端）
cd frontend
npm install
npm run dev
```

### ✅ 验证安装

访问以下地址确认服务正常:

- 🌐 **前端应用**: http://localhost:3000
- 📚 **API文档**: http://localhost:8000/docs
- 📦 **MinIO控制台**: http://localhost:9001 (minioadmin/minioadmin123)

---

## 🏗️ 技术架构

### 后端技术栈

```
FastAPI + SQLAlchemy + Celery + PostgreSQL + Redis + MinIO
```

- **FastAPI**: 高性能异步Web框架
- **SQLAlchemy**: ORM与数据库管理
- **Celery**: 分布式异步任务队列
- **PostgreSQL**: 主数据库
- **Redis**: 缓存与消息队列
- **MinIO**: 对象存储（图片、音频、视频）

### 前端技术栈

```
Vue 3 + Element Plus + Pinia + Vite
```

- **Vue 3**: 渐进式JavaScript框架
- **Element Plus**: 企业级UI组件库
- **Pinia**: 状态管理
- **Vite**: 下一代前端构建工具

---

## 📖 文档

- 📦 **[安装部署指南](docs/INSTALLATION.md)** - 详细的安装步骤、GPU加速配置、Bilibili工具配置
- 💻 **[开发指南](docs/DEVELOPMENT.md)** - 项目结构、开发环境、代码规范、测试指南
- ✨ **[功能详细说明](docs/FEATURES.md)** - 各功能模块的详细介绍和使用教程
- 📺 **[Bilibili集成方案](docs/bilibili_integration_plan.md)** - B站发布功能的技术方案

---

## 🎯 成本优化建议

### 推荐配置（极致性价比）

| 步骤 | 推荐服务 | 成本 |
|------|---------|------|
| **提示词生成** | GPT-4o-mini / DeepSeek | ~¥0.001/句 |
| **图片生成** | Sora_Image（中转平台） | ~¥0.04/张 |
| **语音合成** | 硅基流动 index-tts2 | ~¥0.02/句 |

**示例成本计算**（100句视频）：
- 提示词：100 × ¥0.001 = ¥0.1
- 图片：100 × ¥0.04 = ¥4.0
- 语音：100 × ¥0.02 = ¥2.0
- **总计：约¥6.1**

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

感谢以下开源项目和服务：

- [FastAPI](https://fastapi.tiangolo.com/)
- [Vue.js](https://vuejs.org/)
- [Element Plus](https://element-plus.org/)
- [FFmpeg](https://ffmpeg.org/)
- [Celery](https://docs.celeryq.dev/)
- [硅基流动](https://cloud.siliconflow.cn/)
- [biliup-rs](https://github.com/biliup/biliup-rs)

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个Star！**

Made with ❤️ by AICG Team

</div>