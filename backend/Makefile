# AICG内容分发平台 - 后端服务 Makefile
# 提供开发环境的快速启动和常用命令

.PHONY: help start migrate setup worker beat test lint clean format check install

# 默认目标
.DEFAULT_GOAL := help

# 颜色定义
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
GRAY := \033[90m
RESET := \033[0m

# 项目配置
PROJECT_NAME := aicg-platform-backend
PYTHON := python3
UV := uv
PORT := 8000
HOST := 0.0.0.0

help: ## 显示帮助信息
	@echo "$(BLUE)AICG平台后端服务 - 开发命令集合$(RESET)"
	@echo ""
	@echo "$(GREEN)核心命令:$(RESET)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(YELLOW)%-12s$(RESET) %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort
	@echo ""
	@echo "$(GREEN)示例:$(RESET)"
	@echo "  make setup     # 初始化开发环境"
	@echo "  make start     # 启动开发服务器"
	@echo "  make migrate   # 运行数据库迁移"

setup: ## 初始化开发环境 (安装依赖 + 数据库迁移)
	@echo "$(BLUE)🚀 初始化开发环境...$(RESET)"
	$(UV) sync
	@echo "$(GREEN)✅ 依赖安装完成$(RESET)"
	$(MAKE) migrate
	@echo "$(GREEN)🎉 开发环境初始化完成!$(RESET)"
	@echo ""
	@echo "$(YELLOW)现在可以运行以下命令启动服务:$(RESET)"
	@echo "  make start"

start: ## 启动开发服务器 (热重载)
	@echo "$(BLUE)🚀 启动开发服务器...$(RESET)"
	@echo "$(GREEN)📍 服务地址: http://$(HOST):$(PORT)$(RESET)"
	@echo "$(GREEN)📖 API文档: http://$(HOST):$(PORT)/docs$(RESET)"
	@echo "$(YELLOW)⚠️  确保先启动基础设施服务: cd .. && ./scripts/start.sh$(RESET)"
	@echo ""
	$(UV) run uvicorn src.main:app --reload --host $(HOST) --port $(PORT)

migrate: ## 运行数据库迁移
	@echo "$(BLUE)🔄 运行数据库迁移...$(RESET)"
	$(UV) run alembic upgrade head
	@echo "$(GREEN)✅ 数据库迁移完成$(RESET)"

migrate-create: ## 创建新的数据库迁移 (使用: make migrate-create MSG="描述")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)❌ 请提供迁移描述: make migrate-create MSG=\"添加用户表\"$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)📝 创建数据库迁移: $(MSG)$(RESET)"
	$(UV) run alembic revision --autogenerate -m "$(MSG)"
	@echo "$(GREEN)✅ 迁移文件创建完成$(RESET)"

migrate-down: ## 回滚最后一次数据库迁移
	@echo "$(YELLOW)⚠️  回滚数据库迁移...$(RESET)"
	$(UV) run alembic downgrade -1
	@echo "$(GREEN)✅ 迁移回滚完成$(RESET)"

worker: ## 启动Celery Worker
	@echo "$(BLUE)🔄 启动Celery Worker...$(RESET)"
	$(UV) run celery -A src.workers.base worker --loglevel=info --concurrency=4

beat: ## 启动Celery Beat (定时任务调度器)
	@echo "$(BLUE)⏰ 启动Celery Beat...$(RESET)"
	$(UV) run celery -A src.workers.base beat --loglevel=info

dev: ## 启动完整开发环境 (API + Worker + Beat)
	@echo "$(BLUE)🚀 启动完整开发环境...$(RESET)"
	@echo "$(YELLOW)需要在多个终端窗口中运行以下命令:$(RESET)"
	@echo ""
	@echo "$(GREEN)终端1 - API服务:$(RESET)"
	@echo "  make start"
	@echo ""
	@echo "$(GREEN)终端2 - Celery Worker:$(RESET)"
	@echo "  make worker"
	@echo ""
	@echo "$(GREEN)终端3 - Celery Beat:$(RESET)"
	@echo "  make beat"

test: ## 运行所有测试
	@echo "$(BLUE)🧪 运行测试...$(RESET)"
	$(UV) run pytest
	@echo "$(GREEN)✅ 测试完成$(RESET)"

test-unit: ## 运行单元测试
	@echo "$(BLUE)🧪 运行单元测试...$(RESET)"
	$(UV) run pytest -m unit

test-integration: ## 运行集成测试
	@echo "$(BLUE)🧪 运行集成测试...$(RESET)"
	$(UV) run pytest -m integration

test-fast: ## 运行快速测试 (排除慢速测试)
	@echo "$(BLUE)🏃 运行快速测试...$(RESET)"
	$(UV) run pytest -m "not slow" 

lint: ## 运行代码检查和格式化
	@echo "$(BLUE)🔍 代码检查和格式化...$(RESET)"
	$(MAKE) format
	$(MAKE) check

format: ## 格式化代码 (black + isort)
	@echo "$(BLUE)📝 格式化代码...$(RESET)"
	$(UV) run black src/ tests/
	$(UV) run isort src/ tests/
	@echo "$(GREEN)✅ 代码格式化完成$(RESET)"

check: ## 代码质量检查 (flake8 + mypy)
	@echo "$(BLUE)🔍 代码质量检查...$(RESET)"
	@echo "$(YELLOW)Flake8检查:$(RESET)"
	$(UV) run flake8 src/ tests/ || true
	@echo "$(YELLOW)MyPy检查:$(RESET)"
	$(UV) run mypy src/ || true
	@echo "$(GREEN)✅ 代码检查完成$(RESET)"

clean: ## 清理临时文件和缓存
	@echo "$(BLUE)🧹 清理项目...$(RESET)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage coverage.xml
	@echo "$(GREEN)✅ 清理完成$(RESET)"

install: ## 安装开发依赖
	@echo "$(BLUE)📦 安装开发依赖...$(RESET)"
	$(UV) sync --dev
	@echo "$(GREEN)✅ 依赖安装完成$(RESET)"

add: ## 添加新依赖 (使用: make add PACKAGE=fastapi)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "$(RED)❌ 请提供包名: make add PACKAGE=fastapi$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)📦 添加依赖: $(PACKAGE)$(RESET)"
	$(UV) add $(PACKAGE)

add-dev: ## 添加开发依赖 (使用: make add-dev PACKAGE=pytest)
	@if [ -z "$(PACKAGE)" ]; then \
		echo "$(RED)❌ 请提供包名: make add-dev PACKAGE=pytest$(RESET)"; \
		exit 1; \
	fi
	@echo "$(BLUE)📦 添加开发依赖: $(PACKAGE)$(RESET)"
	$(UV) add --dev $(PACKAGE)

shell: ## 启动Python Shell (带项目环境)
	@echo "$(BLUE)🐍 启动Python Shell...$(RESET)"
	$(UV) run python

db-reset: ## 重置数据库 (删除所有表并重新迁移)
	@echo "$(RED)⚠️  警告: 这将删除所有数据!$(RESET)"
	@read -p "确认继续? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	@echo "$(BLUE)🔄 重置数据库...$(RESET)"
	$(UV) run alembic downgrade base
	$(MAKE) migrate
	@echo "$(GREEN)✅ 数据库重置完成$(RESET)"

db-status: ## 查看数据库迁移状态
	@echo "$(BLUE)📊 数据库迁移状态:$(RESET)"
	$(UV) run alembic current

logs: ## 查看应用日志 (如果启用了日志文件)
	@if [ -f "logs/app.log" ]; then \
		echo "$(BLUE)📄 应用日志:$(RESET)"; \
		tail -f logs/app.log; \
	else \
		echo "$(YELLOW)⚠️  日志文件不存在，确保LOG_FILE配置正确$(RESET)"; \
	fi

health: ## 检查服务健康状态
	@echo "$(BLUE)🏥 检查服务健康状态...$(RESET)"
	@echo "$(GREEN)API服务:$(RESET)"
	@curl -s http://$(HOST):$(PORT)/health | python3 -m json.tool 2>/dev/null || echo "$(RED)服务未运行$(RESET)"
	@echo ""
	@echo "$(GREEN)数据库连接:$(RESET)"
	@curl -s http://$(HOST):$(PORT)/health/database | python3 -m json.tool 2>/dev/null || echo "$(RED)数据库检查失败$(RESET)"

docs: ## 启动文档服务 (如果配置了)
	@echo "$(BLUE)📚 API文档地址:$(RESET)"
	@echo "$(GREEN)Swagger UI: http://$(HOST):$(PORT)/docs$(RESET)"
	@echo "$(GREEN)ReDoc: http://$(HOST):$(PORT)/redoc$(RESET)"

# 开发者工具
info: ## 显示项目信息
	@echo "$(BLUE)📋 项目信息:$(RESET)"
	@echo "  项目名称: $(PROJECT_NAME)"
	@echo "  Python版本: $(shell $(PYTHON) --version)"
	@echo "  uv版本: $(shell $(UV) --version)"
	@echo "  端口: $(PORT)"
	@echo "  环境: $(shell $(UV) run python -c "from src.core.config import settings; print(settings.ENVIRONMENT)")"
	@echo ""

# 快速别名
s: start ## start的别名
m: migrate ## migrate的别名
t: test ## test的别名
l: lint ## lint的别名
c: clean ## clean的别名