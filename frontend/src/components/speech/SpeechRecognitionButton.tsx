// src/components/speech/SpeechRecognitionButton.tsx
import React, { useState, useRef } from 'react';
import { IconButton, CircularProgress, Tooltip } from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';

interface SpeechRecognitionButtonProps {
  apiUrl: string;
  apiKey: string;
  onResult: (text: string) => void;
  onError?: (error: Error) => void;
  disabled?: boolean;
}

/**
 * 语音识别按钮组件，用于录制用户语音并转换为文本
 */
const SpeechRecognitionButton: React.FC<SpeechRecognitionButtonProps> = ({
  apiUrl,
  apiKey,
  onResult,
  onError,
  disabled = false
}) => {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  
  const baseUrl = apiUrl || window.location.origin;

  /**
   * 开始录音
   */
  const startRecording = async (): Promise<void> => {
    try {
      // 请求用户麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // 创建MediaRecorder实例
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      
      // 配置数据处理
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      // 录音结束时处理
      mediaRecorder.onstop = async () => {
        setIsProcessing(true);
        try {
          await processAudio();
        } catch (error) {
          console.error('处理音频时出错:', error);
          if (onError && error instanceof Error) {
            onError(error);
          }
        } finally {
          setIsProcessing(false);
          setIsRecording(false);
          
          // 停止所有轨道
          stream.getTracks().forEach(track => track.stop());
        }
      };
      
      // 开始录音
      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error('启动录音失败:', error);
      if (onError && error instanceof Error) {
        onError(error);
      }
      setIsRecording(false);
    }
  };

  /**
   * 停止录音
   */
  const stopRecording = (): void => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
  };

  /**
   * 处理录制的音频
   */
  const processAudio = async (): Promise<void> => {
    if (audioChunksRef.current.length === 0) {
      throw new Error('没有录制到音频数据');
    }
    
    // 合并音频块
    const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
    
    // 创建FormData对象
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.wav');
    
    try {
      // 发送到后端API
      const response = await fetch(`${baseUrl}/api/stt`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${apiKey}`
        },
        body: formData
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `语音识别失败，状态码: ${response.status}`);
      }
      
      const result = await response.json();
      
      // 如果有识别结果，调用回调函数
      if (result.success && result.text) {
        onResult(result.text);
      } else {
        throw new Error('没有识别到语音内容');
      }
    } catch (error) {
      console.error('语音识别请求失败:', error);
      throw error;
    }
  };

  /**
   * 处理按钮点击
   */
  const handleButtonClick = (): void => {
    if (!isRecording && !isProcessing) {
      startRecording();
    } else if (isRecording) {
      stopRecording();
    }
  };

  return (
    <Tooltip title={isRecording ? "点击停止录音" : "点击开始录音"}>
      <IconButton
        color={isRecording ? "error" : "primary"}
        onClick={handleButtonClick}
        disabled={disabled || isProcessing}
        sx={{
          position: 'relative',
          bgcolor: isRecording ? 'error.main' : 'primary.main',
          color: 'white',
          '&:hover': {
            bgcolor: isRecording ? 'error.dark' : 'primary.dark',
          }
        }}
      >
        {isProcessing ? (
          <CircularProgress size={24} color="inherit" />
        ) : (
          isRecording ? <MicOffIcon /> : <MicIcon />
        )}
      </IconButton>
    </Tooltip>
  );
};

export default SpeechRecognitionButton;