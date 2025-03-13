import os
import base64
import tempfile
import time
from enum import Enum
from typing import Optional, Dict, List, Union, Any
import requests
import numpy as np
from scipy.io.wavfile import write as write_wav

class VoiceStyle(Enum):
    """预定义的语音风格"""
    NORMAL = "normal"
    CHEERFUL = "cheerful" 
    SERIOUS = "serious"
    GENTLE = "gentle"
    CUTE = "cute"

class TTSEngine:
    """
    基础TTS引擎接口
    """
    def synthesize(self, text: str, voice_style: str = None) -> bytes:
        """
        将文本转换为语音
        :param text: 要转换的文本
        :param voice_style: 语音风格
        :return: 音频数据
        """
        raise NotImplementedError("子类必须实现此方法")
    
    def get_available_voices(self) -> List[str]:
        """
        获取可用的语音列表
        :return: 语音列表
        """
        raise NotImplementedError("子类必须实现此方法")

class EdgeTTSEngine(TTSEngine):
    """
    使用Microsoft Edge TTS API的语音合成引擎
    优点: 免费使用，音质较好，支持多种语音和语言
    """
    def __init__(self):
        try:
            import edge_tts
            self.edge_tts = edge_tts
            self.communicate_class = edge_tts.Communicate
        except ImportError:
            raise ImportError("请安装edge-tts库: pip install edge-tts")
        
        # 声音风格到具体Voice的映射
        self.style_to_voice = {
            "normal": "zh-CN-XiaoxiaoNeural",    # 标准女声
            "cheerful": "zh-CN-XiaoyiNeural",     # 活泼女声
            "serious": "zh-CN-YunjianNeural",     # 严肃男声
            "gentle": "zh-CN-YunxiNeural",        # 温柔男声
            "cute": "zh-CN-XiaoxiaoNeural",       # 可爱女声 (更改为使用XiaoxiaoNeural作为备选)
        }
        
        # 默认语音参数
        self.default_rate = "+0%"  # 语速 (-100% ~ +100%)
        self.default_volume = "+0%"  # 音量 (-100% ~ +100%)
        self.default_pitch = "+0Hz"  # 音调 (使用Hz单位，如 +0Hz, +10Hz, -5Hz)
    
    async def _synthesize_async(self, text: str, voice: str) -> bytes:
        """异步合成语音"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
            temp_path = temp_file.name
        
        try:
            # 创建通信对象
            communicate = self.communicate_class(
                text, 
                voice,
                rate=self.default_rate,
                volume=self.default_volume,
                pitch=self.default_pitch
            )
            
            # 合成语音并保存到临时文件
            await communicate.save(temp_path)
            
            # 读取文件内容
            with open(temp_path, "rb") as audio_file:
                audio_data = audio_file.read()
            
            return audio_data
        
        finally:
            # 删除临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def synthesize(self, text: str, voice_style: str = "normal") -> bytes:
        """
        将文本转换为语音
        :param text: 要转换的文本
        :param voice_style: 语音风格
        :return: 音频数据
        """
        import asyncio
        
        # 获取对应的语音
        voice = self.style_to_voice.get(voice_style, self.style_to_voice["normal"])
        
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 运行异步合成
            audio_data = loop.run_until_complete(self._synthesize_async(text, voice))
            return audio_data
        finally:
            loop.close()
    
    def get_available_voices(self) -> List[str]:
        """获取可用的语音风格列表"""
        return list(self.style_to_voice.keys())
    
    async def list_voices(self) -> List[Dict[str, Any]]:
        """列出所有可用的Edge TTS语音"""
        return await self.edge_tts.list_voices()

class PaddleSpeechTTSEngine(TTSEngine):
    """
    使用PaddleSpeech的TTS引擎
    优点: 开源，无需联网，高度可定制
    """
    def __init__(self, use_gpu: bool = False):
        try:
            from paddlespeech.cli.tts.infer import TTSExecutor
            self.tts = TTSExecutor()
            self.use_gpu = use_gpu
        except ImportError:
            raise ImportError("请安装PaddleSpeech: pip install paddlespeech")
        
        # 声音风格映射
        self.style_to_config = {
            "normal": {"am": "fastspeech2_cnndecoder_csmsc", "voc": "hifigan_csmsc"},
            "cheerful": {"am": "fastspeech2_mix", "voc": "hifigan_csmsc", "spk_id": 9},
            "serious": {"am": "fastspeech2_mix", "voc": "hifigan_csmsc", "spk_id": 0},
            "gentle": {"am": "fastspeech2_mix", "voc": "hifigan_csmsc", "spk_id": 11},
            "cute": {"am": "fastspeech2_mix", "voc": "hifigan_csmsc", "spk_id": 20},
        }
    
    def synthesize(self, text: str, voice_style: str = "normal") -> bytes:
        """
        将文本转换为语音
        :param text: 要转换的文本
        :param voice_style: 语音风格
        :return: 音频数据
        """
        # 获取配置
        config = self.style_to_config.get(voice_style, self.style_to_config["normal"])
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_path = temp_file.name
        
        try:
            # 合成语音
            am = config.get("am", "fastspeech2_cnndecoder_csmsc")
            voc = config.get("voc", "hifigan_csmsc")
            spk_id = config.get("spk_id", 0)
            
            kwargs = {
                "text": text,
                "output": temp_path,
                "am": am,
                "voc": voc,
                "lang": "zh",
                "device": "gpu" if self.use_gpu else "cpu"
            }
            
            if "spk_id" in config:
                kwargs["spk_id"] = spk_id
                
            self.tts(**kwargs)
            
            # 读取文件内容
            with open(temp_path, "rb") as audio_file:
                audio_data = audio_file.read()
            
            return audio_data
        
        finally:
            # 删除临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def get_available_voices(self) -> List[str]:
        """获取可用的语音风格列表"""
        return list(self.style_to_config.keys())

class PersonalizedTTSEngine(TTSEngine):
    """
    支持自定义语音包的TTS引擎
    可以使用用户上传的语音样本创建个性化语音
    """
    def __init__(self, voice_samples_dir: str = "voice_samples"):
        self.voice_samples_dir = voice_samples_dir
        self.custom_voices = {}
        self.default_engine = EdgeTTSEngine()
        
        # 确保语音样本目录存在
        os.makedirs(voice_samples_dir, exist_ok=True)
        
        # 加载已有的自定义语音
        self._load_custom_voices()
    
    def _load_custom_voices(self):
        """加载已有的自定义语音"""
        for voice_name in os.listdir(self.voice_samples_dir):
            voice_dir = os.path.join(self.voice_samples_dir, voice_name)
            if os.path.isdir(voice_dir) and os.listdir(voice_dir):
                self.custom_voices[voice_name] = voice_dir
    
    def create_custom_voice(self, voice_name: str, audio_samples: List[bytes], 
                           transcripts: List[str]) -> bool:
        """
        创建自定义语音
        :param voice_name: 语音名称
        :param audio_samples: 音频样本列表
        :param transcripts: 对应的文本列表
        :return: 是否成功
        """
        # 创建语音目录
        voice_dir = os.path.join(self.voice_samples_dir, voice_name)
        os.makedirs(voice_dir, exist_ok=True)
        
        # 保存音频样本和文本
        for i, (audio, text) in enumerate(zip(audio_samples, transcripts)):
            audio_path = os.path.join(voice_dir, f"sample_{i}.wav")
            text_path = os.path.join(voice_dir, f"sample_{i}.txt")
            
            # 保存音频
            with open(audio_path, "wb") as f:
                f.write(audio)
            
            # 保存文本
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(text)
        
        # 记录自定义语音
        self.custom_voices[voice_name] = voice_dir
        
        # 训练模型 (这里只是一个占位符，真实实现需要接入语音克隆模型)
        # 在这个简化版本中，我们只保存样本，不进行实际训练
        
        return True
    
    def synthesize(self, text: str, voice_style: str = "normal") -> bytes:
        """
        将文本转换为语音
        :param text: 要转换的文本
        :param voice_style: 语音风格或自定义语音名称
        :return: 音频数据
        """
        # 检查是否为自定义语音
        if voice_style in self.custom_voices:
            # 这里应该调用语音克隆模型进行合成
            # 在真实场景中，需要实现语音克隆逻辑
            # 由于复杂度原因，这里简化为使用默认引擎
            print(f"使用自定义语音: {voice_style}")
            return self.default_engine.synthesize(text, "normal")
        else:
            # 使用默认引擎
            return self.default_engine.synthesize(text, voice_style)
    
    def get_available_voices(self) -> List[str]:
        """获取可用的语音列表"""
        # 合并默认语音和自定义语音
        default_voices = self.default_engine.get_available_voices()
        custom_voices = list(self.custom_voices.keys())
        return default_voices + custom_voices

class TTSManager:
    """
    TTS管理器，提供统一的接口
    """
    def __init__(self, engine: str = "edge", cache_dir: str = "tts_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
        # 选择引擎
        if engine.lower() == "edge":
            self.engine = EdgeTTSEngine()
        elif engine.lower() == "paddle":
            self.engine = PaddleSpeechTTSEngine()
        elif engine.lower() == "personalized":
            self.engine = PersonalizedTTSEngine()
        else:
            raise ValueError(f"不支持的引擎: {engine}")
    
    def text_to_speech(self, text: str, voice_style: str = "normal", use_cache: bool = True) -> bytes:
        """
        将文本转换为语音
        :param text: 要转换的文本
        :param voice_style: 语音风格
        :param use_cache: 是否使用缓存
        :return: 音频数据
        """
        # 如果启用缓存，检查缓存中是否有这段文本的语音
        if use_cache:
            cache_key = f"{voice_style}_{hash(text)}.mp3"
            cache_path = os.path.join(self.cache_dir, cache_key)
            
            if os.path.exists(cache_path):
                with open(cache_path, "rb") as f:
                    return f.read()
        
        # 没有缓存或不使用缓存，合成语音
        audio_data = self.engine.synthesize(text, voice_style)
        
        # 如果启用缓存，保存到缓存
        if use_cache:
            with open(cache_path, "wb") as f:
                f.write(audio_data)
        
        return audio_data
    
    def get_available_voices(self) -> List[str]:
        """获取可用的语音列表"""
        return self.engine.get_available_voices()

def create_audio_html(audio_data: bytes) -> str:
    """
    创建可嵌入HTML的音频元素
    :param audio_data: 音频数据
    :return: HTML代码
    """
    # 转换为base64
    b64_audio = base64.b64encode(audio_data).decode()
    
    # 创建HTML
    audio_html = f"""
    <audio controls autoplay style="width:100%; max-width:600px">
        <source src="data:audio/mp3;base64,{b64_audio}" type="audio/mp3">
        您的浏览器不支持音频元素
    </audio>
    """
    return audio_html

def get_voice_style_description(style: str) -> str:
    """获取语音风格的描述"""
    descriptions = {
        "normal": "标准语音 - 清晰自然的女声",
        "cheerful": "活泼语音 - 充满活力的女声",
        "serious": "严肃语音 - 庄重专业的男声",
        "gentle": "温柔语音 - 平缓柔和的男声",
        "cute": "可爱语音 - 甜美俏皮的女声",
    }
    return descriptions.get(style, "自定义语音")

def create_voice_selector_html(available_voices: List[str]) -> str:
    """
    创建语音选择器的HTML
    :param available_voices: 可用的语音列表
    :return: HTML代码
    """
    options_html = ""
    for voice in available_voices:
        description = get_voice_style_description(voice)
        options_html += f'<option value="{voice}">{voice.capitalize()} - {description}</option>'
    
    selector_html = f'''
    <div style="margin:15px 0;">
        <label for="voice-selector" style="font-weight:bold;">语音风格:</label>
        <select id="voice-selector" style="width:100%; padding:8px; margin-top:5px; border-radius:4px; border:1px solid #ccc;">
            {options_html}
        </select>
    </div>
    <script>
        // 添加事件监听器
        document.getElementById('voice-selector').addEventListener('change', function() {{
            // 这里只存储选择，实际应用会通过Streamlit的回调处理
            localStorage.setItem('selected_voice', this.value);
            console.log('选择的语音风格: ' + this.value);
        }});
    </script>
    '''
    return selector_html

# 测试代码
if __name__ == "__main__":
    # 测试TTS管理器
    manager = TTSManager(engine="edge")
    
    test_text = "这是一个语音合成测试，您现在听到的是AI生成的语音。"
    
    print("可用的语音风格:")
    voices = manager.get_available_voices()
    for voice in voices:
        print(f" - {voice}")
    
    print("\n合成测试文本...")
    audio_data = manager.text_to_speech(test_text, "normal")
    
    print(f"生成的音频大小: {len(audio_data)} 字节")
    
    # 保存到文件
    with open("test_output.mp3", "wb") as f:
        f.write(audio_data)
    
    print("测试音频已保存到 test_output.mp3")