// src/components/memory/MemoryTab.tsx
import React, { useState } from 'react';
import { 
  Box, 
  TextField, 
  Button, 
  Typography, 
  Paper, 
  Accordion, 
  AccordionSummary, 
  AccordionDetails,
  CircularProgress,
  Alert,
  Divider,
  Grid
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SearchIcon from '@mui/icons-material/Search';
import { MemorySystem } from '../../hooks/useMemorySystem';
import { Message } from '../../pages/HomePage';
import './MemoryTab.css';

interface MemoryTabProps {
  memorySystem: MemorySystem;
}

// 记忆项类型定义
export interface Memory {
  timestamp: string;
  summary: string;
  messages: Message[];
}

/**
 * 记忆标签页组件，允许用户搜索和查看存储的对话记忆
 */
const MemoryTab: React.FC<MemoryTabProps> = ({ memorySystem }) => {
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedDate, setSelectedDate] = useState<Date | null>(new Date());
  const [memories, setMemories] = useState<Memory[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [searchPerformed, setSearchPerformed] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
    setSearchQuery(e.target.value);
  };

  const handleDateChange = (newDate: Date | null): void => {
    setSelectedDate(newDate);
  };

  const handleSearch = async (): Promise<void> => {
    setIsLoading(true);
    setError(null);
    
    try {
      const dateStr = selectedDate ? 
        selectedDate.toISOString().split('T')[0] : null;
        
      const results = await memorySystem.retrieveMemories(
        searchQuery,
        dateStr,
        10
      );
      
      setMemories(results || []);
      setSearchPerformed(true);
    } catch (err) {
      console.error('搜索记忆时出错:', err);
      setError(`无法搜索记忆: ${(err as Error).message || '未知错误'}`);
      setMemories([]);
    } finally {
      setIsLoading(false);
    }
  };

  const formatTimestamp = (timestamp: string | undefined): string => {
    if (!timestamp) return '';
    
    try {
      const date = new Date(timestamp);
      return date.toLocaleString();
    } catch (e) {
      return timestamp.toString();
    }
  };

  return (
    <Box sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Typography variant="h6" gutterBottom>
        记忆系统
      </Typography>
      
      <Paper sx={{ p: 2, mb: 2 }}>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={4}>
            <LocalizationProvider dateAdapter={AdapterDateFns}>
              <DatePicker
                label="选择日期"
                value={selectedDate}
                onChange={handleDateChange}
                slotProps={{ textField: { fullWidth: true } }}
              />
            </LocalizationProvider>
          </Grid>
          
          <Grid item xs={12} md={6}>
            <TextField 
              fullWidth
              label="搜索记忆"
              placeholder="输入关键词搜索..."
              value={searchQuery}
              onChange={handleSearchChange}
              variant="outlined"
            />
          </Grid>
          
          <Grid item xs={12} md={2}>
            <Button
              fullWidth
              variant="contained"
              startIcon={isLoading ? <CircularProgress size={20} /> : <SearchIcon />}
              onClick={handleSearch}
              disabled={isLoading}
            >
              搜索记忆
            </Button>
          </Grid>
        </Grid>
      </Paper>
      
      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}
      
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : searchPerformed ? (
          <>
            {memories.length > 0 ? (
              <>
                <Typography variant="body2" sx={{ mb: 2 }}>
                  找到 {memories.length} 条记忆
                </Typography>
                
                {memories.map((memory, index) => (
                  <Accordion key={index} sx={{ mb: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography>
                        {memory.summary || '对话记录'} - {formatTimestamp(memory.timestamp).split(' ')[0]}
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      {memory.messages && memory.messages.map((msg, msgIndex) => (
                        <Box key={msgIndex} sx={{ mb: 2 }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 'bold' }}>
                            {msg.role === 'user' ? '用户' : 'AI助手'}:
                          </Typography>
                          <Typography variant="body2" sx={{ pl: 2 }}>
                            {msg.content}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {formatTimestamp(msg.timestamp)}
                          </Typography>
                          {msgIndex < memory.messages.length - 1 && (
                            <Divider sx={{ my: 1 }} />
                          )}
                        </Box>
                      ))}
                    </AccordionDetails>
                  </Accordion>
                ))}
              </>
            ) : (
              <Alert severity="info">
                未找到相关记忆
              </Alert>
            )}
          </>
        ) : (
          <Box 
            sx={{ 
              display: 'flex', 
              justifyContent: 'center', 
              alignItems: 'center', 
              height: '100%',
              flexDirection: 'column',
              color: 'text.secondary'
            }}
          >
            <SearchIcon sx={{ fontSize: 40, mb: 2, opacity: 0.5 }} />
            <Typography>
              使用上方搜索栏查找您的对话记忆
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default MemoryTab;