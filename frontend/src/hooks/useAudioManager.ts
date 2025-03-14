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

export const useAudioManager = (apiUrl: string = ''): AudioManager => {
  const [audioFiles, setAudioFiles] = useState<string[]>([]);
  const [currentAudio, setCurrentAudio] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  
  // 使用useRef替代useState来管理队列
  const queueRef = useRef<string[]>([]);
  const playingRef = useRef<boolean>(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // 添加一个正在处理队列的标记，防止多个异步处理重叠
  const processingQueueRef = useRef<boolean>(false);
  
  const baseUrl = apiUrl || window.location.origin;

  // 初始化音频元素
  useEffect(() => {
    audioRef.current = new Audio();
    
    // 添加更多的音频事件监听器，帮助调试
    const handleAudioEvent = (event: string) => (e: Event) => {
      console.log(`Audio event: ${event}`, e);
    };
    
    // 音频播放结束时，播放下一个队列中的文件
    const handleAudioEnd = () => {
      console.log("Audio ended, current URL:", audioRef.current?.src);
      
      // 重要：标记当前不在播放状态
      playingRef.current = false;
      setIsPlaying(false);
      
      // 重要：先检查处理队列的标记，防止重复处理
      if (!processingQueueRef.current && queueRef.current.length > 0) {
        console.log("Queue has more items, processing next...");
        processQueue();
      } else {
        console.log("Queue empty or already processing");
      }
    };
    
    const handleAudioError = (e: Event) => {
      console.error("Audio error:", e);
      playingRef.current = false;
      setIsPlaying(false);
      
      // 重要：先检查处理队列的标记，防止重复处理
      if (!processingQueueRef.current && queueRef.current.length > 0) {
        console.log("Error occurred, trying next in queue...");
        processQueue();
      }
    };
    
    if (audioRef.current) {
      // 添加基本事件监听
      audioRef.current.addEventListener('ended', handleAudioEnd);
      audioRef.current.addEventListener('error', handleAudioError);
      
      // 添加额外事件用于调试
      audioRef.current.addEventListener('play', handleAudioEvent('play'));
      audioRef.current.addEventListener('playing', handleAudioEvent('playing'));
      audioRef.current.addEventListener('pause', handleAudioEvent('pause'));
      audioRef.current.addEventListener('waiting', handleAudioEvent('waiting'));
      audioRef.current.addEventListener('canplay', handleAudioEvent('canplay'));
    }
    
    // 组件卸载时的清理
    return () => {
      if (audioRef.current) {
        audioRef.current.removeEventListener('ended', handleAudioEnd);
        audioRef.current.removeEventListener('error', handleAudioError);
        // 移除额外事件监听器
        audioRef.current.removeEventListener('play', handleAudioEvent('play'));
        audioRef.current.removeEventListener('playing', handleAudioEvent('playing'));
        audioRef.current.removeEventListener('pause', handleAudioEvent('pause'));
        audioRef.current.removeEventListener('waiting', handleAudioEvent('waiting'));
        audioRef.current.removeEventListener('canplay', handleAudioEvent('canplay'));
        
        audioRef.current.pause();
        audioRef.current = null;
      }
      cleanup();
    };
  }, []);

  /**
   * 安全地处理队列 - 非异步包装函数
   * 这个函数确保在任何时候只有一个队列处理流程在进行
   */
  const processQueue = () => {
    // 如果已经在处理队列或者正在播放，直接返回
    if (processingQueueRef.current || playingRef.current) {
      console.log("Already processing queue or playing, skipping");
      return;
    }
    
    // 设置处理队列标记
    processingQueueRef.current = true;
    
    // 非异步调用，但内部会处理异步
    playNextInQueue().finally(() => {
      // 异步操作完成后，重置处理队列标记
      processingQueueRef.current = false;
    });
  };

  /**
   * 直接从URL播放音频
   */
  const playAudioFromUrl = (audioUrl: string): void => {
    // 追踪音频文件
    const fullUrl = audioUrl.startsWith('http') ? audioUrl : `${baseUrl}${audioUrl}`;
    
    const callId = Date.now().toString().substr(-4); // 用于日志追踪
    console.log(`[${callId}] 请求播放音频: ${fullUrl}`);
    console.log(`[${callId}] 当前队列长度: ${queueRef.current.length}`);
    console.log(`[${callId}] 当前播放状态: playingRef=${playingRef.current}, processingQueue=${processingQueueRef.current}`);

    // 添加到文件列表
    if (!audioFiles.includes(fullUrl)) {
      setAudioFiles(prev => [...prev, fullUrl]);
    }
    
    // 添加到队列
    queueRef.current.push(fullUrl);
    console.log(`[${callId}] 添加后队列长度: ${queueRef.current.length}`);
    
    // 如果当前没有播放且没有正在处理队列，启动队列处理
    if (!playingRef.current && !processingQueueRef.current) {
      console.log(`[${callId}] 开始处理队列`);
      processQueue();
    } else {
      console.log(`[${callId}] 已在播放或处理队列中，不启动新处理`);
    }
  };

  /**
   * 将音频添加到播放队列
   */
  const addToQueue = (audioUrl: string): void => {
    queueRef.current.push(audioUrl);
    
    // 如果当前没有播放且没有正在处理队列，启动队列处理
    if (!playingRef.current && !processingQueueRef.current) {
      processQueue();
    }
  };

  /**
   * 播放队列中的下一个音频
   * 注意：这是一个内部异步函数，不应直接调用
   * 应通过processQueue函数调用，以确保状态管理正确
   */
  const playNextInQueue = async (): Promise<void> => {
    const callId = Date.now().toString().substr(-4); // 用于日志追踪
    
    try {
      // 再次检查队列状态，防止条件发生变化
      if (queueRef.current.length === 0 || !audioRef.current) {
        console.log(`[${callId}] Queue empty or audio ref not available`);
        return;
      }
    
      // 已经在播放，不启动新的播放
      if (playingRef.current) {
        console.log(`[${callId}] Already playing, not starting new playback`);
        return;
      }
      
      // 从队列中获取下一个音频
      const nextAudio = queueRef.current.shift();
      if (!nextAudio) {
        console.log(`[${callId}] Shifted empty item from queue`);
        return;
      }
      
      // 标记正在播放
      playingRef.current = true;
      setIsPlaying(true);
      
      console.log(`[${callId}] Now playing from queue: ${nextAudio}`);
      console.log(`[${callId}] Remaining in queue: ${queueRef.current.length}`);
      
      // 检查文件是否存在可访问
      // const response = await fetch(nextAudio, { method: 'HEAD' });
      // if (!response.ok) {
      //   throw new Error(`File not accessible: ${response.status}`);
      // }
      
      // 检查Content-Length确认文件不为空
      // const contentLength = response.headers.get('content-length');
      // console.log(`[${callId}] Audio file size: ${contentLength} bytes`);
      
      // if (contentLength && parseInt(contentLength) < 100) {
      //   console.warn(`[${callId}] Audio file is too small, may be empty or corrupted`);
      // }
      
      // 设置当前播放音频
      setCurrentAudio(nextAudio);
      
      // 使用非阻塞方式加载和播放音频
      console.log(`[${callId}] Setting up audio element`);
      
      // 重要：创建新的Audio元素而不是重用
      const audioElement = new Audio();
      
      // 设置preload为"none"避免阻塞加载
      audioElement.preload = "none";
      
      // 监听错误
      audioElement.onerror = (e) => {
        console.error(`[${callId}] Audio error:`, e);
        playingRef.current = false;
        setIsPlaying(false);
        
        // 尝试队列中的下一个
        setTimeout(() => {
          if (queueRef.current.length > 0) {
            processQueue();
          }
        }, 0);
      };
      
      // 监听播放结束
      audioElement.onended = () => {
        console.log(`[${callId}] Audio ended`);
        playingRef.current = false;
        setIsPlaying(false);
        
        // 尝试队列中的下一个
        setTimeout(() => {
          if (queueRef.current.length > 0) {
            processQueue();
          }
        }, 0);
      };
      
      // 设置音频源
      audioElement.src = nextAudio;
      
      // 使用setTimeout非阻塞播放
      setTimeout(() => {
        console.log(`[${callId}] Starting playback with non-blocking approach`);
        
        // 尝试播放
        const playPromise = audioElement.play();
        
        if (playPromise) {
          playPromise
            .then(() => {
              console.log(`[${callId}] Successfully started playing: ${nextAudio}`);
              
              // 更新引用
              if (audioRef.current) {
                audioRef.current.pause();
              }
              audioRef.current = audioElement;
            })
            .catch(error => {
              console.error(`[${callId}] Play promise error:`, error);
              playingRef.current = false;
              setIsPlaying(false);
              
              // 尝试队列中的下一个
              if (queueRef.current.length > 0) {
                setTimeout(() => processQueue(), 0);
              }
            });
        }
      }, 0);
    } catch (error) {
      console.error(`[${callId}] Failed to play audio:`, error);
      
      // 重置状态
      playingRef.current = false;
      setIsPlaying(false);
      setCurrentAudio(null);
      
      // 如果队列中还有项目，尝试下一个
      if (queueRef.current.length > 0) {
        console.log(`[${callId}] Trying next audio in queue`);
        // 直接调用processQueue，它会检查状态并决定是否处理
        processQueue();
      }
    }
  };

  /**
   * 清理所有音频资源
   */
  const cleanup = (): void => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    queueRef.current = [];
    playingRef.current = false;
    processingQueueRef.current = false;
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
      queueLength: queueRef.current.length
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