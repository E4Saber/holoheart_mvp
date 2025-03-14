# 在合适的模块中（例如 app/utils/audio_utils.py）

import os
from uuid import uuid4
from pydub import AudioSegment
from app.config.config import settings

async def merge_audio_segments(segment_paths, output_filename=None):
    """
    合并多个音频片段为一个完整的音频文件
    
    参数:
        segment_paths (list): 音频片段文件路径列表
        output_filename (str, optional): 输出文件名，如果未提供则自动生成
        
    返回:
        tuple: (完整音频路径, 音频URL)
    """
    if not segment_paths:
        return None, None
        
    # 如果没有提供输出文件名，生成一个唯一文件名
    if not output_filename:
        output_filename = f"complete_{uuid4()}.mp3"
        
    # 构建输出文件的完整路径
    output_path = os.path.join(settings.AUDIO_FILES_DIR, output_filename)
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 如果只有一个片段，直接复制
    if len(segment_paths) == 1:
        import shutil
        shutil.copy2(segment_paths[0], output_path)
    else:
        # 合并多个音频片段
        try:
            print(f"合并音频片段[0]: {segment_paths[0]}")
            combined = AudioSegment.from_mp3(segment_paths[0])
            for segment_path in segment_paths[1:]:
                print(f"合并音频片段: {segment_path}")
                segment = AudioSegment.from_mp3(segment_path)
                combined += segment
                
            # 导出合并后的音频
            combined.export(output_path, format="mp3")
        except Exception as e:
            print(f"合并音频失败: {e}")
            return None, None
    
    # 返回文件路径和相对URL
    audio_url = f"/audio/{output_filename}"
    return output_path, audio_url