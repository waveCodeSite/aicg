#!/bin/bash

# ==========================================
# AICG平台 - Docker镜像构建脚本
# ==========================================

set -e  # 遇到错误立即退出

# 颜色定义
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 配置 - 与docker-compose.prod.yml保持一致
BACKEND_IMAGE="wave/aicon-backend:latest"
FRONTEND_IMAGE="wave/aicon-frontend:latest"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}AICG平台 - Docker镜像构建${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker未安装，请先安装Docker${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker已安装${NC}"
echo ""

# 构建后端镜像
echo -e "${BLUE}📦 构建后端镜像...${NC}"
echo -e "${YELLOW}镜像名称: ${BACKEND_IMAGE}${NC}"
cd backend
docker build -t "${BACKEND_IMAGE}" .
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 后端镜像构建成功${NC}"
else
    echo -e "${RED}❌ 后端镜像构建失败${NC}"
    exit 1
fi
cd ..
echo ""

# 构建前端镜像
echo -e "${BLUE}📦 构建前端镜像...${NC}"
echo -e "${YELLOW}镜像名称: ${FRONTEND_IMAGE}${NC}"
cd frontend
docker build -t "${FRONTEND_IMAGE}" .
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 前端镜像构建成功${NC}"
else
    echo -e "${RED}❌ 前端镜像构建失败${NC}"
    exit 1
fi
cd ..
echo ""

# 显示镜像信息
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🎉 所有镜像构建完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}构建的镜像:${NC}"
docker images | grep "aicon-backend\|aicon-frontend"
echo ""

# 提示下一步操作
echo -e "${BLUE}========================================${NC}"
echo -e "${YELLOW}下一步操作:${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "1. ${GREEN}启动服务:${NC}"
echo -e "   docker-compose -f docker-compose.prod.yml --env-file .env.production up -d"
echo ""
echo -e "2. ${GREEN}查看服务状态:${NC}"
echo -e "   docker-compose -f docker-compose.prod.yml ps"
echo ""
echo -e "3. ${GREEN}查看日志:${NC}"
echo -e "   docker-compose -f docker-compose.prod.yml logs -f"
echo ""
