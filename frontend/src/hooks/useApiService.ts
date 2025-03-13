// src/hooks/useApiService.ts
import { useRef, useEffect } from 'react';

interface ApiMessage {
  role: string;
  content: string;
}

interface ApiService {
  chat: (message: string, history?: ApiMessage[]) => Promise<string>;
  streamChat: (message: string, history?: ApiMessage[], onChunk?: (chunk: string, fullResponse: string) => void) => Promise<string>;
}

/**
 * API服务钩子，处理AI服务的API调用
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
  const validateApiConfig = (): void => {
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
  const chat = async (message: string, history: ApiMessage[] = []): Promise<string> => {
    validateApiConfig();
    
    // 取消之前的请求（如果有）
    if (controller.current) {
      controller.current.abort();
    }
    
    // 创建新的AbortController
    controller.current = new AbortController();
    const signal = controller.current.signal;
    
    try {
      // 准备请求体
      const requestBody = {
        model: "moonshot-v1-8k", // 可配置为模型参数
        messages: [
          ...history,
          { role: "user", content: message }
        ]
      };
      
      // 发送请求
      const response = await fetch(`${apiUrl}/chat/completions`, {
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
        throw new Error(errorData.error?.message || `API请求失败，状态码: ${response.status}`);
      }
      
      // 解析响应
      const responseData = await response.json();
      const assistantMessage = responseData.choices?.[0]?.message?.content || '';
      
      return assistantMessage;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('请求已取消');
        return '';
      }
      throw error;
    }
  };

  /**
   * 执行流式聊天请求
   */
  const streamChat = async (
    message: string, 
    history: ApiMessage[] = [], 
    onChunk?: (chunk: string, fullResponse: string) => void
  ): Promise<string> => {
    validateApiConfig();
    
    // 取消之前的请求（如果有）
    if (controller.current) {
      controller.current.abort();
    }
    
    // 创建新的AbortController
    controller.current = new AbortController();
    const signal = controller.current.signal;
    
    try {
      // 准备请求体
      const requestBody = {
        model: "moonshot-v1-8k", // 可配置为模型参数
        messages: [
          ...history,
          { role: "user", content: message }
        ],
        stream: true
      };
      
      // 发送请求
      const response = await fetch(`${apiUrl}/chat/completions`, {
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
        throw new Error(errorData.error?.message || `API请求失败，状态码: ${response.status}`);
      }
      
      // 获取响应流
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('无法获取响应流');
      }
      
      const decoder = new TextDecoder('utf-8');
      let completeResponse = '';
      
      // 处理流数据
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        // 解码收到的数据
        const chunk = decoder.decode(value, { stream: true });
        
        // 处理数据块 (格式为 "data: {...}\n\n")
        const lines = chunk.split('\n\n');
        for (const line of lines) {
          if (line.startsWith('data: ') && line !== 'data: [DONE]') {
            try {
              const data = JSON.parse(line.substring(6));
              const content = data.choices?.[0]?.delta?.content || '';
              
              if (content) {
                completeResponse += content;
                
                // 如果提供了回调函数，调用它
                if (onChunk && typeof onChunk === 'function') {
                  onChunk(content, completeResponse);
                }
              }
            } catch (e) {
              console.error('解析流数据失败:', e);
            }
          }
        }
      }
      
      return completeResponse;
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        console.log('请求已取消');
        return '';
      }
      throw error;
    }
  };

  return {
    chat,
    streamChat
  };
};