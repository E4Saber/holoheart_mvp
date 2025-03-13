// src/hooks/useApiService.ts
import { useRef, useEffect } from 'react';
import { Message } from '../pages/HomePage';

interface ApiService {
  chat: (message: string, history?: Message[]) => Promise<{text: string, audioUrl?: string}>;
  streamChat: (
    message: string, 
    history?: Message[], 
    onChunk?: (chunk: string, fullResponse: string) => void
  ) => Promise<{text: string, audioUrl?: string}>;
}

/**
 * API服务钩子，处理与后端API的通信
 */
export const useApiService = (apiKey: string, apiUrl: string): ApiService => {
  const controller = useRef<AbortController | null>(null);
  
  // 在组件卸载时取消任何正在进行的请求
  useEffect(() => {
    return () => {
      if (controller.current) {
        controller.current.abort();
      }
    };
  }, []);

  /**
   * 验证API配置
   */
  const validateConfig = (): void => {
    if (!apiKey) {
      throw new Error('API密钥未配置');
    }
    
    if (!apiUrl) {
      throw new Error('API URL未配置');
    }
  };

  /**
   * 执行非流式聊天请求
   */
  const chat = async (message: string, history: Message[] = []): Promise<{text: string, audioUrl?: string}> => {
    validateConfig();
    
    // 取消之前的请求（如果有）
    if (controller.current) {
      controller.current.abort();
    }
    
    // 创建新的AbortController
    controller.current = new AbortController();
    const signal = controller.current.signal;
    
    try {
      // 准备请求体 - 适配后端API格式
      const requestBody = {
        message: message,
        conversation_id: Date.now().toString(), // 生成唯一会话ID
        stream: false,
        tts_enabled: true,
        voice_style: "normal" // 默认风格，可以从settings传入
      };
      
      // 发送请求到后端
      const response = await fetch(`${apiUrl}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify(requestBody),
        signal: signal
      });
      
      // 检查响应状态
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API请求失败，状态码: ${response.status}`);
      }
      
      // 解析响应
      const responseData = await response.json();
      
      return {
        text: responseData.assistant_message.content,
        audioUrl: responseData.audio_url
      };
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('请求已取消');
        return { text: '' };
      }
      throw error;
    }
  };

  /**
   * 执行流式聊天请求
   */
  const streamChat = async (
    message: string, 
    history: Message[] = [], 
    onChunk?: (chunk: string, fullResponse: string) => void
  ): Promise<{text: string, audioUrl?: string}> => {
    validateConfig();
    
    // 取消之前的请求（如果有）
    if (controller.current) {
      controller.current.abort();
    }
    
    // 创建新的AbortController
    controller.current = new AbortController();
    const signal = controller.current.signal;
    
    try {
      // 准备请求体 - 适配后端API格式
      const requestBody = {
        message: message,
        conversation_id: Date.now().toString(),
        stream: true,
        tts_enabled: true,
        voice_style: "normal" // 默认风格，可以从settings传入
      };
      
      // 发送请求到后端流式端点
      const response = await fetch(`${apiUrl}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${apiKey}`
        },
        body: JSON.stringify(requestBody),
        signal: signal
      });
      
      // 检查响应状态
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API请求失败，状态码: ${response.status}`);
      }
      
      // 获取事件流
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法获取响应流');
      }
      
      const decoder = new TextDecoder('utf-8');
      let completeResponse = '';
      let audioUrl: string | undefined;
      
      // 处理流数据
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        // 解码收到的数据
        const chunk = decoder.decode(value, { stream: true });
        
        // 处理事件数据 (格式为 "data: {...}\n\n")
        const lines = chunk.split('\n\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.substring(6));
              
              // 根据事件类型处理
              if (data.type === 'chunk') {
                // 文本片段
                const content = data.content || '';
                if (content) {
                  completeResponse += content;
                  
                  // 如果提供了回调函数，调用它
                  if (onChunk && typeof onChunk === 'function') {
                    onChunk(content, completeResponse);
                  }
                }
              } else if (data.type === 'end') {
                // 结束事件，可能包含音频URL
                audioUrl = data.audio_url;
              } else if (data.type === 'error') {
                // 错误事件
                throw new Error(data.content || '处理请求时出错');
              }
            } catch (e) {
              console.error('解析流数据失败:', e);
            }
          }
        }
      }
      
      return {
        text: completeResponse,
        audioUrl
      };
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('请求已取消');
        return { text: '' };
      }
      throw error;
    }
  };

  return {
    chat,
    streamChat
  };
};