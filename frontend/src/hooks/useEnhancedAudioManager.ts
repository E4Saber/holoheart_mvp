// src/hooks/useEnhancedAudioManager.ts
import { useState, useEffect, useRef } from 'react';

export interface EnhancedAudioManager {
  playAudioFromUrl: (audioUrl: string, priority?: number) => void;
  addToQueue: (audioUrl: string, priority?: number) => void;
  pauseAll: () => void;
  resumeAll: () => void;
  skipCurrent: () => void;
  cleanup: () => void;
  getAudioStatus: () => AudioStatus;
  audioFiles: string[];
}

interface AudioStatus {
  isPlaying: boolean;
  currentAudio: string | null;
  queueLength: number;
}

interface QueueItem {
  url: string;
  priority: number;
  buffer?: AudioBuffer;
  id: string;
}

export const useEnhancedAudioManager = (apiUrl: string = ''): EnhancedAudioManager => {
  const [audioFiles, setAudioFiles] = useState<string[]>([]);
  const [currentAudio, setCurrentAudio] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  
  // 使用useRef替代useState来管理队列
  const queueRef = useRef<QueueItem[]>([]);
  const playingRef = useRef<boolean>(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const currentSourceRef = useRef<AudioBufferSourceNode | null>(null);
  const audioBufferCacheRef = useRef<Map<string, AudioBuffer>>(new Map());
  const workerRef = useRef<Worker | null>(null);
  const processingQueueRef = useRef<boolean>(false);
  const uniqueIdCounterRef = useRef<number>(0);
  
  const baseUrl = apiUrl || window.location.origin;

  // 初始化Web Audio API和Web Worker
  useEffect(() => {
    // 创建AudioContext
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    audioContextRef.current = new AudioContextClass();
    
    // 创建Web Worker
    try {
      // 因为Web Worker需要一个独立的JS文件，我们需要创建一个Blob URL
      const workerCode = `
        self.addEventListener('message', async function(e) {
          const { type, url, id } = e.data;
          
          if (type === 'load') {
            try {
              // 获取音频数据
              const response = await fetch(url);
              if (!response.ok) {
                throw new Error('Failed to fetch audio: ' + response.status);
              }
              
              // 获取ArrayBuffer
              const arrayBuffer = await response.arrayBuffer();
              
              // 发送回主线程
              self.postMessage({
                type: 'loaded',
                buffer: arrayBuffer,
                id: id,
                url: url
              });
            } catch (error) {
              self.postMessage({
                type: 'error',
                error: error.message,
                id: id,
                url: url
              });
            }
          }
        });
      `;
      
      const blob = new Blob([workerCode], { type: 'application/javascript' });
      const workerUrl = URL.createObjectURL(blob);
      workerRef.current = new Worker(workerUrl);
      
      // 处理Worker消息
      workerRef.current.onmessage = async (e) => {
        const { type, buffer, id, url } = e.data;
        
        if (type === 'loaded') {
          try {
            // 解码音频数据
            const audioBuffer = await audioContextRef.current!.decodeAudioData(buffer);
            
            // 缓存解码后的AudioBuffer
            audioBufferCacheRef.current.set(url, audioBuffer);
            
            // 更新队列中的项目
            queueRef.current = queueRef.current.map(item => {
              if (item.id === id) {
                return { ...item, buffer: audioBuffer };
              }
              return item;
            });
            
            // 如果当前没有播放且没有正在处理队列，启动队列处理
            if (!playingRef.current && !processingQueueRef.current) {
              processQueue();
            }
          } catch (error) {
            console.error('Failed to decode audio data:', error);
            
            // 从队列中移除失败的项目
            queueRef.current = queueRef.current.filter(item => item.id !== id);
            
            // 如果当前没有播放且没有正在处理队列，启动队列处理
            if (!playingRef.current && !processingQueueRef.current) {
              processQueue();
            }
          }
        } else if (type === 'error') {
          console.error('Worker error loading audio:', e.data.error);
          
          // 从队列中移除失败的项目
          queueRef.current = queueRef.current.filter(item => item.id !== id);
          
          // 如果当前没有播放且没有正在处理队列，启动队列处理
          if (!playingRef.current && !processingQueueRef.current) {
            processQueue();
          }
        }
      };
      
      // 在不用的时候释放BlobURL
      URL.revokeObjectURL(workerUrl);
    } catch (error) {
      console.error('Failed to create Web Worker:', error);
      // 降级为不使用Worker的实现
    }
    
    // 组件卸载时的清理
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      
      if (workerRef.current) {
        workerRef.current.terminate();
      }
      
      cleanup();
    };
  }, []);

  /**
   * 解码和缓存音频数据
   */
  const loadAndDecodeAudio = (url: string, id: string): void => {
    // 如果已经缓存了这个URL的AudioBuffer，不需要重新加载
    if (audioBufferCacheRef.current.has(url)) {
      // 更新队列中的项目
      queueRef.current = queueRef.current.map(item => {
        if (item.id === id) {
          return { ...item, buffer: audioBufferCacheRef.current.get(url) };
        }
        return item;
      });
      
      // 如果当前没有播放且没有正在处理队列，启动队列处理
      if (!playingRef.current && !processingQueueRef.current) {
        processQueue();
      }
      
      return;
    }
    
    // 使用Worker加载音频
    if (workerRef.current) {
      workerRef.current.postMessage({
        type: 'load',
        url,
        id
      });
    } else {
      // 降级实现：直接在主线程加载
      fetch(url)
        .then(response => {
          if (!response.ok) {
            throw new Error(`Failed to fetch audio: ${response.status}`);
          }
          return response.arrayBuffer();
        })
        .then(arrayBuffer => audioContextRef.current!.decodeAudioData(arrayBuffer))
        .then(audioBuffer => {
          // 缓存解码后的AudioBuffer
          audioBufferCacheRef.current.set(url, audioBuffer);
          
          // 更新队列中的项目
          queueRef.current = queueRef.current.map(item => {
            if (item.id === id) {
              return { ...item, buffer: audioBuffer };
            }
            return item;
          });
          
          // 如果当前没有播放且没有正在处理队列，启动队列处理
          if (!playingRef.current && !processingQueueRef.current) {
            processQueue();
          }
        })
        .catch(error => {
          console.error('Failed to load or decode audio:', error);
          
          // 从队列中移除失败的项目
          queueRef.current = queueRef.current.filter(item => item.id !== id);
          
          // 如果当前没有播放且没有正在处理队列，启动队列处理
          if (!playingRef.current && !processingQueueRef.current) {
            processQueue();
          }
        });
    }
  };

  /**
   * 安全地处理队列
   */
  const processQueue = (): void => {
    // 如果已经在处理队列或者正在播放，直接返回
    if (processingQueueRef.current || playingRef.current) {
      console.log("Already processing queue or playing, skipping");
      return;
    }
    
    // 设置处理队列标记
    processingQueueRef.current = true;
    
    try {
      // 检查队列是否为空
      if (queueRef.current.length === 0) {
        processingQueueRef.current = false;
        return;
      }
      
      // 按优先级排序队列
      queueRef.current.sort((a, b) => b.priority - a.priority);
      
      // 查找第一个具有已解码音频缓冲区的项目
      const readyItemIndex = queueRef.current.findIndex(item => item.buffer);
      
      if (readyItemIndex >= 0) {
        // 有准备好的音频，播放它
        const item = queueRef.current[readyItemIndex];
        
        // 从队列中移除
        queueRef.current.splice(readyItemIndex, 1);
        
        // 播放音频
        playAudioBuffer(item.buffer!, item.url);
      } else {
        // 没有准备好的音频，尝试加载队列中的第一个项目
        const item = queueRef.current[0];
        loadAndDecodeAudio(item.url, item.id);
        
        // 重置处理队列标记，因为加载是异步的
        processingQueueRef.current = false;
      }
    } catch (error) {
      console.error('Error processing audio queue:', error);
      processingQueueRef.current = false;
    }
  };

  /**
   * 播放解码后的AudioBuffer
   */
  const playAudioBuffer = (buffer: AudioBuffer, url: string): void => {
    if (!audioContextRef.current) {
      console.error('AudioContext not initialized');
      processingQueueRef.current = false;
      return;
    }
    
    try {
      // 创建音频源
      const source = audioContextRef.current.createBufferSource();
      source.buffer = buffer;
      source.connect(audioContextRef.current.destination);
      
      // 保存当前源引用
      currentSourceRef.current = source;
      
      // 设置结束事件处理
      source.onended = () => {
        playingRef.current = false;
        setIsPlaying(false);
        setCurrentAudio(null);
        currentSourceRef.current = null;
        
        // 继续处理队列
        processingQueueRef.current = false;
        if (queueRef.current.length > 0) {
          processQueue();
        }
      };
      
      // 开始播放
      source.start();
      playingRef.current = true;
      setIsPlaying(true);
      setCurrentAudio(url);
      
    } catch (error) {
      console.error('Error playing audio buffer:', error);
      
      // 重置状态
      playingRef.current = false;
      setIsPlaying(false);
      setCurrentAudio(null);
      currentSourceRef.current = null;
      
      // 继续处理队列
      processingQueueRef.current = false;
      if (queueRef.current.length > 0) {
        processQueue();
      }
    }
  };

  /**
   * 直接从URL播放音频
   */
  const playAudioFromUrl = (audioUrl: string, priority: number = 0): void => {
    // 追踪音频文件
    const fullUrl = audioUrl.startsWith('http') ? audioUrl : `${baseUrl}${audioUrl}`;
    
    // 创建唯一ID
    const id = `audio_${Date.now()}_${uniqueIdCounterRef.current++}`;
    
    console.log(`请求播放音频: ${fullUrl}，优先级: ${priority}`);
    
    // 添加到文件列表
    if (!audioFiles.includes(fullUrl)) {
      setAudioFiles(prev => [...prev, fullUrl]);
    }
    
    // 添加到队列
    queueRef.current.push({
      url: fullUrl,
      priority,
      id
    });
    
    // 如果当前没有播放且没有正在处理队列，启动队列处理
    if (!playingRef.current && !processingQueueRef.current) {
      processQueue();
    }
  };

  /**
   * 将音频添加到播放队列
   */
  const addToQueue = (audioUrl: string, priority: number = 0): void => {
    const fullUrl = audioUrl.startsWith('http') ? audioUrl : `${baseUrl}${audioUrl}`;
    
    // 创建唯一ID
    const id = `audio_${Date.now()}_${uniqueIdCounterRef.current++}`;
    
    queueRef.current.push({
      url: fullUrl,
      priority,
      id
    });
    
    // 如果当前没有播放且没有正在处理队列，启动队列处理
    if (!playingRef.current && !processingQueueRef.current) {
      processQueue();
    }
  };

  /**
   * 暂停所有音频播放
   */
  const pauseAll = (): void => {
    if (audioContextRef.current && audioContextRef.current.state === 'running') {
      audioContextRef.current.suspend();
    }
  };

  /**
   * 恢复所有音频播放
   */
  const resumeAll = (): void => {
    if (audioContextRef.current && audioContextRef.current.state === 'suspended') {
      audioContextRef.current.resume();
    }
  };

  /**
   * 跳过当前播放的音频
   */
  const skipCurrent = (): void => {
    if (currentSourceRef.current) {
      currentSourceRef.current.stop();
      // onended事件处理会处理后续逻辑
    }
  };

  /**
   * 清理所有音频资源
   */
  const cleanup = (): void => {
    if (currentSourceRef.current) {
      try {
        currentSourceRef.current.stop();
      } catch (e) {
        // 忽略错误，可能已经停止
      }
      currentSourceRef.current = null;
    }
    
    queueRef.current = [];
    audioBufferCacheRef.current.clear();
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
    pauseAll,
    resumeAll,
    skipCurrent,
    cleanup,
    getAudioStatus,
    audioFiles
  };
};