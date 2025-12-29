"""
测试视频拼接功能 - 用于测试去除重复帧的视频拼接

使用方法:
python scripts/test_video_concatenation.py --chapter-id <章节ID>
python scripts/test_video_concatenation.py --chapter-id <章节ID> --no-remove-duplicates  # 对比测试
python scripts/test_video_concatenation.py --video-dir <视频目录>  # 使用本地视频测试
"""

import asyncio
import sys
from pathlib import Path
import argparse
import tempfile
import shutil

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.database import get_async_db
from src.core.logging import get_logger
from src.utils.ffmpeg_utils import concatenate_videos, check_ffmpeg_installed
from sqlalchemy import select
from sqlalchemy.orm import joinedload

logger = get_logger(__name__)


async def test_concatenation_from_chapter(chapter_id: str, args):
    """
    从章节的过渡视频测试拼接功能
    
    Args:
        chapter_id: 章节ID
        args: 命令行参数对象
    """
    temp_dir = None
    
    try:
        # 检查FFmpeg
        if not check_ffmpeg_installed():
            logger.error("FFmpeg未安装或不可用")
            return
        
        # 获取数据库会话
        async with get_async_db() as db_session:
            # 查询章节的所有过渡视频
            from src.models.movie import MovieScript, MovieShotTransition
            
            # 先获取剧本ID
            result = await db_session.execute(
                select(MovieScript)
                .where(MovieScript.chapter_id == chapter_id)
            )
            script = result.scalar_one_or_none()
            
            if not script:
                logger.error(f"章节没有电影剧本: {chapter_id}")
                return
            
            # 获取所有已完成的过渡视频
            result = await db_session.execute(
                select(MovieShotTransition)
                .where(MovieShotTransition.script_id == script.id)
                .where(MovieShotTransition.video_url.isnot(None))
                .order_by(MovieShotTransition.order_index)
                # .limit(6)
            )
            transitions = result.scalars().all()
            
            if len(transitions) < 2:
                logger.error(f"过渡视频数量不足(需要至少2个): {len(transitions)}")
                return
            
            logger.info(f"找到 {len(transitions)} 个过渡视频")
            
            # 创建临时目录
            temp_dir = Path(tempfile.mkdtemp(prefix="test_concat_"))
            logger.info(f"临时目录: {temp_dir}")
            
            # 下载过渡视频
            from src.utils.storage import get_storage_client
            storage = await get_storage_client()
            
            video_paths = []
            for idx, transition in enumerate(transitions):
                logger.info(f"📥 下载过渡视频 {idx + 1}/{len(transitions)}: {transition.video_url}")
                
                video_path = temp_dir / f"transition_{idx:03d}.mp4"
                content = await storage.download_file(transition.video_url)
                
                with open(video_path, 'wb') as f:
                    f.write(content)
                
                video_paths.append(video_path)
                logger.info(f"✅ 下载完成: {len(content)} bytes")
            
            # 执行拼接测试
            await _test_concatenation(
                video_paths, 
                temp_dir, 
                mode=args.mode,
                transition_type=args.transition_type,
                transition_duration=args.transition_duration,
                trim_frames=args.trim_frames
            )

            
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        
    finally:
        # 清理临时目录
        if temp_dir and temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"清理临时目录: {temp_dir}")
            except Exception as e:
                logger.error(f"清理临时目录失败: {e}")


async def _test_concatenation(
    video_paths: list, 
    temp_dir: Path, 
    mode: str = "crossfade",
    transition_type: str = "fade",
    transition_duration: float = 0.5,
    trim_frames: int = 15
):
    """
    执行拼接测试
    
    Args:
        video_paths: 视频文件路径列表
        temp_dir: 临时目录
        mode: 拼接模式 (crossfade/trim/fast)
        transition_type: 过渡效果类型 (仅crossfade模式)
        transition_duration: 过渡时长(秒) (仅crossfade模式)
        trim_frames: 每处裁剪的帧数 (仅trim模式)
    """
    import time
    
    # 准备输出
    output_dir = Path("./test_output")
    output_dir.mkdir(exist_ok=True)
    
    # 根据模式生成文件名
    if mode == "crossfade":
        suffix = f"_crossfade_{transition_type}_{transition_duration}s"
    elif mode == "trim":
        suffix = f"_trim{trim_frames}"
    else:
        suffix = "_fast"
    
    output_file = output_dir / f"concatenated{suffix}.mp4"
    concat_file = temp_dir / "concat.txt"
    
    logger.info("=" * 60)
    logger.info(f"开始拼接测试...")
    logger.info(f"视频数量: {len(video_paths)}")
    logger.info(f"拼接模式: {mode}")
    
    if mode == "crossfade":
        logger.info(f"过渡效果: {transition_type}")
        logger.info(f"过渡时长: {transition_duration}秒")
    elif mode == "trim":
        logger.info(f"裁剪帧数: {trim_frames}帧/处")
    
    logger.info("=" * 60)
    
    # 记录开始时间
    start_time = time.time()
    
    # 执行拼接
    success = concatenate_videos(
        video_paths,
        output_file,
        concat_file,
        mode=mode,
        transition_type=transition_type,
        transition_duration=transition_duration,
        trim_frames=trim_frames
    )
    
    # 记录结束时间
    elapsed_time = time.time() - start_time
    
    if success:
        logger.info("=" * 60)
        logger.info(f"✅ 视频拼接成功!")
        logger.info(f"📹 输出文件: {output_file.absolute()}")
        logger.info(f"📊 文件大小: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
        logger.info(f"⏱️  处理时间: {elapsed_time:.2f} 秒")
        logger.info(f"🔧 拼接模式: {mode}")
        logger.info("=" * 60)
        
        # 显示视频信息
        from src.utils.ffmpeg_utils import get_audio_duration
        duration = get_audio_duration(str(output_file))
        if duration:
            logger.info(f"🎬 视频时长: {duration:.2f} 秒")
        
        # 提示对比测试
        logger.info("")
        logger.info("💡 提示: 可以尝试不同的拼接模式进行对比:")
        logger.info("   --mode crossfade (推荐,最自然的过渡)")
        logger.info("   --mode trim (裁剪重复帧)")
        logger.info("   --mode fast (快速拼接,不处理)")
        
        if mode == "crossfade":
            logger.info("")
            logger.info("💡 可用的过渡效果:")
            logger.info("   fade, dissolve, wipeleft, wiperight, slideleft, slideright")
            logger.info("   circleopen, circleclose, fadeblack, fadewhite 等")
            
    else:
        logger.error("=" * 60)
        logger.error(f"❌ 视频拼接失败!")
        logger.error("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="测试视频拼接功能(支持多种拼接模式)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用crossfade模式(推荐,最自然)
  python scripts/test_video_concatenation.py --chapter-id abc123...
  
  # 使用不同的过渡效果
  python scripts/test_video_concatenation.py --chapter-id abc123... --transition-type dissolve
  
  # 调整过渡时长
  python scripts/test_video_concatenation.py --chapter-id abc123... --transition-duration 1.0
  
  # 使用trim模式(旧方法)
  python scripts/test_video_concatenation.py --chapter-id abc123... --mode trim
  
  # 使用fast模式(快速,不处理)
  python scripts/test_video_concatenation.py --chapter-id abc123... --mode fast
        """
    )
    
    # 互斥参数组
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--chapter-id",
        help="章节ID (UUID格式)"
    )
    
    # 拼接模式
    parser.add_argument(
        "--mode",
        choices=["crossfade", "trim", "fast"],
        default="crossfade",
        help="拼接模式: crossfade(交叉淡化,推荐), trim(裁剪重复帧), fast(快速拼接)"
    )
    
    # Crossfade模式参数
    parser.add_argument(
        "--transition-type",
        default="fade",
        help="过渡效果类型(仅crossfade模式): fade, dissolve, wipeleft, wiperight, slideleft, slideright, circleopen, circleclose, fadeblack, fadewhite等"
    )
    
    parser.add_argument(
        "--transition-duration",
        type=float,
        default=0.5,
        help="过渡时长(秒,仅crossfade模式), 默认0.5秒"
    )
    
    # Trim模式参数
    parser.add_argument(
        "--trim-frames",
        type=int,
        default=15,
        help="裁剪帧数(仅trim模式), 默认15帧"
    )
    
    args = parser.parse_args()
    
    # 运行测试
    asyncio.run(test_concatenation_from_chapter(args.chapter_id, args))


if __name__ == "__main__":
    main()
