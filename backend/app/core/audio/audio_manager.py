"""
音频队列管理器 - FastAPI适配版本
管理音频文件的播放队列和状态跟踪
"""
import asyncio
import time
import queue
import os
from pathlib import Path
from typing import Dict, Optional, List

class AudioManager:
    """音频队列管理器，处理音频播放队列"""
    
    def __init__(self):
        # 音频队列
        self.audio_queue = asyncio.Queue()
        
        # 当前播放状态
        self.current_audio = None
        self.audio_start_time = 0
        self.audio_play_duration = 0
        self.is_playing = False
        
        # 任务和锁
        self.task = None
        self.lock = asyncio.Lock()
    
    async def start(self):
        """启动音频处理任务"""
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._audio_processor())
            print("音频处理任务已启动")
    
    async def stop(self):
        """停止音频处理任务"""
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
            print("音频处理任务已停止")
    
    async def add_to_queue(self, audio_path: str) -> bool:
        """将音频添加到播放队列"""
        if not audio_path or not os.path.exists(audio_path):
            print(f"音频文件不存在: {audio_path}")
            return False
        
        await self.audio_queue.put(audio_path)
        print(f"已将音频添加到队列: {audio_path}")
        
        # 确保处理任务正在运行
        await self.start()
        
        return True
    
    async def clear_queue(self):
        """清空音频队列"""
        async with self.lock:
            # 清空队列
            while not self.audio_queue.empty():
                try:
                    await self.audio_queue.get()
                    self.audio_queue.task_done()
                except Exception:
                    pass
            
            # 重置当前状态
            self.current_audio = None
            self.is_playing = False
            print("音频队列已清空")
    
    async def get_status(self) -> Dict:
        """获取当前音频状态"""
        async with self.lock:
            if self.current_audio and self.is_playing:
                elapsed = time.time() - self.audio_start_time
                remaining = max(0, self.audio_play_duration - elapsed)
                
                return {
                    "playing": self.is_playing,
                    "path": self.current_audio,
                    "remaining": remaining,
                    "elapsed": elapsed,
                    "total": self.audio_play_duration,
                    "queue_size": self.audio_queue.qsize()
                }
            else:
                return {
                    "playing": False,
                    "queue_size": self.audio_queue.qsize()
                }
    
    async def _audio_processor(self):
        """音频处理循环"""
        print("音频处理循环已启动")
        
        try:
            while True:
                # 获取队列大小
                queue_size = self.audio_queue.qsize()
                if queue_size > 0:
                    print(f"队列中有 {queue_size} 个音频等待处理")
                
                # 从队列获取下一个音频
                try:
                    audio_path = await self.audio_queue.get()
                    
                    # 检查文件是否存在
                    if not os.path.exists(audio_path):
                        print(f"音频文件不存在: {audio_path}")
                        self.audio_queue.task_done()
                        continue
                    
                    async with self.lock:
                        # 设置当前播放状态
                        self.current_audio = audio_path
                        self.audio_start_time = time.time()
                        self.is_playing = True
                        
                        # 获取音频时长（估计值）
                        file_size = os.path.getsize(audio_path)
                        # 假设中文语音每字符约需要0.2秒，假设1KB约包含20个字符
                        estimate_chars = file_size / 50
                        play_time = max(2.0, estimate_chars * 0.2)  # 至少2秒
                        self.audio_play_duration = play_time
                    
                    print(f"音频处理开始: {audio_path}, 估计时长: {play_time:.2f}秒")
                    
                    # 在服务端我们不实际播放，只模拟音频播放时长
                    await asyncio.sleep(play_time)
                    
                    async with self.lock:
                        # 更新状态
                        print(f"音频处理完成: {audio_path}")
                        self.current_audio = None
                        self.is_playing = False
                    
                    # 标记任务完成
                    self.audio_queue.task_done()
                
                except asyncio.CancelledError:
                    print("音频处理任务被取消")
                    break
                except Exception as e:
                    print(f"处理音频时出错: {str(e)}")
                    async with self.lock:
                        self.current_audio = None
                        self.is_playing = False
                    
                    # 继续处理下一个
                    self.audio_queue.task_done()
                
                # 短暂等待
                await asyncio.sleep(0.1)
        
        except asyncio.CancelledError:
            print("音频处理循环被取消")
        except Exception as e:
            print(f"音频处理循环异常: {str(e)}")
        finally:
            print("音频处理循环已退出")

# 单例模式
_audio_manager = None

def get_audio_manager() -> AudioQueueManager:
    """获取全局音频管理器实例"""
    global _audio_manager
    if _audio_manager is None:
        _audio_manager = AudioQueueManager()
    return _audio_manager

async def initialize_audio_system():
    """初始化音频系统"""
    manager = get_audio_manager()
    await manager.start()
    print("音频系统已初始化")
    return True

async def add_to_audio_queue(audio_path):
    """将音频添加到队列"""
    manager = get_audio_manager()
    return await manager.add_to_queue(audio_path)

async def get_current_audio_status():
    """获取当前播放状态"""
    manager = get_audio_manager()
    return await manager.get_status()

async def clear_audio_queue():
    """清空音频队列"""
    manager = get_audio_manager()
    await manager.clear_queue()

async def shutdown_audio_system():
    """关闭音频系统"""
    manager = get_audio_manager()
    await manager.stop()
    await manager.clear_queue()
    print("音频系统已关闭")