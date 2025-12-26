# src/services/providers/custom_provider.py
import asyncio
import aiohttp
import json
from typing import Any, Dict, List
from openai import AsyncOpenAI

from src.core.logging import get_logger
from src.services.provider.base import BaseLLMProvider, log_provider_call

logger = get_logger(__name__)


class CustomProvider(BaseLLMProvider):
    """
    纯净 SiliconFlow Provider，不含任何业务逻辑。

    - 不拼接 prompt
    - 不封装风格
    - 不理解句子
    - 不处理提示词生成

    只提供 completions() 和 generate_image() 接口 → 等同于一个可并发的 SiliconFlow SDK wrapper
    """

    def __init__(
        self,
        api_key: str,
        max_concurrency: int = 5,
        base_url: str = "https://api.siliconflow.cn/v1",
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.base_url = base_url
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(max_concurrency)

    @log_provider_call("completions")
    async def completions(
        self, model: str, messages: List[Dict[str, Any]], **kwargs: Any
    ):
        """
        调用 SiliconFlow chat.completions.create（纯粹透传）
        """

        # 用 semaphore 限制并发
        async with self.semaphore:
            return await self.client.chat.completions.create(
                model=model, messages=messages, **kwargs
            )

    @log_provider_call("generate_image")
    async def generate_image(self, prompt: str, model: str = None, **kwargs: Any):
        """
        调用 自定义 images.generate（纯粹透传）
        如果模型是 gemini-3-pro-image-preview，则调用 generate_image_gemini
        """

        # 检查是否是 Gemini 图像模型
        if model and "gemini" in model.lower():
            # 调用 Gemini 专用方法，传递所有kwargs
            gemini_response = await self.generate_image_gemini(prompt, **kwargs)

            # 将 Gemini 响应包装成兼容格式
            return self._wrap_gemini_response(gemini_response)

        # 用 semaphore 限制并发
        async with self.semaphore:
            return await self.client.images.generate(
                model=model or "Kwai-Kolors/Kolors", prompt=prompt, **kwargs
            )

    @log_provider_call("generate_audio")
    async def generate_audio(
        self, input_text: str, voice: str = "alloy", model: str = "tts-1", **kwargs: Any
    ):
        """
        调用 OpenAI audio.speech.create（纯粹透传）
        """

        # 用 semaphore 限制并发
        async with self.semaphore:
            return await self.client.audio.speech.create(
                model=model, voice=voice, input=input_text, **kwargs
            )

    def _wrap_gemini_response(self, gemini_response: dict):
        """
        将 Gemini 响应包装成兼容 OpenAI 格式的对象

        Gemini API 实际返回格式:
        {
            "candidates": [{
                "content": {
                    "parts": [
                        {"text": "..."},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": "<BASE64>"
                            }
                        }
                    ]
                }
            }]
        }
        """
        try:
            parts = gemini_response["candidates"][0]["content"]["parts"]

            base64_data = None
            mime = None

            # 遍历 parts 查找图片数据
            for part in parts:
                # 检查 inlineData 字段（注意是驼峰命名）
                if "inlineData" in part:
                    base64_data = part["inlineData"]["data"]
                    mime = part["inlineData"]["mimeType"]
                    break

            if not base64_data:
                raise ValueError(
                    "响应中未找到图片数据 (inlineData 或 thoughtSignature)"
                )

            # 创建兼容对象
            class GeminiImageResponse:
                def __init__(self, base64_data, mime):
                    self.data = [GeminiImageData(base64_data, mime)]

            class GeminiImageData:
                def __init__(self, base64_data, mime):
                    self.url = None  # Gemini 不返回 URL
                    self.b64_json = base64_data  # 存储 base64 数据
                    self.mime = mime

            return GeminiImageResponse(base64_data, mime)
        except (KeyError, IndexError) as e:
            raise ValueError(f"无法从 Gemini 响应中提取图像数据: {e}")

    async def generate_image_gemini(self, prompt: str,aspectRatio: str="16:9",imageSize: str="2K", **kwargs: Any):
        """
        Gemini 生成图像（携程异步版本）
        支持 reference_images 参数 (Persona)
        """
        base_url = self.base_url.replace("/v1", "")
        url = f"{base_url}/v1beta/models/gemini-3-pro-image-preview:generateContent?key={self.api_key}"
        
        # 构造 prompt 部分
        parts = [{"text": prompt}]
        
        # 处理参考图 (Persona)
        reference_images = kwargs.get("reference_images")
        if reference_images:
            import base64
            from datetime import timedelta
            from src.utils.storage import get_storage_client
            
            logger.info(f"处理 {len(reference_images)} 张参考图")
            
            # 检查是否是MinIO key (以"uploads/"开头)
            if reference_images and reference_images[0].startswith("uploads/"):
                logger.info("检测到MinIO key,转换为presigned URL")
                storage_client = await get_storage_client()
                converted_urls = []
                for key in reference_images[:5]:  # 最大5张
                    try:
                        presigned_url = storage_client.get_presigned_url(key, expires=timedelta(hours=1))
                        converted_urls.append(presigned_url)
                        logger.debug(f"MinIO key转URL: {key[:30]}...")
                    except Exception as e:
                        logger.warning(f"MinIO key转URL失败 {key}: {e}")
                reference_images = converted_urls
            
            # 最大支持 5 张参考图
            for img_url in reference_images[:5]:
                try:
                    # 下载参考图并转 Base64
                    async with aiohttp.ClientSession() as session:
                        async with session.get(img_url, timeout=10) as resp:
                            if resp.status == 200:
                                img_data = await resp.read()
                                b64_img = base64.b64encode(img_data).decode('utf-8')
                                
                                # 检测MIME类型
                                mime_type = "image/jpeg"
                                if img_data[:4] == b'\x89PNG':
                                    mime_type = "image/png"
                                
                                parts.append({
                                    "inline_data": {
                                        "mime_type": mime_type,
                                        "data": b64_img
                                    }
                                })
                                logger.info(f"成功添加参考图: {img_url[:50]}...")
                            else:
                                logger.warning(f"下载参考图失败 HTTP {resp.status}: {img_url[:50]}...")
                except Exception as e:
                    logger.warning(f"处理参考图失败 {img_url[:50]}...: {e}")

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": aspectRatio,"imageSize": imageSize}},
        }   

        async with self.semaphore:  # 控制最大并发
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, json=payload, headers={"Content-Type": "application/json"}
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Gemini API Error: {error_text}")
                        raise ValueError(f"Gemini API 请求失败: {resp.status} - {error_text}")
                        
                    result = await resp.text()
                    return json.loads(result)

