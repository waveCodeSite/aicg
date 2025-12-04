"""
FFmpeg工具函数 - 视频处理相关的FFmpeg操作
"""

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from src.core.logging import get_logger

logger = get_logger(__name__)


def check_ffmpeg_installed() -> bool:
    """
    检查FFmpeg是否已安装

    Returns:
        如果FFmpeg可用返回True，否则返回False
    """
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.info("FFmpeg已安装并可用")
            return True
        return False
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
        logger.error(f"FFmpeg检查失败: {e}")
        return False


def get_audio_duration(audio_path: str) -> Optional[float]:
    """
    获取音频文件时长

    Args:
        audio_path: 音频文件路径

    Returns:
        音频时长（秒），如果失败返回None
    """
    try:
        # 使用ffprobe获取音频时长
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            duration = float(result.stdout.strip())
            logger.debug(f"音频时长: {audio_path} = {duration}秒")
            return duration
        else:
            logger.error(f"获取音频时长失败: {result.stderr}")
            return None

    except Exception as e:
        logger.error(f"获取音频时长异常: {e}")
        return None


def create_concat_file(video_paths: List[Path], output_path: Path) -> None:
    """
    创建FFmpeg concat文件

    Args:
        video_paths: 视频文件路径列表
        output_path: concat文件输出路径
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for video_path in video_paths:
                # 使用绝对路径并转义特殊字符
                abs_path = video_path.absolute()
                # FFmpeg concat文件格式: file 'path'
                f.write(f"file '{abs_path}'\n")

        logger.info(f"创建concat文件成功: {output_path}, 包含{len(video_paths)}个视频")

    except Exception as e:
        logger.error(f"创建concat文件失败: {e}")
        raise


def run_ffmpeg_command(command: List[str], timeout: int = 300) -> Tuple[bool, str, str]:
    """
    执行FFmpeg命令

    Args:
        command: FFmpeg命令列表
        timeout: 超时时间（秒），默认300秒

    Returns:
        (是否成功, 标准输出, 标准错误)
    """
    try:
        logger.info(f"执行FFmpeg命令: {' '.join(command)}")

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        success = result.returncode == 0

        if success:
            logger.info("FFmpeg命令执行成功")
        else:
            logger.error(f"FFmpeg命令执行失败: {result.stderr}")

        return success, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        error_msg = f"FFmpeg命令执行超时（{timeout}秒）"
        logger.error(error_msg)
        return False, "", error_msg

    except Exception as e:
        error_msg = f"FFmpeg命令执行异常: {e}"
        logger.error(error_msg)
        return False, "", error_msg


def build_sentence_video_command(
        image_path: str,
        audio_path: str,
        output_path: str,
        subtitle_filter: str,
        gen_setting: dict
) -> List[str]:
    """
    构建单句视频合成命令（电影级效果）

    Args:
        image_path: 图片路径
        audio_path: 音频路径
        output_path: 输出视频路径
        subtitle_filter: 字幕滤镜字符串
        gen_setting: 生成设置

    Returns:
        FFmpeg命令列表
    """
    # 获取音频时长
    duration = get_audio_duration(audio_path)
    if not duration:
        raise ValueError(f"无法获取音频时长: {audio_path}")

    # 解析设置
    resolution = gen_setting.get("resolution", "1440x1080")  # 默认4:3横屏
    fps = gen_setting.get("fps", 30)  # 提高到30fps更流畅
    video_codec = gen_setting.get("video_codec", "libx264")
    audio_codec = gen_setting.get("audio_codec", "aac")
    audio_bitrate = gen_setting.get("audio_bitrate", "192k")
    video_speed = gen_setting.get("video_speed", 1.0)  # 视频速度，默认1.0（正常速度）
    zoom_speed = gen_setting.get("zoom_speed", 0.00015)  # Ken Burns缩放速度，默认0.00015

    # 解析分辨率
    width, height = resolution.split('x')
    
    # 计算总帧数（考虑视频速度）
    # 如果速度是2.0，视频会快2倍，所以帧数减半
    effective_duration = duration / video_speed
    total_frames = int(fps * effective_duration)

    # 增强的Ken Burns效果：
    # 1. 缩放：从1.0逐渐放大到1.15（更明显的缩放）
    # 2. 平移：从左上角移动到右下角（增加动感）
    # 3. 使用easing函数让动画更自然
    
    # zoompan参数：
    # z: 缩放因子，使用pzoom（前一帧的zoom）+ 增量
    # x, y: 平移坐标
    # d: 持续帧数
    # s: 输出尺寸
    
    # 构建视频滤镜链
    video_filters = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
        f"zoompan="
        f"z='min(1+{zoom_speed}*on,1.15)':"  # 使用配置的缩放速度
        f"x='iw/2-(iw/zoom/2)-{int(width)*0.05}*on/{total_frames}':"  # 从左向右平移
        f"y='ih/2-(ih/zoom/2)-{int(height)*0.05}*on/{total_frames}':"  # 从上向下平移
        f"d={total_frames}:"
        f"s={width}x{height}:"
        f"fps={fps}"
    )
    
    # 如果视频速度不是1.0，添加setpts滤镜
    if video_speed != 1.0:
        # setpts用于调整视频时间戳
        # PTS/(speed) 会让视频加速，例如 speed=2.0 时，PTS/2 让视频快2倍
        video_filters += f",setpts=PTS/{video_speed}"
    
    # 构建音频滤镜链
    # atempo用于调整音频速度，同时保持音调
    # atempo的范围是0.5-2.0，如果需要更大的速度变化，需要链式调用
    audio_filters = "[1:a]"
    if video_speed != 1.0:
        # 计算需要多少个atempo滤镜
        # atempo单次只能在0.5-2.0范围内调整
        remaining_speed = video_speed
        atempo_chain = []
        
        while remaining_speed > 2.0:
            atempo_chain.append("atempo=2.0")
            remaining_speed /= 2.0
        
        while remaining_speed < 0.5:
            atempo_chain.append("atempo=0.5")
            remaining_speed /= 0.5
        
        if remaining_speed != 1.0:
            atempo_chain.append(f"atempo={remaining_speed}")
        
        if atempo_chain:
            audio_filters += ",".join(atempo_chain)
    
    audio_filters += "[a]"
    
    if subtitle_filter:
        # 有字幕时的滤镜链
        filter_complex = (
            f"{video_filters}[bg];"
            f"[bg]{subtitle_filter}[v];"
            f"{audio_filters}"
        )
        map_video = "[v]"
        map_audio = "[a]"
    else:
        # 无字幕时的滤镜链
        filter_complex = (
            f"{video_filters}[v];"
            f"{audio_filters}"
        )
        map_video = "[v]"
        map_audio = "[a]"

    # 构建命令
    command = [
        "ffmpeg",
        "-y",
        "-loop", "1",
        "-framerate", str(fps),
        "-i", image_path,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", map_video,
        "-map", map_audio,
        "-c:v", video_codec,
        "-preset", "slow",  # 使用slow预设获得最佳质量
        "-crf", "20",  # 提高质量（更低的CRF值）
        "-profile:v", "high",  # 使用high profile
        "-level", "4.2",
        "-c:a", audio_codec,
        "-b:a", audio_bitrate,
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",  # 优化网络播放
        "-shortest",
        output_path
    ]

    return command


def concatenate_videos(video_paths: List[Path], output_path: Path, concat_file_path: Path) -> bool:
    """
    拼接多个视频文件

    Args:
        video_paths: 视频文件路径列表
        output_path: 输出视频路径
        concat_file_path: concat文件路径

    Returns:
        是否成功
    """
    try:
        # 创建concat文件
        create_concat_file(video_paths, concat_file_path)

        # 构建拼接命令
        command = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file_path),
            "-c", "copy",  # 直接复制流，不重新编码
            str(output_path)
        ]

        # 执行命令
        success, stdout, stderr = run_ffmpeg_command(command, timeout=600)

        if success:
            logger.info(f"视频拼接成功: {output_path}")
        else:
            logger.error(f"视频拼接失败: {stderr}")

        return success

    except Exception as e:
        logger.error(f"视频拼接异常: {e}")
        return False



def mix_bgm_with_video(
        video_path: str,
        bgm_path: str,
        output_path: str,
        bgm_volume: float = 0.15,
        loop_bgm: bool = True
) -> bool:
    """
    将BGM混合到视频中

    Args:
        video_path: 输入视频路径
        bgm_path: BGM音频路径
        output_path: 输出视频路径
        bgm_volume: BGM音量（0.0-1.0），默认0.15（15%）
        loop_bgm: 是否循环BGM以匹配视频长度

    Returns:
        是否成功
    """
    try:
        # 获取视频时长
        video_duration = get_audio_duration(video_path)
        if not video_duration:
            logger.error("无法获取视频时长")
            return False

        # 获取BGM时长
        bgm_duration = get_audio_duration(bgm_path)
        if not bgm_duration:
            logger.error("无法获取BGM时长")
            return False

        logger.info(f"视频时长: {video_duration:.2f}s, BGM时长: {bgm_duration:.2f}s, BGM音量: {bgm_volume}")

        # 构建FFmpeg命令
        # 使用 amix 滤镜混合原音频和BGM
        # 如果BGM较短，使用 aloop 循环；如果较长，会自动截断
        
        if loop_bgm and bgm_duration < video_duration:
            # 计算需要循环的次数
            loop_count = int(video_duration / bgm_duration) + 1
            
            # 构建滤镜：调整BGM音量，循环BGM，然后与原音频混合
            filter_complex = (
                f"[1:a]volume={bgm_volume},aloop=loop={loop_count}:size=2e+09[bgm];"
                f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
        else:
            # BGM足够长或不需要循环，直接混合
            filter_complex = (
                f"[1:a]volume={bgm_volume}[bgm];"
                f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )

        command = [
            "ffmpeg",
            "-y",
            "-i", video_path,  # 输入视频
            "-i", bgm_path,    # 输入BGM
            "-filter_complex", filter_complex,
            "-map", "0:v",     # 使用视频流
            "-map", "[aout]",  # 使用混合后的音频流
            "-c:v", "copy",    # 视频流直接复制，不重新编码
            "-c:a", "aac",     # 音频编码为AAC
            "-b:a", "192k",    # 音频比特率
            "-shortest",       # 以最短的流为准
            output_path
        ]

        # 执行命令
        success, stdout, stderr = run_ffmpeg_command(command, timeout=600)

        if success:
            logger.info(f"BGM混合成功: {output_path}")
        else:
            logger.error(f"BGM混合失败: {stderr}")

        return success

    except Exception as e:
        logger.error(f"BGM混合异常: {e}")
        return False


__all__ = [
    "check_ffmpeg_installed",
    "get_audio_duration",
    "create_concat_file",
    "run_ffmpeg_command",
    "build_sentence_video_command",
    "concatenate_videos",
    "mix_bgm_with_video",
]

