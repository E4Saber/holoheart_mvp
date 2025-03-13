// src/hooks/useAudioManager.ts
import { useState, useEffect, useRef } from 'react';

export interface AudioManager {
  playAudioFromUrl: (audioUrl: string) => void;
  addToQueue: (audioUrl: string) => void;
  cleanup: () => void;
  getAudioStatus: () => AudioStatus;
  audioFiles: string[];
}

interface AudioStatus {
  isPlaying: boolean;
  currentAudio: string | null;
  queueLength: number;
}

/**
 * 音频管理器钩子，处理音频播放和管理
 */
export const useAudioManager = (apiUrl: string = ''): AudioManager => {
  const [audioFiles, setAudioFiles] = useState<string[]>([]);
  const [currentAudio, setCurrentAudio] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [queue, setQueue] = useState<string[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  
  const baseUrl = apiUrl || window.location.origin;

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
   * 直接从URL播放音频
   */
  const playAudioFromUrl = (audioUrl: string): void => {
    // 追踪音频文件
    const fullUrl = audioUrl.startsWith('http') ? audioUrl : `${baseUrl}${audioUrl}`;

    console.log("Playing audio from URL:", fullUrl);
    
    // 添加到文件列表
    if (!audioFiles.includes(fullUrl)) {
      setAudioFiles(prev => [...prev, fullUrl]);
    }
    
    // 添加到播放队列
    addToQueue(fullUrl);
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
    if (queue.length === 0 || !audioRef.current) {
      console.log("Queue empty or audio ref not available");
      return;
    }

    // 已经在播放，不启动新的播放
    if (isPlaying) {
      return;
    }
    
    const nextAudio = queue[0];
    console.log("Now playing from queue:", nextAudio);
    setQueue(prev => prev.slice(1));
    
    // 先检查文件是否存在可访问
    fetch(nextAudio, { method: 'HEAD' })
    .then(response => {
      if (!response.ok) {
        throw new Error(`File not accessible: ${response.status}`);
      }
      
      // 从队列中移除此项
      setQueue(prev => prev.slice(1));
      
      // 设置当前播放音频
      setCurrentAudio(nextAudio);
      audioRef.current!.src = nextAudio;
      audioRef.current!.load();
      
      // 播放音频
      return audioRef.current!.play();
    })
    .then(() => {
      console.log("Started playing:", nextAudio);
      setIsPlaying(true);
    })
    .catch(error => {
      console.error("Failed to play audio:", error);
      
      // 从队列中移除
      setQueue(prev => prev.slice(1));
      
      // 重置状态
      setIsPlaying(false);
      setCurrentAudio(null);
      
      // 继续尝试下一个
      setTimeout(() => {
        playNextInQueue();
      }, 500); // 短暂延迟后尝试下一个
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

  return {
    playAudioFromUrl,
    addToQueue,
    cleanup,
    getAudioStatus,
    audioFiles
  };
};