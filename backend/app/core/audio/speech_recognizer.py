"""
语音识别服务 - FastAPI适配版本
整合Vosk和混合语音识别器
"""
import os
import asyncio
import json
import tempfile
from typing import Dict, Optional, List, Any, Union, BinaryIO
from pathlib import Path
import base64

from app.config.config import settings

# 定义语音识别服务类
class SpeechRecognizer:
    """语音识别服务，提供本地和远程混合模式"""
    
    def __init__(self, models_dir: Optional[Path] = None):
        """
        初始化语音识别服务
        
        Args:
            models_dir: 语音模型目录
        """
        # 设置模型目录
        self.models_dir = models_dir or settings.BASE_DIR / "speech_models"
        os.makedirs(self.models_dir, exist_ok=True)
        
        # 模型缓存
        self.recognizers = {}
        
        # 状态
        self.initialized = False
        self.server_available = False
        
        # 配置
        self.config = {
            "default_language": "zh-cn",
            "use_server": False,  # 默认不使用服务器，除非服务器检查成功
            "fallback_to_local": True,
            "auto_detect_language": False,
            "vad_sensitivity": 0.5,
            "silence_threshold": 0.8
        }
    
    async def initialize(self):
        """初始化语音识别系统"""
        # 已经初始化则返回
        if self.initialized:
            return True
        
        try:
            # 检查并加载Vosk模型
            await self._init_vosk_models()
            
            # 检查服务器可用性
            self.server_available = await self._check_server_connection()
            
            # 标记为已初始化
            self.initialized = True
            
            print(f"语音识别服务初始化完成，本地模型: {len(self.recognizers)}，服务器: {'可用' if self.server_available else '不可用'}")
            return True
        
        except Exception as e:
            print(f"初始化语音识别服务失败: {str(e)}")
            return False
    
    async def _init_vosk_models(self):
        """初始化Vosk模型"""
        # 注意：这里延迟导入Vosk，因为它可能是一个可选依赖
        try:
            from vosk import Model, KaldiRecognizer, SetLogLevel
            
            # 设置日志级别
            SetLogLevel(-1)  # 关闭日志
            
            # 检查模型目录中的模型
            model_dirs = [
                d for d in os.listdir(self.models_dir) 
                if os.path.isdir(os.path.join(self.models_dir, d)) and d.startswith("vosk-model-")
            ]
            
            if not model_dirs:
                print("未找到Vosk模型")
                return
            
            # 加载每个模型
            for model_dir in model_dirs:
                try:
                    model_path = os.path.join(self.models_dir, model_dir)
                    
                    # 从模型名称推断语言
                    if "cn" in model_dir:
                        language = "zh-cn"
                    elif "ja" in model_dir:
                        language = "ja"
                    elif "en" in model_dir:
                        language = "en-us"
                    else:
                        # 尝试从model_dir提取
                        parts = model_dir.split("-")
                        language = parts[2] if len(parts) > 2 else "unknown"
                    
                    print(f"加载Vosk模型: {model_dir}, 语言: {language}")
                    
                    # 创建模型和识别器
                    model = Model(model_path)
                    recognizer = KaldiRecognizer(model, 16000)
                    recognizer.SetWords(True)  # 启用词级时间戳
                    
                    # 保存到缓存
                    self.recognizers[language] = {
                        "recognizer": recognizer,
                        "model": model,
                        "model_id": model_dir
                    }
                    
                    print(f"已加载Vosk模型: {model_dir}")
                
                except Exception as e:
                    print(f"加载Vosk模型出错 {model_dir}: {str(e)}")
        
        except ImportError:
            print("Vosk库未安装，本地语音识别将不可用")
    
    async def _check_server_connection(self):
        """检查服务器连接状态"""
        # 实际应用中，这里应该检查语音识别服务器连接
        # 例如，尝试发送一个测试请求
        
        # 模拟实现
        await asyncio.sleep(0.1)
        
        # 默认不启用服务器
        return False
    
    async def recognize_audio(self, 
                            audio_data: Union[bytes, str, BinaryIO], 
                            language: str = "zh-cn",
                            force_local: bool = False,
                            force_server: bool = False) -> Dict[str, Any]:
        """
        识别音频数据
        
        Args:
            audio_data: 音频数据，可以是字节、Base64字符串或文件对象
            language: 语言代码，默认为"zh-cn"
            force_local: 强制使用本地识别
            force_server: 强制使用服务器识别
            
        Returns:
            识别结果字典
        """
        # 确保已初始化
        if not self.initialized:
            await self.initialize()
        
        # 处理音频数据
        audio_bytes = await self._prepare_audio_data(audio_data)
        
        # 确定使用哪种模式
        use_server = False
        if force_local:
            use_server = False
        elif force_server:
            use_server = self.server_available
        else:
            # 自动决定：优先使用配置指定的方式
            use_server = self.config["use_server"] and self.server_available
        
        try:
            # 执行识别
            if use_server:
                result = await self._server_recognition(audio_bytes, language)
            else:
                result = await self._local_recognition(audio_bytes, language)
            
            return result
        
        except Exception as e:
            error_msg = f"语音识别失败: {str(e)}"
            print(error_msg)
            
            # 如果服务器识别失败并且配置允许回退，尝试本地识别
            if use_server and self.config["fallback_to_local"] and not force_server:
                try:
                    print("服务器识别失败，回退到本地识别")
                    return await self._local_recognition(audio_bytes, language)
                except Exception as inner_e:
                    print(f"本地识别也失败: {str(inner_e)}")
            
            # 返回错误结果
            return {
                "success": False,
                "text": "",
                "error": error_msg,
                "language": language,
                "confidence": 0.0
            }
    
    async def _prepare_audio_data(self, audio_data: Union[bytes, str, BinaryIO]) -> bytes:
        """
        准备音频数据
        
        Args:
            audio_data: 音频数据，可以是字节、Base64字符串或文件对象
            
        Returns:
            处理后的音频字节数据
        """
        # 如果是字节数据，直接返回
        if isinstance(audio_data, bytes):
            return audio_data
        
        # 如果是Base64字符串，解码
        if isinstance(audio_data, str):
            try:
                return base64.b64decode(audio_data)
            except Exception as e:
                raise ValueError(f"无法解码Base64字符串: {str(e)}")
        
        # 如果是文件对象，读取内容
        if hasattr(audio_data, 'read'):
            return audio_data.read()
        
        raise ValueError("不支持的音频数据类型")
    
    async def _local_recognition(self, audio_bytes: bytes, language: str) -> Dict[str, Any]:
        """
        使用本地Vosk模型识别
        
        Args:
            audio_bytes: 音频数据
            language: 语言代码
            
        Returns:
            识别结果字典
        """
        # 检查是否有对应语言的本地模型
        if language not in self.recognizers:
            raise ValueError(f"没有可用的{language}本地模型")
        
        recognizer = self.recognizers[language]["recognizer"]
        
        # 将音频数据传递给识别器
        if recognizer.AcceptWaveform(audio_bytes):
            result_json = recognizer.Result()
            result = json.loads(result_json)
            
            return {
                "success": True,
                "text": result.get("text", ""),
                "language": language,
                "confidence": 0.8,  # Vosk没有置信度，使用一个较高的默认值
                "word_timestamps": result.get("result", []),
                "source": "local"
            }
        else:
            # 没有有效结果
            partial_json = recognizer.PartialResult()
            partial = json.loads(partial_json)
            
            return {
                "success": True,
                "text": partial.get("partial", ""),
                "language": language,
                "confidence": 0.5,  # 部分结果置信度较低
                "source": "local"
            }
    
    async def _server_recognition(self, audio_bytes: bytes, language: str) -> Dict[str, Any]:
        """
        使用服务器识别
        
        Args:
            audio_bytes: 音频数据
            language: 语言代码
            
        Returns:
            识别结果字典
        """
        # 实际应用中，这里应该发送请求到语音识别服务器
        # 例如，使用HTTP请求上传音频数据并获取结果
        
        # 模拟实现
        await asyncio.sleep(1)
        
        # 模拟结果
        if language == "ja":
            text = "これはテスト応答です"
        else:
            text = "这是一个测试响应"
        
        return {
            "success": True,
            "text": text,
            "language": language,
            "confidence": 0.95,
            "source": "server"
        }
    
    async def list_available_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        # 确保已初始化
        if not self.initialized:
            await self.initialize()
        
        models = []
        
        # 本地模型
        for language, info in self.recognizers.items():
            models.append({
                "id": info["model_id"],
                "language": language,
                "name": f"Vosk {language} 模型",
                "size_mb": 0,  # 实际实现中应计算模型大小
                "status": "installed",
                "accuracy": "中等",
                "source": "local"
            })
        
        # 服务器模型
        if self.server_available:
            # 模拟服务器上可用的模型
            server_models = [
                {
                    "id": "server-zh-cn",
                    "language": "zh-cn",
                    "name": "服务器中文模型",
                    "size_mb": 0,
                    "status": "available",
                    "accuracy": "高",
                    "source": "server"
                },
                {
                    "id": "server-en-us",
                    "language": "en-us",
                    "name": "服务器英语模型",
                    "size_mb": 0,
                    "status": "available",
                    "accuracy": "高",
                    "source": "server"
                }
            ]
            models.extend(server_models)
        
        return models
    
    async def get_supported_languages(self) -> List[Dict[str, Any]]:
        """获取支持的语言列表"""
        # 确保已初始化
        if not self.initialized:
            await self.initialize()
        
        # 基本支持的语言
        languages = [
            {
                "code": "zh-cn",
                "name": "中文",
                "model_size": "小型",
                "offline_available": "zh-cn" in self.recognizers
            },
            {
                "code": "ja",
                "name": "日语",
                "model_size": "小型",
                "offline_available": "ja" in self.recognizers
            },
            {
                "code": "en-us",
                "name": "英语 (美国)",
                "model_size": "中型",
                "offline_available": "en-us" in self.recognizers
            }
        ]
        
        return languages
    
    async def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """更新配置"""
        # 更新配置字典
        for key, value in new_config.items():
            if key in self.config:
                self.config[key] = value
        
        return self.config
    
    async def download_model(self, model_id: str) -> Dict[str, Any]:
        """
        下载语音模型
        
        Args:
            model_id: 模型ID
            
        Returns:
            下载状态
        """
        # 实际应用中，这里应该实现模型下载逻辑
        # 例如，从服务器下载并解压模型文件
        
        # 模拟实现
        print(f"开始下载模型: {model_id}")
        
        # 模拟下载延迟
        for i in range(5):
            await asyncio.sleep(1)
            print(f"下载进度: {(i+1)*20}%")
        
        print(f"模型 {model_id} 下载完成")
        
        # 返回下载状态
        return {
            "success": True,
            "model_id": model_id,
            "status": "downloaded",
            "message": f"模型 {model_id} 下载完成"
        }

# 单例模式
_speech_service = None

def get_speech_service() -> SpeechRecognizer:
    """获取语音识别服务单例"""
    global _speech_service
    if _speech_service is None:
        _speech_service = SpeechRecognizer()
    return _speech_service

async def initialize_speech_system() -> bool:
    """初始化语音识别系统"""
    service = get_speech_service()
    return await service.initialize()

async def recognize_speech(audio_data, language="zh-cn", 
                          force_local=False, force_server=False) -> Dict[str, Any]:
    """识别语音"""
    service = get_speech_service()
    return await service.recognize_audio(
        audio_data=audio_data,
        language=language,
        force_local=force_local,
        force_server=force_server
    )