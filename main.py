import os
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.components import Plain
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.provider.entities import ProviderRequest

@register("astrbot_plugin_image_size_limit", "YourName", "限制图片尺寸", "0.1")
class MyPlugin(Star):
    max_size: int = 1 * 1024 * 200
    config: AstrBotConfig

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config

    async def initialize(self):
        self.max_size = self.config.get("max_size", 204800)
        logger.info(f"最大图片尺寸限制：{self.max_size}字节")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("image-size")
    def set_image_size(self, event: AstrMessageEvent, size: int):
        self.max_size = size
        logger.info(f"限制图片尺寸为{size}字节")
        yield event.plain_result(f"当前图片尺寸限制为{self.max_size}字节")

    @filter.on_llm_request()
    async def my_custom_hook_1(self, event: AstrMessageEvent, req: ProviderRequest):
        for image_url in req.image_urls:
            size = os.path.getsize(image_url)
            logger.info("图片{},尺寸{}".format(image_url, size))
            if size > self.max_size:
                await event.send(MessageChain([Plain(f"图片尺寸过大，请上传小于 {self.max_size}字节 的图片。")]))
                event.stop_event()

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
