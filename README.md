# AICG 内容分发平台

> 🎬 **AI驱动的智能内容创作与分发平台** - 从文字到视频，一站式AI内容生产解决方案

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Vue](https://img.shields.io/badge/vue-3.x-green.svg)](https://vuejs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-latest-009688.svg)](https://fastapi.tiangolo.com/)

## 🌟 核心亮点

### 🎥 AI电影工作室 - 重磅功能

**从文字到电影，全自动AI电影生成流水线**

- **📝 智能剧本解析** - 自动提取场景、分镜、角色，构建完整电影结构
- **🎨 角色定妆照生成** - AI生成一致性角色形象，支持多视角参考图
- **🖼️ 场景图生成** - 为每个场景生成氛围图，确保视觉连贯性
- **🎞️ 关键帧生成** - 智能生成分镜关键帧，支持前后帧参考保持连续性
- **🎬 过渡视频生成** - 自动生成分镜间过渡视频，实现流畅衔接
- **📜 生成历史管理** - 记录所有生成版本，支持历史版本切换和对比
- **🔄 智能提示词重生成** - 使用LLM自动优化视频生成提示词
- **🎵 BGM配乐** - 智能配乐系统，为电影添加背景音乐
- **📦 一键合成** - 自动合成所有素材，输出完整电影

**工作流程**：
```
文字剧本 → 角色提取 → 场景分析 → 分镜生成 → 
关键帧渲染 → 过渡视频 → BGM配乐 → 最终合成 → 完整电影
```

### 🎨 AI图文说内容生成

**传统图文说视频制作的智能化升级**

- **📖 智能分段** - 自动将长文本分割为适合视频的段落
- **🎯 AI导演引擎** - 智能生成每个段落的视觉提示词
- **🖼️ 批量图片生成** - 支持多种AI模型，批量生成配图
- **🎙️ 智能配音** - 文字转语音，支持多种音色和语速
- **🎬 自动合成** - 图片、配音、字幕自动合成为视频

### 📺 B站一键发布

- **🚀 自动上传** - 视频自动上传到B站
- **📝 智能标题** - AI生成吸引人的标题和简介
- **🏷️ 标签推荐** - 智能推荐相关标签
- **📊 发布管理** - 统一管理所有发布任务

## 🏗️ 技术架构

### 后端技术栈

- **框架**: FastAPI + SQLAlchemy + Alembic
- **数据库**: PostgreSQL
- **任务队列**: Celery + Redis
- **存储**: MinIO (S3兼容)
- **AI集成**: 
  - 文本生成: OpenAI GPT / Google Gemini
  - 图片生成: Stable Diffusion / DALL-E / Gemini
  - 视频生成: VectorEngine / Runway
  - 语音合成: Azure TTS / 其他TTS服务

### 前端技术栈

- **框架**: Vue 3 + Vite
- **UI库**: Element Plus
- **状态管理**: Pinia
- **路由**: Vue Router
- **HTTP客户端**: Axios

### 核心特性

- ✅ **异步任务处理** - Celery分布式任务队列
- ✅ **实时状态追踪** - WebSocket实时更新
- ✅ **模块化设计** - 清晰的代码结构和职责分离
- ✅ **RESTful API** - 标准化的API设计
- ✅ **数据库迁移** - Alembic版本控制
- ✅ **对象存储** - MinIO文件管理
- ✅ **多模型支持** - 灵活切换不同AI服务商

## 📁 项目结构

```
aicon2/
├── backend/                 # 后端服务
│   ├── src/
│   │   ├── api/            # API路由和端点
│   │   │   ├── v1/         # API v1版本
│   │   │   │   ├── movie_*.py    # 电影生成相关API
│   │   │   │   ├── generation_history.py  # 生成历史API
│   │   │   │   └── ...
│   │   │   └── schemas/    # Pydantic数据模型
│   │   ├── models/         # SQLAlchemy数据模型
│   │   ├── services/       # 业务逻辑层
│   │   │   ├── movie.py           # 电影服务
│   │   │   ├── generation_history_service.py
│   │   │   └── ...
│   │   ├── tasks/          # Celery异步任务
│   │   ├── core/           # 核心配置
│   │   └── utils/          # 工具函数
│   ├── migrations/         # 数据库迁移
│   └── tests/             # 测试文件
│
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── views/         # 页面组件
│   │   │   └── studio/    # 电影工作室
│   │   ├── components/    # 可复用组件
│   │   │   └── studio/    # 工作室组件
│   │   ├── composables/   # Vue组合式函数
│   │   ├── services/      # API服务
│   │   ├── stores/        # Pinia状态管理
│   │   └── utils/         # 工具函数
│   └── public/            # 静态资源
│
└── docs/                  # 项目文档
    ├── movie_generation_workflow.md  # 电影生成流程文档
    └── ...
```

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- PostgreSQL 14+
- Redis 6+
- MinIO (或其他S3兼容存储)

### 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，配置数据库、Redis、MinIO等

# 运行数据库迁移
alembic upgrade head

# 启动后端服务
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 启动Celery Worker（新终端）
celery -A src.tasks.app worker --loglevel=info
```

### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 `http://localhost:3000` 即可使用系统。

## 🎯 主要功能模块

### 1. 项目管理
- 创建和管理内容项目
- 支持文本导入和在线编辑
- 项目版本控制

### 2. 电影工作室
- **角色管理**: 提取角色、生成定妆照
- **场景管理**: 场景提取、场景图生成
- **分镜管理**: 分镜提取、关键帧生成
- **过渡视频**: 创建过渡、生成视频、提示词优化
- **素材检查**: 自动检查所有素材完整性
- **电影合成**: 一键合成完整电影

### 3. 图文说工作室
- 段落分割和管理
- 批量图片生成
- 配音生成
- 视频合成

### 4. API密钥管理
- 支持多个AI服务商
- 密钥安全存储
- 使用统计

### 5. 视频任务管理
- 任务列表和状态追踪
- 失败重试
- 批量操作

### 6. B站发布
- 视频上传
- 元数据编辑
- 发布状态管理

## 🔧 配置说明

### 环境变量

主要环境变量配置（`.env`文件）：

```env
# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/aicg

# Redis配置
REDIS_URL=redis://localhost:6379/0

# MinIO配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=aicg-platform

# AI服务配置
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key

# 应用配置
SECRET_KEY=your-secret-key
DEBUG=true
```

## 📊 数据库设计

### 核心表结构

- **projects** - 项目信息
- **chapters** - 章节管理
- **movie_scripts** - 电影剧本
- **movie_scenes** - 场景信息
- **movie_shots** - 分镜信息
- **movie_characters** - 角色信息
- **movie_shot_transitions** - 过渡视频
- **movie_generation_history** - 生成历史记录（统一表）
- **video_tasks** - 视频任务
- **api_keys** - API密钥

## 🎨 生成历史功能

系统为所有生成内容提供完整的历史记录管理：

- **版本追踪**: 记录每次生成的结果
- **历史切换**: 随时切换到任意历史版本
- **提示词记录**: 保存每次生成使用的提示词
- **模型信息**: 记录使用的AI模型
- **时间戳**: 完整的生成时间记录

支持的资源类型：
- 场景图 (scene_image)
- 关键帧 (shot_keyframe)
- 角色头像 (character_avatar)
- 过渡视频 (transition_video)

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出新功能建议！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 开发日志

### v2.0.0 - AI电影工作室 (2025-12-29)

**🎬 重磅更新：AI电影生成功能**

- ✨ 完整的电影生成工作流
- ✨ 角色、场景、分镜智能提取
- ✨ 关键帧和过渡视频生成
- ✨ 生成历史管理系统
- ✨ LLM驱动的提示词优化
- ✨ 一键电影合成

### v1.0.0 - 基础功能 (2024)

- 🎨 图文说视频生成
- 📺 B站自动发布
- 🔑 API密钥管理
- 📊 任务管理系统

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

感谢以下开源项目和服务：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的Python Web框架
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
- [Element Plus](https://element-plus.org/) - Vue 3 UI组件库
- [Celery](https://docs.celeryq.dev/) - 分布式任务队列
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python ORM
- [MinIO](https://min.io/) - 高性能对象存储

以及所有AI服务提供商：OpenAI、Google、Azure等

## 📧 联系方式

- 项目主页: [GitHub](https://github.com/869413421/aicon2)
- 问题反馈: [Issues](https://github.com/869413421/aicon2/issues)

---

⭐ 如果这个项目对你有帮助，请给个Star支持一下！