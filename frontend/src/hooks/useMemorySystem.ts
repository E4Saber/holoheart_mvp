// src/hooks/useMemorySystem.ts
import { useState, useEffect } from 'react';
import { Message } from '../pages/HomePage';
import { Memory } from '../components/memory/MemoryTab';

export interface MemorySystem {
  isInitialized: boolean;
  saveConversation: (conversation: Message[]) => Promise<boolean>;
  retrieveMemories: (query?: string, date?: string | null, limit?: number) => Promise<Memory[]>;
}

/**
 * 记忆系统钩子，处理对话历史的存储和检索
 */
export const useMemorySystem = (apiUrl: string = ''): MemorySystem => {
  const [isInitialized, setIsInitialized] = useState<boolean>(false);
  const baseUrl = apiUrl || window.location.origin;
  
  // 初始化记忆系统
  useEffect(() => {
    const initializeMemorySystem = async (): Promise<void> => {
      try {
        // 检查记忆系统是否可用
        console.log("记忆系统初始化");
        setIsInitialized(true);
      } catch (error) {
        console.error("记忆系统初始化失败:", error);
      }
    };
    
    initializeMemorySystem();
    
    // 清理函数
    return () => {
      console.log("记忆系统清理");
    };
  }, []);

  /**
   * 保存当前对话到记忆系统
   */
  const saveConversation = async (conversation: Message[]): Promise<boolean> => {
    if (!isInitialized) {
      console.warn("记忆系统尚未初始化");
      return false;
    }
    
    try {
      // 确保有对话内容
      if (!conversation || conversation.length === 0) {
        return false;
      }
      
      // 生成会话ID
      // const conversationId = `conv_${Date.now()}`;
      
      // 调用后端API保存对话
      const response = await fetch(`${baseUrl}/api/memories`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          // conversation_id: conversationId,
          conversations: localStorage.getItem('conversations'),
          // summary: null, // 让后端自动生成摘要
          // tags: []
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `保存记忆失败，状态码: ${response.status}`);
      }
      
      return true;
    } catch (error) {
      console.error("保存对话到记忆系统失败:", error);
      return false;
    }
  };

  /**
   * 根据查询和日期检索记忆
   */
  const retrieveMemories = async (
    query: string = "", 
    date: string | null = null, 
    limit: number = 10
  ): Promise<Memory[]> => {
    if (!isInitialized) {
      console.warn("记忆系统尚未初始化");
      return [];
    }
    
    try {
      // 调用后端API检索记忆
      const response = await fetch(`${baseUrl}/api/memories/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          query: query,
          date: date,
          limit: limit
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `检索记忆失败，状态码: ${response.status}`);
      }
      
      const memorySummaries = await response.json();
      
      // 对于每个摘要，获取详细信息
      const memories: Memory[] = [];
      
      for (const summary of memorySummaries) {
        try {
          const detailResponse = await fetch(`${baseUrl}/api/memories/${summary.memory_id}`);
          
          if (detailResponse.ok) {
            const memoryDetail = await detailResponse.json();
            
            // 转换为前端期望的格式
            memories.push({
              timestamp: memoryDetail.timestamp,
              summary: memoryDetail.summary,
              messages: memoryDetail.messages.map((msg: any) => ({
                role: msg.role,
                content: msg.content,
                timestamp: msg.timestamp
              }))
            });
          }
        } catch (detailError) {
          console.error(`获取记忆详情失败 ${summary.memory_id}:`, detailError);
        }
      }
      
      return memories;
    } catch (error) {
      console.error("检索记忆失败:", error);
      return [];
    }
  };

  return {
    isInitialized,
    saveConversation,
    retrieveMemories
  };
};