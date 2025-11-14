# 异步文件处理系统设置指南

## 🚀 快速开始

### 1. 启动服务

首先确保以下服务已启动：

#### PostgreSQL 数据库
```bash
# 如果使用Docker
docker run --name postgres-aicg \
  -e POSTGRES_DB=aicg_platform \
  -e POSTGRES_USER=aicg_user \
  -e POSTGRES_PASSWORD=aicg_password \
  -p 5432:5432 \
  -d postgres:15

# 或使用系统安装的PostgreSQL
sudo systemctl start postgresql
```

#### Redis 消息队列
```bash
# 如果使用Docker
docker run --name redis-aicg -p 6379:6379 -d redis:7-alpine

# 或使用系统安装的Redis
redis-server
```

#### MinIO 对象存储
```bash
# 如果使用Docker
docker run --name minio-aicg \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  -v /tmp/minio-data:/data \
  minio/minio server /data --console-address ":9001"
```

### 2. 配置环境变量

创建 `.env` 文件：
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://aicg_user:aicg_password@localhost:5432/aicg_platform

# Redis配置
REDIS_URL=redis://localhost:6379/0

# Celery配置
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# MinIO配置
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false

# 应用配置
DEBUG=true
SECRET_KEY=your-secret-key-here
```

### 3. 初始化数据库

```bash
cd backend

# 运行数据库迁移
alembic upgrade head

# 或在开发环境创建表
python -c "
import asyncio
from src.core.database import initialize_database
asyncio.run(initialize_database())
"
```

### 4. 启动Celery Worker

```bash
# 启动Celery Worker（文件处理）
# 注意：Celery worker启动时会自动初始化数据库引擎
celery -A src.tasks.file_processing worker --loglevel=info --concurrency=4

# 启动Celery Beat（定时任务，可选）
celery -A src.tasks.file_processing beat --loglevel=info
```

**重要提示**：
- Celery worker启动时会自动初始化数据库引擎
- 如果看到"数据库引擎初始化失败"错误，请检查数据库配置
- 每个worker进程共享同一个数据库引擎，提高性能

### 5. 启动API服务

```bash
# 开发模式
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# 或生产模式
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## 📝 使用示例

### 创建项目并提交文件处理任务

```python
import requests
import json

# 1. 创建项目
project_data = {
    "title": "我的测试项目",
    "description": "测试异步文件处理功能",
    "file_name": "test_document.txt"
}

response = requests.post(
    "http://localhost:8000/api/v1/projects/",
    json=project_data,
    headers={"Authorization": "Bearer your-jwt-token"}
)

project = response.json()
project_id = project["id"]

# 2. 上传文件并启动处理
files = {"file": open("test_document.txt", "rb")}
response = requests.post(
    f"http://localhost:8000/api/v1/projects/{project_id}/upload/",
    files=files,
    headers={"Authorization": "Bearer your-jwt-token"}
}

upload_result = response.json()
print(f"任务ID: {upload_result['task_id']}")
```

### 查询处理状态

```python
# 查询处理状态
response = requests.get(
    f"http://localhost:8000/api/v1/projects/{project_id}/status/",
    headers={"Authorization": "Bearer your-jwt-token"}
)

status = response.json()
print(f"处理状态: {status['status']}")
print(f"进度: {status['processing_progress']}%")
print(f"章节数: {status['chapters_count']}")
print(f"段落数: {status['paragraphs_count']}")
print(f"句子数: {status['sentences_count']}")
```

### 重试失败的任务

```python
# 如果任务失败，可以重试
response = requests.post(
    f"http://localhost:8000/api/v1/projects/{project_id}/retry/",
    headers={"Authorization": "Bearer your-jwt-token"}
)

retry_result = response.json()
print(f"重试任务ID: {retry_result['task_id']}")
```

## 🔧 开发和调试

### 查看Celery任务状态

```bash
# 查看活跃任务
celery -A src.tasks.file_processing inspect active

# 查看已注册任务
celery -A src.tasks.file_processing inspect registered

# 查看任务统计
celery -A src.tasks.file_processing inspect stats
```

### 监控日志

```bash
# 查看Worker日志
tail -f celery_worker.log

# 或实时查看
celery -A src.tasks.file_processing worker --loglevel=debug
```

### 测试单个任务

```python
from src.tasks.file_processing import process_uploaded_file

# 直接调用任务（用于测试）
result = process_uploaded_file.apply(
    args=["project-123", "user-456"],
    kwargs={"file_path": "/path/to/file.txt"}
).get()

print(f"处理结果: {result}")
```

### 健康检查

```python
from src.tasks.file_processing import health_check

# 检查系统健康状态
health = health_check.apply().get()
print(f"系统状态: {health}")
```

## ⚠️ 常见问题

### 1. 数据库连接失败
```bash
# 检查数据库配置
echo $DATABASE_URL

# 测试数据库连接
python -c "
import asyncio
from src.core.database import test_database_connection
print('数据库连接:', asyncio.run(test_database_connection()))
"
```

### 2. Redis连接失败
```bash
# 检查Redis状态
redis-cli ping

# 检查Celery连接
celery -A src.tasks.file_processing inspect ping
```

### 3. 任务执行失败
```bash
# 查看详细错误信息
celery -A src.tasks.file_processing worker --loglevel=error

# 检查任务配置
celery -A src.tasks.file_processing conf
```

### 4. 内存使用过高
```bash
# 降低Worker并发数
celery -A src.tasks.file_processing worker --concurrency=2 --loglevel=info

# 设置任务超时
celery -A src.tasks.file_processing worker --task-time-limit=300 --loglevel=info
```

## 📊 性能优化

### 1. 数据库连接池配置

在 `src/core/config.py` 中调整：
```python
# 增加连接池大小
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
```

### 2. Celery Worker配置

```bash
# 增加Worker进程数
celery -A src.tasks.file_processing worker --concurrency=8

# 设置预取数量
celery -A src.tasks.file_processing worker --prefetch-multiplier=1
```

### 3. 任务优先级

```python
from celery import current_app

@current_app.task(bind=True, name='high_priority_process', priority=9)
def high_priority_process(self, project_id: str):
    # 高优先级任务
    pass
```

## 🔍 监控和维护

### 1. 使用Flower监控Celery

```bash
# 安装Flower
pip install flower

# 启动Flower
celery -A src.tasks.file_processing flower --port=5555

# 访问监控界面
open http://localhost:5555
```

### 2. 数据库性能监控

```python
from src.core.database import get_database_stats

stats = asyncio.run(get_database_stats())
print(f"数据库统计: {stats}")
```

### 3. 清理过期任务

```bash
# 清理过期任务结果
celery -A src.tasks.file_processing purge

# 设置任务结果过期时间（秒）
celery -A src.tasks.file_processing worker --task-result-expires=3600
```

## 📚 API文档

启动API服务后，可以访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🆘 故障排除

如果遇到问题，请按以下步骤排查：

1. **检查服务状态**：确保所有依赖服务运行正常
2. **查看日志**：检查应用和Celery日志
3. **验证配置**：确认环境变量配置正确
4. **测试连接**：使用健康检查工具测试各组件
5. **查看任务**：使用Celery inspect命令检查任务状态

需要更多帮助，请查看项目文档或提交Issue。