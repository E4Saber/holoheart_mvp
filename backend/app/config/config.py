# app/core/config.py
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

class Settings:
    """应用程序设置类"""
    
    def __init__(self):
        # 基本目录设置
        self.BASE_DIR = Path(__file__).resolve().parent.parent.parent
        
        # API设置
        self.API_V1_PREFIX = "/api"
        self.PROJECT_NAME = "Kimi Chat API"
        
        # CORS设置
        self.CORS_ORIGINS = [
            "http://localhost:3000",  # React开发服务器
            "http://localhost:8000",
            "*"  # 允许所有来源（生产环境中应该限制）
        ]
        
        # 文件目录设置
        self.AUDIO_FILES_DIR = os.path.join(self.BASE_DIR, "static", "audio")
        self.MEMORY_DIR = os.path.join(self.BASE_DIR, "data", "memory")
        self.UPLOADS_DIR = os.path.join(self.BASE_DIR, "data", "uploads")
        
        # 确保目录存在
        for directory in [self.AUDIO_FILES_DIR, self.MEMORY_DIR, self.UPLOADS_DIR]:
            os.makedirs(directory, exist_ok=True)
        
        # Kimi API设置
        self.KIMI_API_KEY = os.getenv("KIMI_API_KEY", "")
        self.KIMI_API_URL = os.getenv("KIMI_API_URL", "https://api.moonshot.cn/v1")
        
        # TTS设置
        self.TTS_DEFAULT_VOICE = "normal"  # 默认语音风格
        self.TTS_MAX_TEXT_LENGTH = 300  # 单次TTS的最大文本长度
        
        # 语音识别设置
        self.SPEECH_MODELS_DIR = os.path.join(self.BASE_DIR, "speech_models")
        self.SPEECH_DEFAULT_LANGUAGE = "zh-cn"
        
        # 内存设置
        self.MEMORY_MAX_CACHE_SIZE = 100  # 最大缓存对话数量
        
        # 其他应用设置
        self.DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
        
    @property
    def kimi_api_credentials(self) -> Dict[str, str]:
        """获取Kimi API凭据"""
        return {
            "api_key": self.KIMI_API_KEY,
            "api_url": self.KIMI_API_URL
        }
    
    @property
    def available_voice_styles(self) -> Dict[str, str]:
        """获取可用的语音风格"""
        return {
            "normal": "标准女声 (小小)",
            "cheerful": "活泼女声 (小意)",
            "serious": "严肃男声 (云健)",
            "gentle": "温柔男声 (云溪)",
            "cute": "可爱女声 (小小)"
        }

# 创建设置实例
settings = Settings()