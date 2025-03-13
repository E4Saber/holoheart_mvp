// src/pages/HomePage.tsx
import React, { useState, useEffect } from 'react';
import { Tabs, Tab, Box, Typography, useTheme, FormControlLabel, Switch } from '@mui/material';
import ChatTab from '../components/chat/ChatTab';
import MemoryTab from '../components/memory/MemoryTab';
import SettingsSidebar from '../components/sidebar/SettingsSidebar';
import { useAudioManager } from '../hooks/useAudioManager';
import { useMemorySystem } from '../hooks/useMemorySystem';
import { useApiService } from '../hooks/useApiService';
import './HomePage.css';

// 定义消息类型
export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  isError?: boolean;
  audioPath?: string;
  isTyping?: boolean;
}

// 定义设置类型
export interface Settings {
  apiKey: string;
  apiUrl: string;
  streamMode: boolean;
  ttsEnabled: boolean;
  voiceStyle: string;
  loadMemories: boolean;
}

/**
 * 主页面组件，包含聊天和记忆标签页以及设置侧边栏
 */
const HomePage: React.FC = () => {
  const theme = useTheme();
  const [currentTab, setCurrentTab] = useState<number>(0);
  const [conversations, setConversations] = useState<Message[]>([]);
  const [isResponding, setIsResponding] = useState<boolean>(false);
  const [settings, setSettings] = useState<Settings>({
    apiKey: localStorage.getItem('apiKey') || '',
    apiUrl: localStorage.getItem('apiUrl') || 'http://localhost:8000',
    streamMode: localStorage.getItem('streamMode') !== 'false',
    ttsEnabled: localStorage.getItem('ttsEnabled') !== 'false',
    voiceStyle: localStorage.getItem('voiceStyle') || 'normal',
    loadMemories: localStorage.getItem('loadMemories') === 'true'
  });

  // 从服务中获取钩子实例
  const audioManager = useAudioManager(settings.apiUrl);
  const memorySystem = useMemorySystem(settings.apiUrl);
  const apiService = useApiService(settings.apiKey, settings.apiUrl, audioManager);

  // 当设置变更时保存到localStorage
  useEffect(() => {
    localStorage.setItem('apiKey', settings.apiKey);
    localStorage.setItem('apiUrl', settings.apiUrl);
    localStorage.setItem('streamMode', String(settings.streamMode));
    localStorage.setItem('ttsEnabled', String(settings.ttsEnabled));
    localStorage.setItem('voiceStyle', settings.voiceStyle);
    localStorage.setItem('loadMemories', String(settings.loadMemories));
  }, [settings]);

  // 聊天历史本地存储
  useEffect(() => {
    const savedConversations = localStorage.getItem('conversations');
    if (savedConversations) {
      try {
        setConversations(JSON.parse(savedConversations));
      } catch (e) {
        console.error("Failed to parse saved conversations:", e);
      }
    }
  }, []);

  useEffect(() => {
    if (conversations.length > 0) {
      localStorage.setItem('conversations', JSON.stringify(conversations));
    }
  }, [conversations]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  // 清除聊天历史
  const clearConversations = (): void => {
    setConversations([]);
    localStorage.removeItem('conversations');
    audioManager.cleanup();
  };

  // 保存当前对话到记忆系统
  const saveCurrentConversation = async (): Promise<boolean> => {
    if (conversations.length > 0) {
      return await memorySystem.saveConversation(conversations);
    }
    return false;
  };

  // 更新设置
  const updateSettings = (newSettings: Partial<Settings>): void => {
    setSettings(prev => ({
      ...prev,
      ...newSettings
    }));
  };

  // 处理新消息
  const handleSendMessage = async (message: string): Promise<void> => {
    // 添加用户消息到对话
    const userMessage: Message = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    };
    
    setConversations(prev => [...prev, userMessage]);
    setIsResponding(true);
    
    try {
      // 准备请求参数，包括历史会话和记忆加载选项
      const requestParams = {
        message,
        conversation_id: `conv_${Date.now()}`,
        stream: settings.streamMode,
        tts_enabled: settings.ttsEnabled,
        voice_style: settings.voiceStyle,
        load_memories: settings.loadMemories
      };
      
      // 准备历史会话
      const history = conversations.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      let assistantResponse = '';
      let finalAudioUrl: string | undefined;
      
      if (settings.streamMode) {
        // 流式响应处理
        const streamResult = await apiService.streamChat(
          requestParams,
          history,
          (chunk, fullResponse) => {
            // 累积完整响应文本
            assistantResponse = fullResponse;
            
            // 更新AI正在打字的显示
            setConversations(prev => {
              const newConversations = [...prev];
              // 查找或添加assistantMessage
              const lastMsg = newConversations[newConversations.length - 1];
              if (lastMsg.role === 'assistant' && lastMsg.isTyping) {
                // 更新正在输入的消息
                newConversations[newConversations.length - 1] = {
                  ...lastMsg,
                  content: fullResponse
                };
              } else {
                // 添加新的assistant消息
                newConversations.push({
                  role: 'assistant',
                  content: fullResponse,
                  timestamp: new Date().toISOString(),
                  isTyping: true
                });
              }
              return newConversations;
            });
          },
          (audioUrl) => {
            // 后端自动生成并返回了音频URL，前端不需要处理
            // 音频将通过audioManager直接播放
            finalAudioUrl = audioUrl; // 保存最新的音频URL
          }
        );
        
        // 使用函数返回的最终值更新
        assistantResponse = streamResult.text;
        finalAudioUrl = finalAudioUrl || streamResult.audioUrl;
      } else {
        // 非流式响应
        const response = await apiService.chat(requestParams, history);
        assistantResponse = response.text;
        finalAudioUrl = response.audioUrl;
      }
      
      // 添加最终AI响应到对话
      if (assistantResponse) {
        // 移除临时的"正在输入"消息，添加最终消息
        setConversations(prev => {
          const filteredConversations = prev.filter(msg => !msg.isTyping);
          return [
            ...filteredConversations,
            {
              role: 'assistant',
              content: assistantResponse,
              timestamp: new Date().toISOString(),
              audioPath: finalAudioUrl
            }
          ];
        });
      }
    } catch (error) {
      console.error('处理消息时出错:', error);
      // 添加错误消息
      setConversations(prev => {
        // 移除任何临时的"正在输入"消息
        const filteredConversations = prev.filter(msg => !msg.isTyping);
        return [
          ...filteredConversations,
          {
            role: 'assistant',
            content: `发生错误: ${(error as Error).message || '无法处理您的请求'}`,
            timestamp: new Date().toISOString(),
            isError: true
          }
        ];
      });
    } finally {
      setIsResponding(false);
    }
  };

  const handleLoadMemoriesToggle = (event: React.ChangeEvent<HTMLInputElement>) => {
    updateSettings({ loadMemories: event.target.checked });
  };

  return (
    <div className="home-container">
      {/* 侧边栏 */}
      <SettingsSidebar 
        settings={settings}
        onUpdateSettings={updateSettings}
        onSaveConversation={saveCurrentConversation}
        onClearHistory={clearConversations}
        audioManager={audioManager}
      />
      
      {/* 主内容区 */}
      <div className="main-content">
        <Box sx={{ 
          width: '100%', 
          display: 'flex', 
          flexDirection: 'column',
          height: '100vh',
          bgcolor: theme.palette.background.default
        }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', p: '20px 20px 0 20px' }}>
            <Typography variant="h4" component="h1" sx={{ fontWeight: 'bold' }}>
              🤖 AI全息角色系统
            </Typography>
            
            <FormControlLabel
              control={
                <Switch
                  checked={settings.loadMemories}
                  onChange={handleLoadMemoriesToggle}
                  color="primary"
                />
              }
              label="启用记忆"
              sx={{ ml: 2 }}
            />
          </Box>
          
          <Box sx={{ borderBottom: 1, borderColor: 'divider', px: 2 }}>
            <Tabs value={currentTab} onChange={handleTabChange}>
              <Tab label="🗨️ 聊天" id="chat-tab" />
              <Tab label="🧠 记忆" id="memory-tab" />
            </Tabs>
          </Box>
          
          <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
            {currentTab === 0 && (
              <ChatTab 
                conversations={conversations}
                isResponding={isResponding}
                onSendMessage={handleSendMessage}
                apiKey={settings.apiKey}
                audioManager={audioManager}
                apiUrl={settings.apiUrl}
              />
            )}
            
            {currentTab === 1 && (
              <MemoryTab 
                memorySystem={memorySystem}
              />
            )}
          </Box>
          
          <Box sx={{ 
            borderTop: 1, 
            borderColor: 'divider', 
            p: 1, 
            textAlign: 'center',
            fontSize: '0.75rem',
            color: theme.palette.text.secondary 
          }}>
            AI全息角色系统 | 基于FastAPI & React构建 | {new Date().getFullYear()}
          </Box>
        </Box>
      </div>
    </div>
  );
};

export default HomePage;