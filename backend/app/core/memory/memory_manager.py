"""
记忆系统 - FastAPI适配版本
管理对话历史记录和记忆检索
"""
import asyncio
import json
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.config.config import settings

class MemoryManager:
    """记忆系统类，管理对话历史记录和记忆检索"""
    
    def __init__(self):
        # 记忆处理队列
        self.memory_queue = asyncio.Queue()
        
        # 状态追踪
        self.last_activity_time = time.time()
        self.activity_timeout = 600  # 10分钟无活动触发保存
        
        # 内存缓存
        self.memory_cache = {}  # 缓存最近的对话，键为日期
        
        # 创建目录
        self.base_dir = settings.MEMORY_DIR
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.directory = self.base_dir / self.today
        os.makedirs(self.directory, exist_ok=True)
        
        # 处理任务
        self.task = None
        self.lock = asyncio.Lock()
    
    async def start(self):
        """启动记忆处理任务"""
        if self.task is None or self.task.done():
            self.task = asyncio.create_task(self._memory_processor())
            print("记忆处理任务已启动")
    
    async def stop(self):
        """停止记忆处理任务"""
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
            print("记忆处理任务已停止")
    
    async def _memory_processor(self):
        """记忆处理循环"""
        print("记忆处理循环已启动")
        
        try:
            while True:
                # 检查是否有待处理的记忆
                if not self.memory_queue.empty():
                    # 获取记忆数据
                    memory_data = await self.memory_queue.get()
                    await self._process_memory(memory_data)
                    self.memory_queue.task_done()
                
                # 检查是否需要触发自动保存（长时间无活动）
                current_time = time.time()
                if current_time - self.last_activity_time > self.activity_timeout:
                    print(f"检测到{self.activity_timeout}秒无活动，触发自动保存")
                    # 注意：此处实际应从应用获取当前对话
                    self.last_activity_time = current_time  # 重置计时器
                
                # 避免CPU占用
                await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            print("记忆处理循环被取消")
        except Exception as e:
            print(f"记忆处理循环异常: {str(e)}")
        finally:
            print("记忆处理循环已退出")
    
    async def _process_memory(self, memory_data: Dict[str, Any]):
        """处理单条记忆"""
        conversation_id = memory_data.get("conversation_id", "unknown")
        timestamp = memory_data.get("timestamp", datetime.now().isoformat())
        
        print(f"处理对话记忆: {conversation_id}, 时间: {timestamp}")
        
        # 转换为存储格式
        storage_format = self._convert_to_storage_format(memory_data)
        
        # 保存到文件系统
        await self._save_to_file(storage_format, conversation_id)
        
        # 更新内存缓存
        self._update_memory_cache(storage_format)
    
    def _convert_to_storage_format(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """将原始对话转换为结构化存储格式"""
        storage_format = {
            "id": memory_data.get("conversation_id", f"conv_{int(time.time())}"),
            "timestamp": memory_data.get("timestamp", datetime.now().isoformat()),
            "messages": memory_data.get("messages", []),
            "summary": memory_data.get("summary") or self._generate_summary(memory_data.get("messages", [])),
            "metadata": {
                "processed_at": datetime.now().isoformat(),
                "source": "fastapi_app",
            }
        }
        
        return storage_format
    
    def _generate_summary(self, messages: List[Dict[str, Any]]) -> str:
        """为对话生成简单摘要"""
        if not messages:
            return "空对话"
        
        # 简单实现：使用第一条用户消息作为摘要
        for msg in messages:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                return content[:100] + ("..." if len(content) > 100 else "")
        
        return "无用户消息的对话"
    
    async def _save_to_file(self, memory_data: Dict[str, Any], conversation_id: str) -> Path:
        """将记忆保存到文件系统"""
        # 确保目录存在
        os.makedirs(self.directory, exist_ok=True)
        
        # 创建文件名
        filename = f"{conversation_id}_{int(time.time())}.json"
        filepath = self.directory / filename

        # 检查文件是否存在
        existing_data = []
        if filepath.exists():
            # 读取现有数据
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    # 确保现有数据是一个列表
                    if not isinstance(existing_data, list):
                        existing_data = [existing_data]
            except json.JSONDecodeError:
                existing_data = []
        
        # 将新数据添加到列表中
        existing_data.append(memory_data)
        
        # 保存数据
        async with self.lock:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        print(f"记忆已保存到文件: {filepath}")
        return filepath
    
    def _update_memory_cache(self, memory_data: Dict[str, Any]):
        """更新内存中的记忆缓存"""
        # 使用日期作为键
        date_key = memory_data.get("timestamp", "")[:10]  # YYYY-MM-DD
        
        if date_key not in self.memory_cache:
            self.memory_cache[date_key] = []
        
        # 添加到对应日期的缓存列表
        self.memory_cache[date_key].append(memory_data)
        
        # 可选：限制每个日期的缓存大小
        if len(self.memory_cache[date_key]) > 20:  # 每天最多缓存20条对话
            self.memory_cache[date_key] = self.memory_cache[date_key][-20:]
    
    async def save_conversation(self, conversation_history: List[Dict[str, Any]], 
                               summary: Optional[str] = None,
                               tags: Optional[List[str]] = None) -> bool:
        """保存对话到记忆系统"""
        if not conversation_history:
            return False
        
        # 创建记忆数据
        memory_data = {
            "conversation_id": f"conv_{int(time.time())}",
            "timestamp": datetime.now().isoformat(),
            "messages": conversation_history,
            "summary": summary,
            "tags": tags or []
        }
        
        # 添加到处理队列
        await self.memory_queue.put(memory_data)
        print(f"对话已添加到记忆处理队列，共{len(conversation_history)}条消息")
        
        # 更新最后活动时间
        self.last_activity_time = time.time()
        
        return True
    
    async def search(self, query: Optional[str] = None, 
                    date: Optional[str] = None, 
                    limit: int = 20) -> List[Dict[str, Any]]:
        """搜索记忆"""
        results = []
        
        # 如果指定了日期且在缓存中
        if date and date in self.memory_cache:
            memories = self.memory_cache[date]
            # 如果有查询词，进行过滤
            if query:
                memories = [
                    mem for mem in memories 
                    if any(query.lower() in msg.get("content", "").lower() 
                          for msg in mem.get("messages", []))
                ]
            return memories[:limit]
        
        # 否则从文件系统检索
        if date:
            search_dir = self.base_dir / date
            if not search_dir.exists():
                return []
            dirs_to_search = [search_dir]
        else:
            # 获取所有日期目录
            if not self.base_dir.exists():
                return []
            dirs_to_search = [
                self.base_dir / d for d in os.listdir(self.base_dir) 
                if (self.base_dir / d).is_dir()
            ]
        
        # 从所有目录中检索文件
        for directory in dirs_to_search:
            if not directory.exists():
                continue
                
            for filename in os.listdir(directory):
                if filename.endswith('.json'):
                    filepath = directory / filename
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            memories = json.load(f)
                            
                            # 确保是列表
                            if not isinstance(memories, list):
                                memories = [memories]
                            
                            for memory in memories:
                                # 如果有查询词，检查是否匹配
                                if query:
                                    match = False
                                    for msg in memory.get("messages", []):
                                        if query.lower() in msg.get("content", "").lower():
                                            match = True
                                            break
                                    if not match:
                                        continue
                                
                                results.append(memory)
                                if len(results) >= limit:
                                    break
                    except Exception as e:
                        print(f"读取记忆文件出错 {filepath}: {str(e)}")
            
            if len(results) >= limit:
                break
        
        return results
    
    async def get_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """通过ID获取记忆详情"""
        # 首先检查内存缓存
        for date_memories in self.memory_cache.values():
            for memory in date_memories:
                if memory.get("id") == memory_id:
                    return memory
        
        # 然后从文件系统查找
        for date_dir in os.listdir(self.base_dir):
            dir_path = self.base_dir / date_dir
            if not dir_path.is_dir():
                continue
                
            for filename in os.listdir(dir_path):
                if not filename.endswith('.json'):
                    continue
                    
                filepath = dir_path / filename
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        memories = json.load(f)
                        if not isinstance(memories, list):
                            memories = [memories]
                        
                        # 查找匹配的记忆
                        for memory in memories:
                            if memory.get("id") == memory_id:
                                return memory
                except Exception as e:
                    print(f"读取记忆文件出错 {filepath}: {str(e)}")
        
        return None
    
    async def delete(self, memory_id: str) -> bool:
        """删除指定ID的记忆"""
        # 首先从内存缓存中删除
        for date, memories in self.memory_cache.items():
            self.memory_cache[date] = [mem for mem in memories if mem.get("id") != memory_id]
        
        # 然后尝试从文件系统中删除
        # 注意：由于我们的存储方式，这需要读取每个文件、修改内容并重写
        # 对于实际应用，考虑使用数据库以简化这个过程
        found = False
        
        for date_dir in os.listdir(self.base_dir):
            dir_path = self.base_dir / date_dir
            if not dir_path.is_dir():
                continue
                
            for filename in os.listdir(dir_path):
                if not filename.endswith('.json'):
                    continue
                    
                filepath = dir_path / filename
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        memories = json.load(f)
                        if not isinstance(memories, list):
                            memories = [memories]
                    
                    # 检查是否存在匹配的记忆
                    original_count = len(memories)
                    memories = [mem for mem in memories if mem.get("id") != memory_id]
                    
                    # 如果删除了记忆，更新文件
                    if len(memories) < original_count:
                        found = True
                        async with self.lock:
                            with open(filepath, 'w', encoding='utf-8') as f:
                                json.dump(memories, f, ensure_ascii=False, indent=2)
                        print(f"从文件{filepath}中删除了记忆ID: {memory_id}")
                        
                        # 文件为空则删除文件
                        if not memories:
                            os.unlink(filepath)
                            print(f"删除了空文件: {filepath}")
                except Exception as e:
                    print(f"处理记忆文件出错 {filepath}: {str(e)}")
        
        return found
    
    async def get_all_dates(self) -> List[str]:
        """获取所有有记忆的日期"""
        if not self.base_dir.exists():
            return []
            
        return [d for d in os.listdir(self.base_dir) 
                if (self.base_dir / d).is_dir()]
    
    async def get_all_tags(self) -> List[str]:
        """获取所有标签"""
        all_tags = set()
        
        # 检查内存缓存
        for date_memories in self.memory_cache.values():
            for memory in date_memories:
                tags = memory.get("tags", [])
                all_tags.update(tags)
        
        # 从文件系统读取
        if self.base_dir.exists():
            for date_dir in os.listdir(self.base_dir):
                dir_path = self.base_dir / date_dir
                if not dir_path.is_dir():
                    continue
                    
                for filename in os.listdir(dir_path):
                    if not filename.endswith('.json'):
                        continue
                        
                    filepath = dir_path / filename
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            memories = json.load(f)
                            if not isinstance(memories, list):
                                memories = [memories]
                            
                            for memory in memories:
                                tags = memory.get("tags", [])
                                all_tags.update(tags)
                    except Exception as e:
                        print(f"读取记忆文件出错 {filepath}: {str(e)}")
        
        return list(all_tags)
    
    async def get_recent(self, limit: int = 10, offset: int = 0) -> List[Dict[str, Any]]:
        """获取最近的记忆"""
        all_memories = []
        
        # 从缓存中获取
        for date_memories in self.memory_cache.values():
            all_memories.extend(date_memories)
        
        # 从文件系统读取
        if self.base_dir.exists():
            for date_dir in sorted(os.listdir(self.base_dir), reverse=True):
                dir_path = self.base_dir / date_dir
                if not dir_path.is_dir():
                    continue
                
                for filename in os.listdir(dir_path):
                    if not filename.endswith('.json'):
                        continue
                    
                    filepath = dir_path / filename
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            memories = json.load(f)
                            if not isinstance(memories, list):
                                memories = [memories]
                            all_memories.extend(memories)
                    except Exception as e:
                        print(f"读取记忆文件出错 {filepath}: {str(e)}")
        
        # 按时间戳排序（最新的优先）
        all_memories.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # 应用分页
        return all_memories[offset:offset+limit]

# 单例模式
_memory_system = None

def get_memory_system() -> MemoryManager:
    """获取记忆系统单例"""
    global _memory_system
    if _memory_system is None:
        _memory_system = MemoryManager()
    return _memory_system

async def initialize_memory_system():
    """初始化记忆系统"""
    memory_system = get_memory_system()
    await memory_system.start()
    print("记忆系统已初始化")
    return True

async def save_current_conversation(conversation_history, summary=None, tags=None):
    """保存当前对话到记忆系统"""
    memory_system = get_memory_system()
    return await memory_system.save_conversation(conversation_history, summary, tags)

async def retrieve_memories(query=None, date=None, limit=10):
    """检索记忆"""
    memory_system = get_memory_system()
    return await memory_system.search(query, date, limit)