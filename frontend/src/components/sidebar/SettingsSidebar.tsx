// src/components/sidebar/SettingsSidebar.tsx
import React, { useState } from 'react';
import {
  Box,
  Drawer,
  Typography,
  TextField,
  Switch,
  FormControlLabel,
  Button,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Tooltip,
  IconButton,
  Alert,
  useTheme,
  SelectChangeEvent
} from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import DeleteIcon from '@mui/icons-material/Delete';
import SaveIcon from '@mui/icons-material/Save';
import { Settings } from '../../pages/HomePage';
import { AudioManager } from '../../hooks/useAudioManager';
import './SettingsSidebar.css';

// 语音风格选项
const VOICE_STYLES: Record<string, string> = {
  normal: '标准',
  cheerful: '欢快',
  serious: '严肃',
  gentle: '温柔',
  robot: '机器人'
};

interface SettingsSidebarProps {
  settings: Settings;
  onUpdateSettings: (settings: Partial<Settings>) => void;
  onSaveConversation: () => Promise<boolean>;
  onClearHistory: () => void;
  audioManager: AudioManager;
}

interface AlertInfo {
  message: string;
  severity: 'success' | 'info' | 'warning' | 'error';
}

/**
 * 设置侧边栏组件，用于配置API、聊天和语音设置
 */
const SettingsSidebar: React.FC<SettingsSidebarProps> = ({ 
  settings, 
  onUpdateSettings, 
  onSaveConversation, 
  onClearHistory,
  audioManager
}) => {
  const theme = useTheme();
  const [showAlert, setShowAlert] = useState<boolean>(false);
  const [alertInfo, setAlertInfo] = useState<AlertInfo>({ message: '', severity: 'success' });

  // 处理设置更改
  const handleSettingChange = (setting: keyof Settings, value: string | boolean): void => {
    onUpdateSettings({ [setting]: value } as Partial<Settings>);
  };

  // 处理文本字段更改
  const handleTextChange = (setting: keyof Settings) => (e: React.ChangeEvent<HTMLInputElement>): void => {
    handleSettingChange(setting, e.target.value);
  };

  // 处理开关更改
  const handleSwitchChange = (setting: keyof Settings) => (e: React.ChangeEvent<HTMLInputElement>): void => {
    handleSettingChange(setting, e.target.checked);
  };

  // 处理选择框更改
  const handleSelectChange = (setting: keyof Settings) => (e: SelectChangeEvent<string>): void => {
    handleSettingChange(setting, e.target.value);
  };

  // 保存对话
  const handleSaveConversation = async (): Promise<void> => {
    try {
      const saved = await onSaveConversation();
      if (saved) {
        showAlertMessage('对话已成功保存到记忆系统', 'success');
      } else {
        showAlertMessage('没有对话可以保存', 'info');
      }
    } catch (error) {
      showAlertMessage(`保存失败: ${(error as Error).message}`, 'error');
    }
  };

  // 清除历史
  const handleClearHistory = (): void => {
    if (window.confirm('确定要清除所有对话历史吗？此操作无法撤销。')) {
      onClearHistory();
      showAlertMessage('对话历史已清除', 'success');
    }
  };

  // 试听语音样本
  const handleTestVoice = async (): Promise<void> => {
    try {
      const sampleText = "这是一个示例语音，您可以使用此风格与AI助手交流。";
      
      // 调用后端TTS API生成语音
      const response = await fetch(`${settings.apiUrl}/api/tts`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          text: sampleText,
          voice_style: settings.voiceStyle
        })
      });
      
      if (!response.ok) {
        throw new Error(`请求失败，状态码: ${response.status}`);
      }
      
      const data = await response.json();
      if (data.audio_url) {
        // 使用音频管理器播放
        audioManager.playAudioFromUrl(data.audio_url);
        showAlertMessage('正在播放语音样本', 'info');
      } else {
        throw new Error('未能获取音频URL');
      }
    } catch (error) {
      showAlertMessage(`无法播放语音样本: ${(error as Error).message}`, 'error');
    }
  };

  // 显示提示信息
  const showAlertMessage = (message: string, severity: AlertInfo['severity']): void => {
    setAlertInfo({ message, severity });
    setShowAlert(true);
    setTimeout(() => setShowAlert(false), 3000);
  };

  // 侧边栏宽度
  const drawerWidth = 280;

  return (
    <Drawer
      variant="permanent"
      anchor="left"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          bgcolor: theme.palette.background.paper,
          borderRight: `1px solid ${theme.palette.divider}`
        },
      }}
    >
      <Box sx={{ p: 2, overflow: 'auto' }}>
        <Typography variant="h6" sx={{ mb: 2, fontWeight: 'bold', display: 'flex', alignItems: 'center' }}>
          🤖 AI全息角色设置
        </Typography>

        {/* 提示信息 */}
        {showAlert && (
          <Alert severity={alertInfo.severity} sx={{ mb: 2 }}>
            {alertInfo.message}
          </Alert>
        )}
        
        {/* API设置 */}
        <Typography variant="subtitle1" sx={{ fontWeight: 'bold', mt: 2 }}>
          API配置
        </Typography>
        <TextField
          label="API密钥"
          type="password"
          fullWidth
          margin="dense"
          value={settings.apiKey}
          onChange={handleTextChange('apiKey')}
          size="small"
        />
        <TextField
          label="API URL"
          fullWidth
          margin="dense"
          value={settings.apiUrl}
          onChange={handleTextChange('apiUrl')}
          size="small"
        />
        
        <Divider sx={{ my: 2 }} />
        
        {/* 聊天设置 */}
        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
          聊天设置
        </Typography>
        <FormControlLabel
          control={
            <Switch
              checked={settings.streamMode}
              onChange={handleSwitchChange('streamMode')}
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="body2">流式输出</Typography>
              <Tooltip title="启用流式输出可以实时看到AI回应，提供更自然的对话体验">
                <IconButton size="small">
                  <InfoIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          }
        />
        
        <FormControlLabel
          control={
            <Switch
              checked={settings.loadMemories}
              onChange={handleSwitchChange('loadMemories')}
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <Typography variant="body2">加载相关记忆</Typography>
              <Tooltip title="自动检索与当前对话相关的历史记忆，提高AI回应的连贯性">
                <IconButton size="small">
                  <InfoIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          }
        />
        
        <Divider sx={{ my: 2 }} />
        
        {/* 语音设置 */}
        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
          语音设置
        </Typography>
        <FormControlLabel
          control={
            <Switch
              checked={settings.ttsEnabled}
              onChange={handleSwitchChange('ttsEnabled')}
            />
          }
          label="启用语音回复"
        />
        
        {settings.ttsEnabled && (
          <>
            <FormControl fullWidth margin="dense" size="small">
              <InputLabel id="voice-style-label">语音风格</InputLabel>
              <Select
                labelId="voice-style-label"
                value={settings.voiceStyle}
                label="语音风格"
                onChange={handleSelectChange('voiceStyle')}
              >
                {Object.entries(VOICE_STYLES).map(([key, label]) => (
                  <MenuItem key={key} value={key}>{label}</MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button
              startIcon={<PlayArrowIcon />}
              variant="outlined"
              size="small"
              onClick={handleTestVoice}
              sx={{ mt: 1 }}
              fullWidth
            >
              试听当前语音
            </Button>
          </>
        )}
        
        <Divider sx={{ my: 2 }} />
        
        {/* 记忆操作 */}
        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
          记忆操作
        </Typography>
        <Button
          startIcon={<SaveIcon />}
          variant="outlined"
          onClick={handleSaveConversation}
          fullWidth
          sx={{ mb: 1 }}
        >
          保存当前对话
        </Button>
        
        <Divider sx={{ my: 2 }} />
        
        {/* 其他操作 */}
        <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
          操作
        </Typography>
        <Button
          startIcon={<DeleteIcon />}
          variant="outlined"
          color="error"
          onClick={handleClearHistory}
          fullWidth
        >
          清除对话历史
        </Button>
      </Box>
    </Drawer>
  );
};

export default SettingsSidebar;