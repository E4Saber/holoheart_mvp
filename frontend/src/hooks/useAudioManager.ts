// src/hooks/useAudioManager.ts
import { useState, useEffect, useRef } from 'react';

export interface AudioManager {
  generateSpeech: (text: string, voiceStyle: string) => Promise<string | null>;
  processStreamingText: (text: string, voiceStyle: string) => void;
  addToQueue: (audioUrl: string) => void;
  cleanup: () => void;
  getAudioStatus: () => AudioStatus;
  resetTextPosition: () => void;
  audioFiles: string[];
}

interface AudioStatus {
  isPlaying: boolean;
  currentAudio: string | null;
  queueLength: number;
}

/**
 * 音频管理器钩子，处理语音的生成、播放和管理
 */
export const useAudioManager = (): AudioManager => {
  const [audioFiles, setAudioFiles] = useState<string[]>([]);
  const [currentAudio, setCurrentAudio] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [queue, setQueue] = useState<string[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastSentenceEndRef = useRef<number>(0);

  // 初始化音频元素
  useEffect(() => {
    audioRef.current = new Audio();
    
    // 音频播放结束时，播放下一个队列中的文件
    const handleAudioEnd = () => {
      setIsPlaying(false);
      playNextInQueue();
    };
    
    audioRef.current.addEventListener('ended', handleAudioEnd);
    
    // 组件卸载时的清理
    return () => {
      if (audioRef.current) {
        audioRef.current.removeEventListener('ended', handleAudioEnd);
        audioRef.current.pause();
        audioRef.current = null;
      }
      cleanup();
    };
  }, []);

  // 队列变化时，如果没有正在播放，开始播放
  useEffect(() => {
    if (queue.length > 0 && !isPlaying && audioRef.current) {
      playNextInQueue();
    }
  }, [queue, isPlaying]);

  /**
   * 查找句子结束位置
   */
  const findSentenceEnd = (text: string): number => {
    const endChars = ["。", "？", "！", ".", "?", "!"];
    let sentenceEnd = -1;
    
    for (const char of endChars) {
      const pos = text.indexOf(char);
      if (pos !== -1 && (sentenceEnd === -1 || pos < sentenceEnd)) {
        sentenceEnd = pos;
      }
    }
    
    return sentenceEnd;
  };

  /**
   * 处理流式文本，提取完整句子进行语音生成
   */
  const processStreamingText = (text: string, voiceStyle: string): void => {
    const currentLength = text.length;
    
    // 确保有足够的新文本
    if (currentLength - lastSentenceEndRef.current < 30) {
      return;
    }
    
    // 提取新文本并查找句子边界
    const newText = text.substring(lastSentenceEndRef.current);
    const sentenceEnd = findSentenceEnd(newText);
    
    // 如果找到完整句子，生成语音
    if (sentenceEnd > 5) {
      const speechText = newText.substring(0, sentenceEnd + 1);
      generateSpeech(speechText, voiceStyle);
      lastSentenceEndRef.current += sentenceEnd + 1;
    }
  };

  /**
   * 生成语音并加入播放队列
   */
  const generateSpeech = async (text: string, voiceStyle: string): Promise<string | null> => {
    try {
      // 实际项目中，这里应该调用TTS服务
      // 此处为模拟实现，实际开发中替换为真实API调用
      console.log(`Generating speech for: "${text}" with style "${voiceStyle}"`);
      
      // 模拟API调用延迟
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // 模拟返回音频URL (实际开发中应使用真实的API响应)
      const mockAudioUrl = `/api/tts?text=${encodeURIComponent(text)}&style=${voiceStyle}&timestamp=${Date.now()}`;
      
      // 将生成的音频添加到文件列表和播放队列
      setAudioFiles(prev => [...prev, mockAudioUrl]);
      addToQueue(mockAudioUrl);
      
      return mockAudioUrl;
    } catch (error) {
      console.error("语音生成失败:", error);
      return null;
    }
  };

  /**
   * 将音频添加到播放队列
   */
  const addToQueue = (audioUrl: string): void => {
    setQueue(prev => [...prev, audioUrl]);
  };

  /**
   * 播放队列中的下一个音频
   */
  const playNextInQueue = (): void => {
    if (queue.length === 0 || !audioRef.current) return;
    
    const nextAudio = queue[0];
    setQueue(prev => prev.slice(1));
    
    setCurrentAudio(nextAudio);
    audioRef.current.src = nextAudio;
    audioRef.current.play()
      .then(() => setIsPlaying(true))
      .catch(error => {
        console.error("音频播放失败:", error);
        setIsPlaying(false);
        playNextInQueue(); // 尝试播放下一个
      });
  };

  /**
   * 清理所有音频资源
   */
  const cleanup = (): void => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    setQueue([]);
    setIsPlaying(false);
    setCurrentAudio(null);
    setAudioFiles([]);
    lastSentenceEndRef.current = 0;
  };

  /**
   * 获取当前音频状态
   */
  const getAudioStatus = (): AudioStatus => {
    return {
      isPlaying,
      currentAudio,
      queueLength: queue.length
    };
  };

  /**
   * 重置句子追踪位置
   */
  const resetTextPosition = (): void => {
    lastSentenceEndRef.current = 0;
  };

  return {
    generateSpeech,
    processStreamingText,
    addToQueue,
    cleanup,
    getAudioStatus,
    resetTextPosition,
    audioFiles
  };
};