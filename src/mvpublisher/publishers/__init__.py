"""Publisher abstractions and runner for platform publishing."""

from .base import PublishResult, Publisher
from .runner import run_publishers
from .xiaohongshu import XiaohongshuPublisher
from .douyin import DouyinPublisher
from .wechat_channels import WechatChannelsPublisher

__all__ = [
    "PublishResult",
    "Publisher",
    "XiaohongshuPublisher",
    "DouyinPublisher",
    "WechatChannelsPublisher",
    "run_publishers",
]
