import aiohttp
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.components import Image


@register("astrbot_plugin_image_size_limit", "ctrlkk", "限制图片尺寸", "0.2")
class MyPlugin(Star):
    max_size: int = 1 * 1024 * 200
    config: AstrBotConfig

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    async def initialize(self):
        self.max_size = self.config.get("max_size", 204800)
        logger.info(f"最大图片尺寸限制：{self.max_size}字节")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""

    def _get_browser_headers(self) -> dict:
        """获取模拟浏览器的请求头"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def _try_head_request(
        self, session: aiohttp.ClientSession, url: str, headers: dict
    ) -> int:
        """尝试使用 HEAD 请求获取文件大小"""
        try:
            async with session.head(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    content_length = response.headers.get("Content-Length")
                    if content_length:
                        return int(content_length)
                    logger.info("HEAD 请求成功但无法获取文件大小")
                else:
                    logger.info(f"HEAD 请求失败，状态码: {response.status}")
                return None
        except Exception as e:
            logger.info(f"HEAD 请求异常: {str(e)}")
            return None

    async def _try_get_request(
        self, session: aiohttp.ClientSession, url: str, headers: dict
    ) -> int:
        """尝试使用 GET 请求获取文件大小"""
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    content_length = response.headers.get("Content-Length")
                    if content_length:
                        response.close()
                        return int(content_length)
                    logger.info("GET 请求成功但无法获取文件大小")
                else:
                    logger.info(f"GET 请求失败，状态码: {response.status}")
                return None
        except Exception as e:
            logger.info(f"GET 请求异常: {str(e)}")
            return None

    async def get_url_file_size(self, url: str) -> int:
        """获取 URL 文件的尺寸"""
        headers = self._get_browser_headers()

        try:
            async with aiohttp.ClientSession() as session:
                # 首先尝试 HEAD 请求
                size = await self._try_head_request(session, url, headers)
                if size is not None:
                    return size

                # 如果 HEAD 请求失败，尝试 GET 请求
                size = await self._try_get_request(session, url, headers)
                return size
        except Exception as e:
            logger.error(f"获取远程文件尺寸时出错: {str(e)}")
            return None

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_all_message(self, event: AstrMessageEvent):
        """检查所有图片"""
        if not event.is_at_or_wake_command:
            return

        messages = event.get_messages()

        for component in messages:
            if isinstance(component, Image):
                logger.info(
                    f"检测到图片消息: file:{component.file} url:{component.url}"
                )

                if not component.url:
                    yield event.plain_result("无法获取图片URL")
                    event.stop_event()
                    break

                image_size = await self.get_url_file_size(component.url)
                if image_size is None:
                    yield event.plain_result("无法获取图片尺寸")
                    event.stop_event()
                    break

                logger.info(f"远程图片尺寸: {image_size} 字节")

                if image_size > self.max_size:
                    logger.info(f"图片尺寸超过限制，最大允许: {self.max_size} 字节")
                    yield event.plain_result(
                        f"图片尺寸过大，请上传小于 {self.max_size}字节 的图片。"
                    )
                    event.stop_event()
                    break
