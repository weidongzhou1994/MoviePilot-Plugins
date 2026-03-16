import time
from typing import Any, List, Dict, Tuple

from app.core.config import settings
from app.core.context import MediaInfo
from app.core.event import eventmanager, Event
from app.modules.emby import Emby
from app.modules.jellyfin import Jellyfin
from app.modules.plex import Plex
from app.plugins import _PluginBase
from app.schemas import TransferInfo, RefreshMediaItem
from app.schemas.types import EventType
from app.log import logger


class MediaServerRefresh(_PluginBase):
    # 插件名称
    plugin_name = "媒体库服务器刷新"
    # 插件描述
    plugin_desc = "入库后自动刷新Emby/Jellyfin/Plex服务器海报墙。"
    # 插件图标
    plugin_icon = "https://github.com/jxxghp/MoviePilot-Plugins/tree/main/icons/refresh2.png"
    # 插件版本
    plugin_version = "2.2"
    # 插件作者
    plugin_author = "jxxghp"
    # 作者主页
    author_url = "https://github.com/jxxghp"
    # 插件配置项ID前缀
    plugin_config_prefix = "mediaserverrefresh_"
    # 加载顺序
    plugin_order = 14
    # 可使用的用户级别
    auth_level = 1

    # 私有属性
    _enabled = False
    _delay = 0
    _emby = None
    _jellyfin = None
    _plex = None
    _path_transfer_confs = ""

    def init_plugin(self, config: dict = None):
        self._emby = Emby()
        self._jellyfin = Jellyfin()
        self._plex = Plex()
        if config:
            self._enabled = config.get("enabled")
            self._delay = config.get("delay") or 0
            self._path_transfer_confs = config.get("path_transfer_confs") or ""

    def get_state(self) -> bool:
        return self._enabled

    @staticmethod
    def get_command() -> List[Dict[str, Any]]:
        pass

    def get_api(self) -> List[Dict[str, Any]]:
        pass

    def get_form(self) -> Tuple[List[dict], Dict[str, Any]]:
        """
        拼装插件配置页面，需要返回两块数据：1、页面配置；2、数据结构
        """
        return [
            {
                'component': 'VForm',
                'content': [
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                    'md': 6
                                },
                                'content': [
                                    {
                                        'component': 'VSwitch',
                                        'props': {
                                            'model': 'enabled',
                                            'label': '启用插件',
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12,
                                },
                                'content': [
                                    {
                                        'component': 'VTextField',
                                        'props': {
                                            'model': 'delay',
                                            'label': '延迟时间（秒）',
                                            'placeholder': '0'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                    {
                        'component': 'VRow',
                        'content': [
                            {
                                'component': 'VCol',
                                'props': {
                                    'cols': 12
                                },
                                'content': [
                                    {
                                        'component': 'VTextarea',
                                        'props': {
                                            'model': 'path_transfer_confs',
                                            'label': '网盘路径转换配置',
                                            'rows': 5,
                                            'placeholder': '网盘目录#本地目录'
                                        }
                                    }
                                ]
                            }
                        ]
                    },
                ]
            }
        ], {
            "enabled": False,
            "delay": 0,
            "path_transfer_confs": ""
        }

    def get_page(self) -> List[dict]:
        pass

    @eventmanager.register(EventType.TransferComplete)
    def refresh(self, event: Event):
        """
        发送通知消息
        """
        if not self._enabled:
            return

        event_info: dict = event.event_data
        if not event_info:
            return

        # 刷新媒体库
        if not settings.MEDIASERVER:
            return

        if self._delay:
            logger.info(f"延迟 {self._delay} 秒后刷新媒体库... ")
            time.sleep(float(self._delay))

        # 入库数据
        transferinfo: TransferInfo = event_info.get("transferinfo")
        mediainfo: MediaInfo = event_info.get("mediainfo")
        for path_transfer_conf in self._path_transfer_confs.split("\n"):
            if not path_transfer_conf:
                    continue
            if str(path_transfer_conf).count("#") != 1:
                    logger.error(f"{path_transfer_conf} 格式错误")
                    continue
            pan_type, pan_path, local_path = path_transfer_conf.split("#")
            if transferinfo.target_storage == pan_type:
                transferinfo.target_path = transferinfo.target_path.replace(pan_path, local_path, 1)
                logger.info(f"转换路径 {pan_path} -> {local_path}，得到 {transferinfo.target_path}")
                break
        items = [
            RefreshMediaItem(
                title=mediainfo.title,
                year=mediainfo.year,
                type=mediainfo.type,
                category=mediainfo.category,
                target_path=transferinfo.target_path
            )
        ]
        # Emby
        if "emby" in settings.MEDIASERVER:
            self._emby.refresh_library_by_items(items)

        # Jeyllyfin
        if "jellyfin" in settings.MEDIASERVER:
            # FIXME Jellyfin未找到刷新单个项目的API
            self._jellyfin.refresh_root_library()

        # Plex
        if "plex" in settings.MEDIASERVER:
            self._plex.refresh_library_by_items(items)

    def stop_service(self):
        """
        退出插件
        """
        pass
