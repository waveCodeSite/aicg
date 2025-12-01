# src/services/providers/custom_provider.py
import asyncio
import aiohttp
import json
from typing import Any, Dict, List
from openai import AsyncOpenAI

from src.services.provider.base import BaseLLMProvider


class CustomProvider(BaseLLMProvider):
    """
    纯净 SiliconFlow Provider，不含任何业务逻辑。

    - 不拼接 prompt
    - 不封装风格
    - 不理解句子
    - 不处理提示词生成

    只提供 completions() 和 generate_image() 接口 → 等同于一个可并发的 SiliconFlow SDK wrapper
    """

    def __init__(self, api_key: str, max_concurrency: int = 5, base_url: str = "https://api.siliconflow.cn/v1"):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.base_url = base_url
        self.api_key = api_key
        self.semaphore = asyncio.Semaphore(max_concurrency)

    async def completions(
            self,
            model: str,
            messages: List[Dict[str, Any]],
            **kwargs: Any
    ):
        """
        调用 SiliconFlow chat.completions.create（纯粹透传）
        """

        # 用 semaphore 限制并发
        async with self.semaphore:
            return await self.client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs
            )

    async def generate_image(
            self,
            prompt: str,
            model: str = None,
            **kwargs: Any
    ):
        """
        调用 自定义 images.generate（纯粹透传）
        如果模型是 gemini-3-pro-image-preview，则调用 generate_image_gemini
        """

        # 检查是否是 Gemini 图像模型
        if model and "gemini" in model.lower():
            # 调用 Gemini 专用方法
            gemini_response = await self.generate_image_gemini(prompt)

            # 将 Gemini 响应包装成兼容格式
            return self._wrap_gemini_response(gemini_response)

        # 用 semaphore 限制并发
        async with self.semaphore:
            return await self.client.images.generate(
                model=model or "Kwai-Kolors/Kolors",
                prompt=prompt,
                **kwargs
            )

    async def generate_audio(
            self,
            input_text: str,
            voice: str = "alloy",
            model: str = "tts-1",
            **kwargs: Any
    ):
        """
        调用 OpenAI audio.speech.create（纯粹透传）
        """

        # 用 semaphore 限制并发
        async with self.semaphore:
            return await self.client.audio.speech.create(
                model=model,
                voice=voice,
                input=input_text,
                **kwargs
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
                raise ValueError("响应中未找到图片数据 (inlineData 或 thoughtSignature)")

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

    async def generate_image_gemini(self, prompt: str):
        """
        Gemini 生成图像（携程异步版本）

        """
        base_url = self.base_url.replace("/v1", '')
        url = f"{base_url}/v1beta/models/gemini-3-pro-image-preview:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        }

        async with self.semaphore:  # 控制最大并发
            async with aiohttp.ClientSession() as session:
                async with session.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"}
                ) as resp:
                    result = await resp.text()
                    return json.loads(result)


if __name__ == "__main__":
    import asyncio


    async def test():
        # provider = CustomProvider(api_key="sk-ibB9WqeYysBiJnjy8eF2B7290bEf409c8d92476c9086BeEa",
        #                           base_url="https://jyapi.ai-wx.cn/v1")

        # provider = CustomProvider(api_key="sk-mrv4RQpMacJiNpA7T5h1yu8KAfkEdoPVvMOf1QM7ctDxEuGi",
        #                           base_url="https://api.vectorengine.ai/v1")
        # response = await provider.generate_image("A beautiful sunset over the mountains", model="sora_image")
        # print(response)

        provider = CustomProvider(api_key="sk-xrVNL5PZvNcpMzwsnyaJZ19nbExkdDRuPXwkI48WyE299Vft",
                                  base_url="https://api.vectorengine.ai/v1")
        response = await provider.generate_image_gemini(
            "范慎面部特写，惊骇呆滞的表情，瞳孔放大，冷汗从额头滑落，背景是庆国皇宫大殿阴影处，烛光摇曳形成强烈明暗对比，粗犷水墨线条勾勒人物轮廓，烽火台狼烟在窗外隐约可见，画面充满压抑的动荡感，细节呈现衣袍褶皱与面部肌肉紧绷状态")
        print(response)


    asyncio.run(test())
