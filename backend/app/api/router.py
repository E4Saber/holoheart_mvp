# app/api/router.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, FileResponse
import os
import asyncio
import base64
import json
from typing import List, Optional, Dict, Any
import time
from datetime import datetime
from uuid import uuid4

from app.client.kimi_api import KimiAPI
from app.models.schemas import (
    ChatRequest, ChatResponse, ChatMessage, 
    TextToSpeechRequest, MemorySearchRequest,
    MemorySummary, MemoryDetail, MemoryCreateRequest,
    SpeechRecognitionRequest, SpeechRecognitionResponse
)
from app.core.audio.audio_file_manager import AudioFileManager
from app.core.audio.audio_manager import get_audio_manager
from app.core.memory.memory_manager import get_memory_system
from app.core.audio.speech_recognizer import get_speech_service
from app.engine.tts_engine import text_to_speech
from app.utils.text_cleaner import clean_text_for_tts, split_text_for_tts, find_sentence_end
from app.config.config import settings

# 创建API路由
api_router = APIRouter()

# 初始化Kimi API客户端
kimi_api_client = KimiAPI()

# 初始化音频文件管理器
audio_file_manager = AudioFileManager(temp_dir=settings.AUDIO_FILES_DIR)

# 扩展的聊天请求格式，包含会话历史
class ExtendedChatRequest(ChatRequest):
    history: Optional[List[Dict[str, str]]] = []
    load_memories: bool = False

# 聊天端点
@api_router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ExtendedChatRequest,
    background_tasks: BackgroundTasks
):
    """处理聊天请求并返回响应"""
    try:
        # 创建用户消息
        user_message = ChatMessage(
            role="user",
            content=request.message,
            timestamp=datetime.now().strftime("%H:%M:%S")
        )
        
        # 使用Kimi API处理
        if request.stream:
            # 这将由流式端点处理
            return HTTPException(
                status_code=400, 
                detail="流式请求应使用 /chat/stream 端点"
            )
        else:
            # 处理会话历史
            conversation_history = request.history or []
            
            # 如果启用了记忆加载，从记忆系统获取相关历史
            if request.load_memories:
                memory_system = get_memory_system()
                relevant_memories = await memory_system.search(
                    query=request.message,
                    limit=5  # 获取最相关的5条记忆
                )
                
                # 如果找到相关记忆，添加到历史中
                if relevant_memories:
                    for memory in relevant_memories:
                        # 添加一个系统消息，标记这是来自记忆的内容
                        conversation_history.append({
                            "role": "system",
                            "content": f"以下是相关的历史对话: {memory.get('summary', '')}"
                        })
                        
                        # 可选：添加记忆中的实际消息
                        memory_messages = memory.get("messages", [])
                        for msg in memory_messages[:3]:  # 仅添加前3条消息，避免太长
                            if isinstance(msg, dict):
                                conversation_history.append({
                                    "role": msg.get("role", "user"),
                                    "content": msg.get("content", "")
                                })
            
            # 通过Kimi API处理请求
            response_text = kimi_api_client.chat(
                message=request.message,
                history=conversation_history
            )
            
            # 创建助手消息
            assistant_message = ChatMessage(
                role="assistant",
                content=response_text,
                timestamp=datetime.now().strftime("%H:%M:%S")
            )
            
            # 如果启用了TTS，生成音频
            audio_url = None
            if request.tts_enabled and response_text:
                # 清理并分割文本用于TTS
                cleaned_text = clean_text_for_tts(response_text)
                text_segments = split_text_for_tts(cleaned_text)
                
                # 为第一段生成TTS
                if text_segments:
                    audio_path = text_to_speech(text_segments[0], request.voice_style)
                    if audio_path:
                        # 保存文件到静态目录
                        filename = f"response_{uuid4()}.mp3"
                        static_path = os.path.join(settings.AUDIO_FILES_DIR, filename)
                        
                        # 确保目录存在
                        os.makedirs(os.path.dirname(static_path), exist_ok=True)
                        
                        # 复制临时文件到静态目录
                        os.rename(audio_path, static_path)
                        
                        # 设置音频URL
                        audio_url = f"/audio/{filename}"
                        assistant_message.audio_path = audio_url
                        
                        # 安排后台任务处理剩余段落的TTS
                        if len(text_segments) > 1:
                            background_tasks.add_task(
                                process_remaining_tts,
                                text_segments[1:],
                                request.voice_style
                            )
            
            # 返回响应
            return ChatResponse(
                conversation_id=request.conversation_id,
                user_message=user_message,
                assistant_message=assistant_message,
                audio_url=audio_url
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"聊天处理失败: {str(e)}")


# 流式聊天端点 - 修改部分
@api_router.post("/chat/stream")
async def stream_chat(request: ExtendedChatRequest):
    """处理流式聊天请求并返回流式响应，同时生成音频片段"""
    try:
        # 创建流式响应
        async def event_generator():
            # 初始化记录完整响应的变量
            full_response = ""
            accumulated_text = ""  # 用于累积足够长度的文本以生成语音
            
            # 处理会话历史
            conversation_history = request.history or []
            
            # 如果启用了记忆加载，从记忆系统获取相关历史
            if request.load_memories:
                memory_system = get_memory_system()
                relevant_memories = await memory_system.search(
                    query=request.message,
                    limit=5  # 获取最相关的5条记忆
                )
                
                # 如果找到相关记忆，添加到历史中
                if relevant_memories:
                    for memory in relevant_memories:
                        # 添加一个系统消息，标记这是来自记忆的内容
                        conversation_history.append({
                            "role": "system",
                            "content": f"以下是相关的历史对话: {memory.get('summary', '')}"
                        })
                        
                        # 可选：添加记忆中的实际消息
                        memory_messages = memory.get("messages", [])
                        for msg in memory_messages[:3]:  # 仅添加前3条消息，避免太长
                            if isinstance(msg, dict):
                                conversation_history.append({
                                    "role": msg.get("role", "user"),
                                    "content": msg.get("content", "")
                                })
            
            # 流式调用Kimi API
            # 在异步函数中使用async for需要一个实现了__aiter__方法的对象
            async for chunk in kimi_api_client.stream_chat(
                message=request.message,
                history=conversation_history
            ):
                # 根据块类型处理
                if chunk.get("type") == "chunk":
                    content = chunk.get("content", "")
                    full_response += content
                    accumulated_text += content
                    
                    # 发送文本块给客户端
                    yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"
                    
                    # 如果启用了TTS并积累了足够长度的文本，生成语音
                    if request.tts_enabled and accumulated_text:
                        # 检查积累的文本是否包含完整句子
                        sentence_end = find_sentence_end(accumulated_text)
                        if sentence_end > 10:  # 确保句子足够长
                            # 提取完整句子
                            sentence = accumulated_text[:sentence_end+1]
                            accumulated_text = accumulated_text[sentence_end+1:]
                            
                            # 生成TTS
                            audio_path = text_to_speech(sentence, request.voice_style)
                            if audio_path:
                                # 保存文件到静态目录
                                filename = f"chunk_{uuid4()}.mp3"
                                static_path = os.path.join(settings.AUDIO_FILES_DIR, filename)
                                
                                # 确保目录存在
                                os.makedirs(os.path.dirname(static_path), exist_ok=True)
                                
                                # 复制临时文件到静态目录
                                os.rename(audio_path, static_path)
                                
                                # 发送音频URL给客户端
                                audio_url = f"/audio/{filename}"
                                yield f"data: {json.dumps({'type': 'audio', 'audio_url': audio_url})}\n\n"
                
                elif chunk.get("type") == "tool_call":
                    yield f"data: {json.dumps({'type': 'tool_call', 'content': '正在搜索相关信息...'})}\n\n"
                
                elif chunk.get("type") == "error":
                    yield f"data: {json.dumps({'type': 'error', 'content': chunk.get('error', '发生错误')})}\n\n"
                    return
                
                elif chunk.get("type") == "end":
                    # 如果还有未处理的文本，生成最后的音频
                    audio_url = None
                    if request.tts_enabled and accumulated_text:
                        audio_path = text_to_speech(accumulated_text, request.voice_style)
                        if audio_path:
                            # 保存文件到静态目录
                            filename = f"final_{uuid4()}.mp3"
                            static_path = os.path.join(settings.AUDIO_FILES_DIR, filename)
                            
                            # 确保目录存在
                            os.makedirs(os.path.dirname(static_path), exist_ok=True)
                            
                            # 复制临时文件到静态目录
                            os.rename(audio_path, static_path)
                            
                            # 设置最终音频URL
                            audio_url = f"/audio/{filename}"
                            
                            # 发送最后一个音频URL给客户端
                            yield f"data: {json.dumps({'type': 'audio', 'audio_url': audio_url})}\n\n"
                    
                    # 发送完成事件
                    yield f"data: {json.dumps({'type': 'end', 'audio_url': audio_url})}\n\n"
                    return
            
        return StreamingResponse(event_generator(), media_type="text/event-stream")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流式聊天处理失败: {str(e)}")

# 文本到语音端点
@api_router.post("/tts")
async def generate_tts(request: TextToSpeechRequest):
    """将文本转换为语音并返回音频文件URL"""
    try:
        if not request.text:
            raise HTTPException(status_code=400, detail="文本不能为空")
        
        # 清理文本
        cleaned_text = clean_text_for_tts(request.text)
        
        # 生成TTS
        audio_path = text_to_speech(cleaned_text, request.voice_style)
        if not audio_path:
            raise HTTPException(status_code=500, detail="TTS生成失败")
        
        # 保存到静态目录
        filename = f"tts_{uuid4()}.mp3"
        static_path = os.path.join(settings.AUDIO_FILES_DIR, filename)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(static_path), exist_ok=True)
        
        # 复制文件
        os.rename(audio_path, static_path)
        
        # 返回URL
        return {"audio_url": f"/audio/{filename}"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS处理失败: {str(e)}")

# 语音识别端点
@api_router.post("/stt", response_model=SpeechRecognitionResponse)
async def speech_to_text(
    file: UploadFile = File(...),
    language: str = Query("zh-cn", description="语言代码")
):
    """处理语音文件并返回识别文本"""
    try:
        # 获取语音识别服务
        speech_service = get_speech_service()
        
        # 读取上传的文件
        audio_data = await file.read()
        
        # 进行语音识别
        recognition_result = await speech_service.recognize_audio(
            audio_data=audio_data,
            language=language
        )
        
        return SpeechRecognitionResponse(
            success=recognition_result.get("success", False),
            text=recognition_result.get("text", ""),
            language=recognition_result.get("language", language),
            confidence=recognition_result.get("confidence", 0.0),
            alternatives=recognition_result.get("alternatives"),
            word_timestamps=recognition_result.get("word_timestamps")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")

# 语音识别端点（Base64）
@api_router.post("/stt/base64", response_model=SpeechRecognitionResponse)
async def speech_to_text_base64(request: SpeechRecognitionRequest):
    """处理Base64编码的语音数据并返回识别文本"""
    try:
        # 获取语音识别服务
        speech_service = get_speech_service()
        
        # 进行语音识别
        recognition_result = await speech_service.recognize_audio(
            audio_data=request.audio_data,  # 可以是Base64字符串或二进制数据
            language=request.language
        )
        
        return SpeechRecognitionResponse(
            success=recognition_result.get("success", False),
            text=recognition_result.get("text", ""),
            language=recognition_result.get("language", request.language),
            confidence=recognition_result.get("confidence", 0.0),
            alternatives=recognition_result.get("alternatives"),
            word_timestamps=recognition_result.get("word_timestamps") if request.include_timestamps else None
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音识别失败: {str(e)}")

# 获取对话历史端点
@api_router.get("/conversations/{conversation_id}")
async def get_conversation_history(conversation_id: str):
    """获取指定对话的历史记录"""
    try:
        memory_system = get_memory_system()
        conversation = await memory_system.get_by_id(conversation_id)
        
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        
        return conversation
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")

# 搜索对话记忆端点
@api_router.post("/memories/search", response_model=List[MemorySummary])
async def search_memories(request: MemorySearchRequest):
    """搜索对话记忆"""
    try:
        memory_system = get_memory_system()
        results = await memory_system.search(
            query=request.query,
            date=request.date,
            limit=request.limit
        )
        
        # 转换为摘要格式
        summaries = []
        for result in results:
            summaries.append(MemorySummary(
                memory_id=result.get("id", ""),
                summary=result.get("summary", ""),
                timestamp=result.get("timestamp", ""),
                tags=result.get("tags", [])
            ))
        
        return summaries
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索记忆失败: {str(e)}")

# 获取记忆详情端点
@api_router.get("/memories/{memory_id}", response_model=MemoryDetail)
async def get_memory_detail(memory_id: str):
    """获取记忆详情"""
    try:
        memory_system = get_memory_system()
        memory = await memory_system.get_by_id(memory_id)
        
        if not memory:
            raise HTTPException(status_code=404, detail="记忆不存在")
        
        # 转换为详情格式
        messages = []
        for msg in memory.get("messages", []):
            messages.append(ChatMessage(
                role=msg.get("role", ""),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", ""),
                audio_path=msg.get("audio_path")
            ))
        
        return MemoryDetail(
            memory_id=memory.get("id", ""),
            summary=memory.get("summary", ""),
            timestamp=memory.get("timestamp", ""),
            messages=messages,
            tags=memory.get("tags", [])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取记忆详情失败: {str(e)}")

# 创建记忆端点
@api_router.post("/memories", response_model=MemorySummary)
async def create_memory(request: MemoryCreateRequest):
    """创建新的记忆"""
    try:
        memory_system = get_memory_system()
        
        # TODO: 获取对话历史
        conversation_history = request.conversations
        
        # 保存到记忆系统
        success = await memory_system.save_conversation(
            conversation_history,
            # summary=request.summary,
            # tags=request.tags
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="保存记忆失败")
        
        # 返回摘要
        return MemorySummary(
            memory_id=f"mem_{int(time.time())}",  # 这应该由记忆系统生成并返回
            summary=request.summary or "新对话",
            timestamp=datetime.now().isoformat(),
            tags=request.tags
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建记忆失败: {str(e)}")

# 处理剩余TTS段落的后台任务
async def process_remaining_tts_async(text_segments, voice_style):
    """异步处理剩余的TTS段落"""
    for segment in text_segments:
        audio_path = text_to_speech(segment, voice_style)
        if audio_path:
            # 添加到音频队列
            audio_manager = get_audio_manager()
            await audio_manager.add_to_queue(audio_path)

# 处理剩余TTS段落的同步版本（用于BackgroundTasks）
def process_remaining_tts(text_segments, voice_style):
    """同步处理剩余的TTS段落（用于BackgroundTasks）"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(process_remaining_tts_async(text_segments, voice_style))
    finally:
        loop.close()