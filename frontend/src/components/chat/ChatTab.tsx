// src/components/chat/ChatTab.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Box, TextField, IconButton, Typography, Paper, CircularProgress } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import ReactMarkdown from 'react-markdown';
import { Message } from '../../pages/HomePage';
import { AudioManager } from '../../hooks/useAudioManager';
import './ChatTab.css';

interface ChatTabProps {
  conversations: Message[];
  isResponding: boolean;
  onSendMessage: (message: string) => Promise<void>;
  apiKey: string;
  audioManager: AudioManager;
}

/**
 * 聊天标签页组件，显示对话历史并允许用户发送新消息
 */
const ChatTab: React.FC<ChatTabProps> = ({ 
  conversations, 
  isResponding, 
  onSendMessage, 
  apiKey, 
  audioManager 
}) => {
  const [message, setMessage] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageInputRef = useRef<HTMLTextAreaElement>(null);

  // 当对话更新时滚动到底部
  useEffect(() => {
    scrollToBottom();
  }, [conversations, isResponding]);

  // 组件挂载时聚焦输入框
  useEffect(() => {
    if (messageInputRef.current) {
      messageInputRef.current.focus();
    }
  }, []);

  const scrollToBottom = (): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleMessageChange = (e: React.ChangeEvent<HTMLTextAreaElement>): void => {
    setMessage(e.target.value);
  };

  const handleSendMessage = (): void => {
    if (message.trim() && !isResponding) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', p: 2 }}>
      {/* 没有消息时显示欢迎信息 */}
      {conversations.length === 0 && (
        <Box 
          sx={{ 
            flexGrow: 1, 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            flexDirection: 'column',
            color: 'text.secondary'
          }}
        >
          <Typography variant="h5" sx={{ mb: 1 }}>
            开始与AI全息角色聊天
          </Typography>
          <Typography variant="body1">
            在下方输入您的消息
          </Typography>
          {!apiKey && (
            <Typography 
              variant="body2" 
              color="error" 
              sx={{ mt: 2, p: 2, bgcolor: 'error.light', borderRadius: 1, color: 'error.contrastText' }}
            >
              请在设置面板中配置API密钥以开始聊天
            </Typography>
          )}
        </Box>
      )}

      {/* 聊天消息区域 */}
      {conversations.length > 0 && (
        <Box className="chat-messages-container">
          {conversations.map((msg, index) => (
            <Box 
              key={index} 
              className={`message-wrapper ${msg.role === 'user' ? 'user-message-wrapper' : 'assistant-message-wrapper'}`}
            >
              <Paper 
                elevation={1} 
                className={`message-bubble ${
                  msg.role === 'user' 
                    ? 'user-message' 
                    : msg.isError 
                      ? 'error-message' 
                      : 'assistant-message'
                }`}
              >
                {msg.role === 'user' ? (
                  <Typography variant="body1">{msg.content}</Typography>
                ) : (
                  <Box className="markdown-container">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </Box>
                )}
                <Typography variant="caption" className="message-timestamp">
                  {formatTimestamp(msg.timestamp)}
                </Typography>
              </Paper>
            </Box>
          ))}

          {/* 正在回应的指示器 */}
          {isResponding && (
            <Box className="message-wrapper assistant-message-wrapper">
              <Paper elevation={1} className="message-bubble assistant-message">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <CircularProgress size={20} />
                  <Typography variant="body2">AI正在思考中...</Typography>
                </Box>
              </Paper>
            </Box>
          )}

          {/* 用于滚动到底部的引用元素 */}
          <div ref={messagesEndRef} />
        </Box>
      )}

      {/* 消息输入区域 */}
      <Box sx={{ mt: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <TextField
          inputRef={messageInputRef}
          fullWidth
          variant="outlined"
          placeholder="输入您的消息..."
          value={message}
          onChange={handleMessageChange}
          onKeyDown={handleKeyDown}
          disabled={isResponding || !apiKey}
          multiline
          maxRows={4}
          size="small"
          sx={{ bgcolor: 'background.paper' }}
        />
        <IconButton 
          color="primary" 
          onClick={handleSendMessage} 
          disabled={!message.trim() || isResponding || !apiKey}
          sx={{ bgcolor: 'primary.main', color: 'primary.contrastText', '&:hover': { bgcolor: 'primary.dark' } }}
        >
          <SendIcon />
        </IconButton>
      </Box>
    </Box>
  );
};

export default ChatTab;