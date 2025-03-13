# tts_simple.py
import asyncio
import re
import os
import tempfile

# 导入Edge TTS
try:
    from edge_tts import Communicate
except ImportError:
    print("请安装 edge-tts: pip install edge-tts")
    raise

# 语音风格映射
VOICE_STYLES = {
    "normal": "zh-CN-XiaoxiaoNeural",  # 标准女声
    "cheerful": "zh-CN-XiaoyiNeural",   # 活泼女声
    "serious": "zh-CN-YunjianNeural",   # 严肃男声
    "gentle": "zh-CN-YunxiNeural",      # 温柔男声
    "cute": "zh-CN-XiaoxiaoNeural"      # 可爱女声（使用稳定的XiaoxiaoNeural）
}

# 清理文本，移除Markdown格式符号，并添加语义转换
def basic_symbol_cleanup(text):
    """
    基本符号清理函数 - 处理Markdown、HTML等格式，不改变文本语义
    """
    # 移除Markdown格式
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # 粗体
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # 斜体
    text = re.sub(r'`(.*?)`', r'\1', text)        # 代码
    text = re.sub(r'#+ (.+)', r'\1', text)        # 标题
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # 链接
    
    # 移除HTML标签
    text = re.sub(r'<[^>]*>', '', text)
    
    # 处理连续空格和空行
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    
    return text.strip()

def semantic_transformation_for_tts(text):
    """
    语义转换函数 - 将特定符号转换为更适合语音朗读的形式
    """
    # 处理年代和日期中的连字符
    text = re.sub(r'(\d+)\s*-\s*(\d+)年', r'\1年至\2年', text)
    text = re.sub(r'(\d+)年\s*-\s*(\d+)年', r'\1年至\2年', text)
    text = re.sub(r'(\d+)\s*-\s*(\d+)月', r'\1月至\2月', text)
    text = re.sub(r'(\d+)月\s*-\s*(\d+)月', r'\1月至\2月', text)
    text = re.sub(r'(\d+)\s*-\s*(\d+)日', r'\1日至\2日', text)
    text = re.sub(r'(\d+)日\s*-\s*(\d+)日', r'\1日至\2日', text)
    
    # 处理生卒年月
    text = re.sub(r'生卒[：:]\s*(\d+)年?\s*-\s*(\d+)年?', r'生卒：\1年至\2年', text)
    text = re.sub(r'([公元前]?\d+)\s*-\s*([公元前]?\d+)', r'\1至\2', text)
    
    # 处理括号内容
    text = re.sub(r'（(.*?)）', r'，也就是\1，', text)
    text = re.sub(r'\((.*?)\)', r'，也就是\1，', text)
    
    # 处理引号
    text = re.sub(r'[""](.+?)[""]', r'"\1"', text)
    
    # 处理破折号
    text = re.sub(r'——', '，', text)
    
    # 处理省略号
    text = re.sub(r'\.{3,}', '等等', text)
    text = re.sub(r'。{3,}', '等等', text)
    text = re.sub(r'…+', '等等', text)
    
    # 处理冒号后的内容
    text = re.sub(r'([^，。；：！？\n])：', r'\1是', text)
    
    # 处理数字与单位之间的空格
    text = re.sub(r'(\d+)\s+([a-zA-Z%㎡㎞元吨千克])', r'\1\2', text)
    
    # 处理百分比
    text = re.sub(r'(\d+)%', r'\1百分比', text)
    
    # 处理特殊字符
    replacements = {
        '&gt;': '大于',
        '&lt;': '小于',
        '&amp;': '和',
        '&': '和',
        '/': '或',
        '|': '或',
        '>': '大于',
        '<': '小于',
        '=': '等于',
        '+': '加',
        '-': '减',
        '×': '乘以',
        '÷': '除以'
    }
    
    for symbol, replacement in replacements.items():
        text = text.replace(symbol, replacement)
    
    return text

def clean_text_for_tts(text):
    """
    完整的TTS文本清理函数，结合基本符号清理和语义转换
    """
    # 先进行基本符号清理
    text = basic_symbol_cleanup(text)
    
    # 再进行语义转换
    text = semantic_transformation_for_tts(text)
    
    return text

# 异步生成语音
async def generate_speech_async(text, voice, output_file):
    """使用Edge TTS生成语音"""
    try:
        # 创建通信对象
        communicate = Communicate(text, voice, rate="+0%", volume="+0%", pitch="+0Hz")
        
        # 合成语音并保存到文件
        await communicate.save(output_file)
        return True
    except Exception as e:
        print(f"生成语音失败: {e}")
        if os.path.exists(output_file):
            os.unlink(output_file)
        return False

# 同步接口
def text_to_speech(text, style="normal"):
    """将文本转换为语音，返回音频文件路径"""
    if not text or len(text.strip()) == 0:
        print("警告: 空文本无法生成语音")
        return None
    
    # 清理文本
    clean_text = clean_text_for_tts(text)
    if not clean_text or len(clean_text.strip()) == 0:
        print("警告: 清理后的文本为空")
        return None
    
    # 获取对应的语音模型
    voice = VOICE_STYLES.get(style, "zh-CN-XiaoxiaoNeural")
    
    # 创建临时文件
    # # 指定自定义临时目录
    # custom_temp_dir = "D:/my_temp_files"  # 替换为你想使用的目录路径

    # # 确保目录存在
    # os.makedirs(custom_temp_dir, exist_ok=True)
    # with tmpfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir=custom_temp_dir) as temp_file:
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_file:
        output_file = temp_file.name
    
    try:
        # 创建事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 运行异步函数
        success = loop.run_until_complete(generate_speech_async(clean_text, voice, output_file))
        loop.close()
        
        if success:
            return output_file
        else:
            return None
    except Exception as e:
        print(f"生成语音出错: {e}")
        if os.path.exists(output_file):
            os.unlink(output_file)
        return None

# 测试代码
if __name__ == "__main__":
    test_text = "这是一个测试文本，将被转换为语音。我正在测试不同的语音风格。"
    
    for style in VOICE_STYLES.keys():
        print(f"测试语音风格: {style}")
        audio_path = text_to_speech(test_text, style)
        if audio_path:
            print(f"生成的音频文件: {audio_path}")
            # 在这里可以添加播放音频的代码
        else:
            print(f"生成失败")