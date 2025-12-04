# AICG 内容分发平台

AI 驱动的智能内容创作与分发平台，致力于将长文本自动转换为高质量的**图解说视频**。

## 🌟 核心特性

- **智能解析**: 自动解析百万字级长篇小说，提取角色、场景和对话。
- **图解说生成**: 
  - 🎨 **AI 绘画**: 集成 Flux、SDXL 等多模型，支持风格定制。
  - 🗣️ **AI 配音**: 支持多种 TTS 引擎，情感丰富。
  - 🎬 **自动合成**: 智能匹配画面与语音，自动生成字幕。
- **高效工作流**:
  - 🚀 **异步处理**: 全链路异步架构，支持高并发任务。
  - 💾 **智能缓存**: 视频生成增量更新，避免重复计算。

## 🔮 未来规划

- **智能运镜**: 电影级镜头语言，自动生成运镜脚本。
- **可视化编排**: 所见即所得的导演模式，精细控制每一帧。
- **多平台分发**: 一键发布到主流视频平台。

## 📚 子项目文档

- [**后端服务 (Backend)**](./backend/README.md): 基于 FastAPI 的核心业务服务。
- [**前端应用 (Frontend)**](./frontend/README.md): 基于 Vue 3 + Element Plus 的现代化管理界面。

## 🚀 快速开始

### 1. 启动基础设施
```bash
./scripts/start.sh
```

### 2. 本地开发
```bash
# 后端
cd backend
uv sync
alembic upgrade head
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev
```

### 3. 访问服务
- 前端页面: http://localhost:5173
- API 文档: http://localhost:8000/docs
- MinIO 控制台: http://localhost:9001 (minioadmin/minioadmin)

## 📁 项目结构
```
aicon2/
├── README.md              # 项目总览
├── backend/               # Python/FastAPI 后端
├── frontend/              # Vue.js 前端
├── scripts/               # 运维脚本
├── docker-compose.yml     # 基础设施编排
└── .env.example           # 环境变量模板
```

## ⚙️ 环境配置
```bash
cp .env.example .env
# 编辑 .env 配置数据库和Redis连接
```

## 🔧 常用命令
```bash
# 启动/停止基础设施
docker-compose up -d
docker-compose down

# 查看日志
docker-compose logs -f
```