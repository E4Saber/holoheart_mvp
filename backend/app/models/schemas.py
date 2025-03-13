from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from uuid import uuid4

class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str  # "user" 或 "assistant" 或 "system"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))
    audio_path: Optional[str] = None

class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    conversation_id: Optional[str] = Field(default_factory=lambda: str(uuid4()))
    stream: bool = False
    tts_enabled: bool = True
    voice_style: str = "normal"
    load_memories: bool = False
    history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    """聊天响应模型"""
    conversation_id: str
    user_message: ChatMessage
    assistant_message: ChatMessage
    audio_url: Optional[str] = None

class TextToSpeechRequest(BaseModel):
    """文本转语音请求模型"""
    text: str
    voice_style: str = "normal"

class ConversationHistory(BaseModel):
    """对话历史模型"""
    conversation_id: str
    messages: List[ChatMessage]
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class MemorySearchRequest(BaseModel):
    """记忆搜索请求模型"""
    query: str
    date: Optional[str] = None
    limit: int = 10

class MemorySummary(BaseModel):
    """记忆摘要模型"""
    memory_id: str
    summary: str
    timestamp: str
    tags: List[str] = []

class MemoryDetail(BaseModel):
    """记忆详情模型"""
    memory_id: str
    summary: str
    timestamp: str
    messages: List[ChatMessage]
    tags: List[str] = []

class MemoryCreateRequest(BaseModel):
    """创建记忆请求模型"""
    conversation_id: str
    summary: Optional[str] = None
    tags: List[str] = []

class ApiConfig(BaseModel):
    """API配置模型"""
    api_key: str
    api_url: str = "https://api.moonshot.cn/v1"

class VoiceStyle(BaseModel):
    """语音风格模型"""
    id: str
    name: str
    description: str
    sample_url: Optional[str] = None

# 添加语音识别相关模型

class SpeechRecognitionRequest(BaseModel):
    """语音识别请求模型"""
    audio_data: Union[str, bytes]  # Base64编码的音频数据或二进制音频数据
    language: str = "zh-cn"
    model_id: Optional[str] = None  # 可选指定模型ID
    max_alternatives: int = 1  # 返回备选结果数量
    include_timestamps: bool = False  # 是否包含单词级别的时间戳

class SpeechRecognitionResponse(BaseModel):
    """语音识别响应模型"""
    success: bool
    text: str
    language: str
    confidence: float
    alternatives: Optional[List[Dict[str, Any]]] = None
    word_timestamps: Optional[List[Dict[str, Any]]] = None

class SpeechModel(BaseModel):
    """语音识别模型信息"""
    id: str
    language: str
    name: str
    size_mb: float
    status: str  # installed, available, downloading
    accuracy: str
    download_url: Optional[str] = None
    last_updated: Optional[datetime] = None

class SpeechLanguage(BaseModel):
    """支持的语音语言"""
    code: str
    name: str
    model_size: str
    offline_available: bool
    supported_models: List[str] = []

class SpeechRecognitionSettings(BaseModel):
    """语音识别设置"""
    default_language: str = "zh-cn"
    use_server: bool = True
    fallback_to_local: bool = True
    auto_detect_language: bool = False
    vad_sensitivity: float = 0.5  # 语音活动检测敏感度
    silence_threshold: float = 0.8  # 静音检测阈值