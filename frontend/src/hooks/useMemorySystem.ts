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
export const useMemorySystem = (): MemorySystem => {
  const [isInitialized, setIsInitialized] = useState<boolean>(false);
  
  // 初始化记忆系统
  useEffect(() => {
    const initializeMemorySystem = async (): Promise<void> => {
      try {
        // 在实际项目中，这里可能需要初始化数据库连接或加载记忆索引
        console.log("记忆系统初始化");
        
        // 模拟初始化延迟
        await new Promise(resolve => setTimeout(resolve, 500));
        
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
      
      // 生成对话摘要 (实际项目中可能使用AI生成)
      const summary = generateSummary(conversation);
      
      // 准备记忆对象
      const memoryObject: Memory = {
        timestamp: new Date().toISOString(),
        summary,
        messages: conversation,
        // 可以添加更多元数据，如对话主题、情感分析等
      };
      
      // 存储记忆 (实际项目中应该保存到数据库)
      const memories: Memory[] = JSON.parse(localStorage.getItem('memories') || '[]');
      memories.push(memoryObject);
      localStorage.setItem('memories', JSON.stringify(memories));
      
      console.log("对话已保存到记忆系统:", memoryObject);
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
      // 从存储中获取记忆 (实际项目中应该从数据库查询)
      const memories: Memory[] = JSON.parse(localStorage.getItem('memories') || '[]');
      
      // 过滤记忆
      let filteredMemories = [...memories];
      
      // 按日期过滤
      if (date) {
        const dateStr = typeof date === 'string' ? date : new Date(date).toISOString().split('T')[0];
        filteredMemories = filteredMemories.filter(memory => 
          memory.timestamp && memory.timestamp.startsWith(dateStr)
        );
      }
      
      // 按查询词过滤
      if (query && query.trim()) {
        const searchTerms = query.toLowerCase().trim().split(/\s+/);
        
        filteredMemories = filteredMemories.filter(memory => {
          // 检查摘要
          const summaryMatch = memory.summary && 
            searchTerms.some(term => memory.summary.toLowerCase().includes(term));
          
          // 检查消息内容
          const contentMatch = memory.messages && 
            memory.messages.some(msg => 
              searchTerms.some(term => msg.content.toLowerCase().includes(term))
            );
            
          return summaryMatch || contentMatch;
        });
      }
      
      // 排序：最新的优先
      filteredMemories.sort((a, b) => 
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      
      // 限制结果数量
      const limitedResults = filteredMemories.slice(0, limit);
      
      return limitedResults;
    } catch (error) {
      console.error("检索记忆失败:", error);
      return [];
    }
  };

  /**
   * 生成对话摘要
   * 注意：这是一个简化的实现，实际项目中可能使用AI生成摘要
   */
  const generateSummary = (conversation: Message[]): string => {
    if (!conversation || conversation.length === 0) {
      return "空对话";
    }
    
    // 提取用户的第一条消息作为摘要基础
    const firstUserMessage = conversation.find(msg => msg.role === 'user');
    if (!firstUserMessage) {
      return "无用户消息的对话";
    }
    
    // 简化为前30个字符+省略号
    const content = firstUserMessage.content;
    const summaryText = content.length > 30 
      ? `${content.substring(0, 30)}...` 
      : content;
    
    return `对话: ${summaryText}`;
  };

  return {
    isInitialized,
    saveConversation,
    retrieveMemories
  };
};