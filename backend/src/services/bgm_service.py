"""
BGM管理服务 - 背景音乐文件管理
"""

import os
import subprocess
import uuid
from typing import List, Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import BusinessLogicError, NotFoundError
from src.core.logging import get_logger
from src.models.bgm import BGM, BGMStatus
from src.services.base import BaseService
from src.utils.storage import storage_client

logger = get_logger(__name__)


class BGMService(BaseService):
    """BGM管理服务"""

    def __init__(self, db_session: Optional[AsyncSession] = None):
        super().__init__(db_session)
        logger.debug("BGMService 初始化完成")

    async def upload_bgm(self, user_id: str, file: UploadFile, name: str) -> BGM:
        """
        上传BGM文件

        Args:
            user_id: 用户ID
            file: 上传的文件
            name: BGM名称

        Returns:
            创建的BGM对象

        Raises:
            BusinessLogicError: 文件格式不支持或文件过大
        """
        # 验证文件类型
        allowed_extensions = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
        file_ext = os.path.splitext(file.filename)[1].lower()

        if file_ext not in allowed_extensions:
            raise BusinessLogicError(
                f"不支持的音频格式: {file_ext}。支持的格式: {', '.join(allowed_extensions)}"
            )

        # 验证文件大小 (50MB)
        max_size = 50 * 1024 * 1024
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        if file_size > max_size:
            raise BusinessLogicError(f"文件大小超过限制 (最大 50MB)")

        try:
            # 生成存储路径
            file_key = f"bgm/{user_id}/{uuid.uuid4()}{file_ext}"

            # 读取内容用于提取时长
            content = await file.read()
            await file.seek(0)

            # 上传到MinIO
            upload_result = await storage_client.upload_file(
                user_id=user_id, file=file, object_key=file_key
            )

            # 使用返回的key
            file_key = upload_result["object_key"]

            # 提取音频时长
            duration = await self._extract_audio_duration(content, file_ext)

            # 创建BGM记录
            bgm = BGM(
                user_id=user_id,
                name=name,
                file_name=file.filename,
                file_size=file_size,
                file_key=file_key,
                duration=duration,
                status=BGMStatus.ACTIVE,
            )

            self.add(bgm)
            await self.commit()
            await self.refresh(bgm)

            logger.info(f"BGM上传成功: ID={bgm.id}, 名称={name}, 时长={duration}s")
            return bgm

        except Exception as e:
            await self.rollback()
            logger.error(f"BGM上传失败: {e}")
            # 尝试清理已上传的文件
            try:
                if "file_key" in locals():
                    storage_client.delete_file(file_key)
            except:
                pass
            raise

    async def _extract_audio_duration(
        self, content: bytes, file_ext: str
    ) -> Optional[int]:
        """
        使用ffprobe提取音频时长

        Args:
            content: 音频文件内容
            file_ext: 文件扩展名

        Returns:
            音频时长（秒），如果提取失败返回None
        """
        import tempfile

        try:
            # 写入临时文件
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name

            # 使用ffprobe获取时长
            cmd = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                tmp_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

            if result.returncode == 0 and result.stdout.strip():
                duration = float(result.stdout.strip())
                return int(duration)

            logger.warning(f"无法提取音频时长: {result.stderr}")
            return None

        except Exception as e:
            logger.warning(f"提取音频时长失败: {e}")
            return None
        finally:
            # 清理临时文件
            try:
                if "tmp_path" in locals():
                    os.unlink(tmp_path)
            except:
                pass

    async def list_user_bgms(
        self,
        user_id: str,
        page: int = 1,
        size: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[BGM], int]:
        """
        获取用户的BGM列表（分页）

        Args:
            user_id: 用户ID
            page: 页码
            size: 每页大小
            sort_by: 排序字段
            sort_order: 排序顺序

        Returns:
            (BGM列表, 总记录数)
        """
        # 参数验证
        if page < 1:
            page = 1
        if size < 1 or size > 100:
            size = min(max(size, 1), 100)

        # 构建查询
        query = select(BGM).filter(
            BGM.user_id == user_id, BGM.status == BGMStatus.ACTIVE
        )

        # 获取总数
        count_query = select(func.count(BGM.id)).filter(
            BGM.user_id == user_id, BGM.status == BGMStatus.ACTIVE
        )
        total_result = await self.execute(count_query)
        total = total_result.scalar()

        # 排序
        sort_column = getattr(BGM, sort_by, BGM.created_at)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)

        # 分页
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)

        # 执行查询
        result = await self.execute(query)
        bgms = result.scalars().all()

        logger.debug(f"查询用户BGM: 用户={user_id}, 总数={total}, 当前页={page}")
        return list(bgms), total

    async def get_bgm_by_id(self, bgm_id: str, user_id: str) -> BGM:
        """
        获取BGM详情

        Args:
            bgm_id: BGM ID
            user_id: 用户ID（用于权限验证）

        Returns:
            BGM对象

        Raises:
            NotFoundError: BGM不存在或无权访问
        """
        query = select(BGM).filter(
            BGM.id == bgm_id, BGM.user_id == user_id, BGM.status == BGMStatus.ACTIVE
        )

        result = await self.execute(query)
        bgm = result.scalar_one_or_none()

        if not bgm:
            raise NotFoundError(
                "BGM不存在或无权访问", resource_type="bgm", resource_id=bgm_id
            )

        return bgm

    async def delete_bgm(self, bgm_id: str, user_id: str) -> bool:
        """
        删除BGM

        Args:
            bgm_id: BGM ID
            user_id: 用户ID（用于权限验证）

        Returns:
            是否删除成功
        """
        bgm = await self.get_bgm_by_id(bgm_id, user_id)

        try:
            # 从MinIO删除文件
            if bgm.file_key:
                await storage_client.delete_file(bgm.file_key)

            # 使用 SQL DELETE 语句从数据库删除
            from sqlalchemy import delete as sql_delete
            logger.info(f"📝 执行SQL DELETE BGM: ID={bgm_id}")
            
            stmt = sql_delete(BGM).where(BGM.id == bgm_id)
            result = await self.execute(stmt)
            await self.commit()

            logger.info(f"删除BGM成功: ID={bgm_id}, 名称={bgm.name}, 影响行数={result.rowcount}")
            return True

        except Exception as e:
            await self.rollback()
            logger.error(f"删除BGM失败: {e}")
            raise

    async def get_bgm_stats(self, user_id: str) -> dict:
        """
        获取用户的BGM统计信息

        Args:
            user_id: 用户ID

        Returns:
            统计信息字典
        """
        # 总数量
        count_query = select(func.count(BGM.id)).filter(
            BGM.user_id == user_id, BGM.status == BGMStatus.ACTIVE
        )
        count_result = await self.execute(count_query)
        total_count = count_result.scalar()

        # 总大小
        size_query = select(func.sum(BGM.file_size)).filter(
            BGM.user_id == user_id, BGM.status == BGMStatus.ACTIVE
        )
        size_result = await self.execute(size_query)
        total_size = size_result.scalar() or 0

        return {
            "total_count": total_count,
            "total_size": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }


__all__ = ["BGMService"]
