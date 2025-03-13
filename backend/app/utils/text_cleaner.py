import re

def clean_text_for_tts(text):
    """
    清理文本，使其适合语音合成
    - 移除Markdown格式符号
    - 清理多余空格
    - 处理特殊字符和缩写

    进阶思考：对于某些辅助性的符号，需要转义
    """
    # 移除Markdown链接，只保留文本
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # 移除Markdown格式符号
    text = re.sub(r'(\*\*|__)(.*?)\1', r'\2', text)  # 粗体
    text = re.sub(r'(\*|_)(.*?)\1', r'\2', text)     # 斜体
    text = re.sub(r'~~(.*?)~~', r'\1', text)         # 删除线
    text = re.sub(r'`([^`]+)`', r'\1', text)         # 代码
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)  # 代码块
    # 移除列表符号（无序列表使用 -、* 或 + 开头）
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)

    # 移除有序列表（数字后跟点和空格）
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # 移除标题符号 (#)
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    
    # 移除列表符号
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
    
    # 移除引用符号 (>)
    text = re.sub(r'^\s*>\s+', '', text, flags=re.MULTILINE)
    
    # 处理HTML标签
    text = re.sub(r'<[^>]*>', '', text)
    
    # 处理转义字符
    text = re.sub(r'\\([\\`*_{}[\]()#+-.!])', r'\1', text)
    
    # 替换多个空格为单个空格
    text = re.sub(r'\s+', ' ', text)
    
    # 处理一些常见缩写和符号
    replacements = {
        '&amp;': '和',
        '&lt;': '小于',
        '&gt;': '大于',
        '&quot;': '"',
        '&apos;': "'",
        '&#39;': "'",
        '&nbsp;': ' ',
        '---': '',
        '--': '',
        '==': '',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # 最后清理空行和首尾空格
    text = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
    text = text.strip()
    
    return text

def split_text_for_tts(text, max_length=300):
    """
    将长文本分割成适合TTS的段落
    - 尝试在句子边界分割
    - 确保每段不超过最大长度
    """
    # 如果文本很短，直接返回
    if len(text) <= max_length:
        return [text]
    
    # 按句子分割点切分文本
    split_pattern = r'(?<=[。！？.!?])'
    sentences = re.split(split_pattern, text)
    
    # 组合句子成段落，每段不超过max_length
    paragraphs = []
    current_paragraph = ""
    
    for sentence in sentences:
        # 跳过空句子
        if not sentence.strip():
            continue
            
        # 如果单个句子超过最大长度，则按逗号分割
        if len(sentence) > max_length:
            comma_parts = re.split(r'(?<=[，,])', sentence)
            for part in comma_parts:
                if not part.strip():
                    continue
                    
                # 如果当前段落加上这部分会超长，先保存当前段落
                if len(current_paragraph) + len(part) > max_length:
                    if current_paragraph:
                        paragraphs.append(current_paragraph.strip())
                        current_paragraph = ""
                
                # 如果单个部分仍然超长，则强制分割
                if len(part) > max_length:
                    # 将长部分分割成固定长度的块
                    for i in range(0, len(part), max_length):
                        chunk = part[i:i+max_length]
                        paragraphs.append(chunk.strip())
                else:
                    current_paragraph += part
        
        # 如果当前段落加上这个句子会超长，先保存当前段落
        elif len(current_paragraph) + len(sentence) > max_length:
            if current_paragraph:
                paragraphs.append(current_paragraph.strip())
                current_paragraph = ""
            current_paragraph += sentence
        else:
            current_paragraph += sentence
    
    # 添加最后一个段落
    if current_paragraph:
        paragraphs.append(current_paragraph.strip())
    
    return paragraphs

# 辅助函数：查找句子结束位置
def find_sentence_end(text: str) -> int:
    """查找文本中句子的结束位置"""
    end_chars = ["。", "？", "！", ".", "?", "!"]
    positions = [text.find(char) for char in end_chars]
    valid_positions = [pos for pos in positions if pos != -1]
    
    if valid_positions:
        return min(valid_positions)
    else:
        # 如果没有找到句号等标点，但文本已经足够长，也可以直接返回
        if len(text) > 50:
            return len(text) - 1
        return -1