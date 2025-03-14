// src/hooks/useParallelAudioManager.ts
import { useState, useEffect, useRef } from 'react';

export interface ParallelAudioManager {
  playAudioFromUrl: (audioUrl: string, priority?: number) => void;
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

interface AudioMessage {
  type: string;
  url?: string;
  priority?: number;
  queueLength?: number;
  error?: string;
}

/**
 * 并行音频管理器 - 使用独立Worker处理音频，避免UI阻塞
 * 这个设计完全分离音频处理和React渲染循环
 */
export const useParallelAudioManager = (apiUrl: string = ''): ParallelAudioManager => {
  const [audioFiles, setAudioFiles] = useState<string[]>([]);
  const [currentAudio, setCurrentAudio] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [queueLength, setQueueLength] = useState<number>(0);
  
  // 音频上下文和工作线程
  const audioContextRef = useRef<AudioContext | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const audioElementsRef = useRef<Map<string, HTMLAudioElement>>(new Map());
  
  const baseUrl = apiUrl || window.location.origin;

  // 初始化音频处理系统
  useEffect(() => {
    // 创建AudioContext
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    audioContextRef.current = new AudioContextClass();
    
    // 创建Worker的核心函数 - 使用Blob URL
    const createAudioWorker = () => {
      // Worker代码 - 必须是完整的、独立的JavaScript代码
      const workerCode = `
        // 音频队列
        let audioQueue = [];
        let isPlaying = false;
        
        // 处理从主线程接收的消息
        self.addEventListener('message', function(e) {
          const { type, url, priority, operation } = e.data;
          
          if (type === 'init') {
            // 初始化音频处理器
            self.postMessage({ type: 'initialized' });
          } 
          else if (type === 'queue') {
            // 添加音频到队列
            audioQueue.push({ url, priority });
            
            // 按优先级排序 - 数字越小优先级越高
            audioQueue.sort((a, b) => a.priority - b.priority);
            
            // 通知主线程更新队列状态
            self.postMessage({ 
              type: 'queueUpdate', 
              queueLength: audioQueue.length 
            });
            
            // 如果不在播放，开始处理队列
            if (!isPlaying) {
              processNextAudio();
            }
          }
          else if (type === 'control') {
            // 处理控制命令
            handleControlCommand(operation);
          }
          else if (type === 'played') {
            // 主线程通知音频播放完成
            if (isPlaying) {
              // 继续处理队列
              processNextAudio();
            }
          }
        });
        
        // 处理控制命令
        function handleControlCommand(operation) {
          switch(operation) {
            case 'pause':
              isPlaying = false;
              self.postMessage({ type: 'paused' });
              break;
            case 'resume':
              if (!isPlaying && audioQueue.length > 0) {
                isPlaying = true;
                processNextAudio();
                self.postMessage({ type: 'resumed' });
              }
              break;
            case 'skip':
              // 跳到下一个音频
              if (isPlaying) {
                // 设置标记，让当前处理结束后立即开始下一个
                isPlaying = false;
                self.postMessage({ type: 'skipped' });
                
                // 立即处理下一个
                setTimeout(() => {
                  if (audioQueue.length > 0) {
                    isPlaying = true;
                    processNextAudio();
                  }
                }, 0);
              }
              break;
            case 'clear':
              // 清空队列
              audioQueue = [];
              isPlaying = false;
              self.postMessage({ 
                type: 'queueUpdate', 
                queueLength: 0 
              });
              break;
          }
        }
        
        // 处理队列中的下一个音频
        function processNextAudio() {
          if (audioQueue.length === 0) {
            isPlaying = false;
            self.postMessage({ type: 'idle' });
            return;
          }
          
          isPlaying = true;
          
          // 获取队列中优先级最高的音频
          const nextAudio = audioQueue.shift();
          
          // 通知主线程开始加载
          self.postMessage({ 
            type: 'loading', 
            url: nextAudio.url 
          });
          
          // 通知主线程播放此URL
          self.postMessage({ 
            type: 'play', 
            url: nextAudio.url 
          });
          
          // 更新队列状态
          self.postMessage({ 
            type: 'queueUpdate', 
            queueLength: audioQueue.length 
          });
        }
      `;
      
      // 创建Blob和URL
      const blob = new Blob([workerCode], { type: 'application/javascript' });
      const workerUrl = URL.createObjectURL(blob);
      
      // 创建Worker
      const worker = new Worker(workerUrl);
      
      // 在创建后释放URL
      URL.revokeObjectURL(workerUrl);
      
      return worker;
    };
    
    // 创建Worker
    try {
      workerRef.current = createAudioWorker();
      
      // 设置消息监听
      workerRef.current.onmessage = handleWorkerMessage;
      
      // 初始化Worker
      workerRef.current.postMessage({ type: 'init' });
    } catch (error) {
      console.error('创建音频处理Worker失败:', error);
    }
    
    // 清理函数
    return () => {
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(console.error);
      }
      
      if (workerRef.current) {
        workerRef.current.terminate();
      }
      
      // 清理所有音频元素
      audioElementsRef.current.forEach(audio => {
        audio.pause();
        audio.src = '';
      });
      audioElementsRef.current.clear();
    };
  }, []);

  // 处理Worker发送的消息
  const handleWorkerMessage = (e: MessageEvent<AudioMessage>) => {
    const { type, url, queueLength: newQueueLength, error } = e.data;
    
    switch (type) {
      case 'initialized':
        console.log('音频处理Worker初始化完成');
        break;
        
      case 'queueUpdate':
        if (typeof newQueueLength === 'number') {
          setQueueLength(newQueueLength);
        }
        break;
        
      case 'loading':
        if (url) {
          console.log(`加载音频: ${url}`);
          // 预加载音频
          preloadAudio(url);
        }
        break;
        
      case 'play':
        if (url) {
          console.log(`播放音频: ${url}`);
          setIsPlaying(true);
          setCurrentAudio(url);
          
          // 播放音频
          playAudio(url).then(() => {
            // 通知Worker音频播放完成
            workerRef.current?.postMessage({ 
              type: 'played', 
              url 
            });
          }).catch(err => {
            console.error(`播放音频失败: ${url}`, err);
            // 通知Worker发生错误
            workerRef.current?.postMessage({ 
              type: 'error', 
              url, 
              error: err.message 
            });
          });
        }
        break;
        
      case 'paused':
        setIsPlaying(false);
        // 暂停当前音频
        if (currentAudio) {
          const audio = audioElementsRef.current.get(currentAudio);
          if (audio) {
            audio.pause();
          }
        }
        break;
        
      case 'resumed':
        setIsPlaying(true);
        // 恢复当前音频
        if (currentAudio) {
          const audio = audioElementsRef.current.get(currentAudio);
          if (audio) {
            audio.play().catch(console.error);
          }
        }
        break;
        
      case 'skipped':
        // 跳过当前音频
        if (currentAudio) {
          const audio = audioElementsRef.current.get(currentAudio);
          if (audio) {
            audio.pause();
            audio.currentTime = audio.duration || 0;
          }
          
          // 通知Worker当前音频已完成
          workerRef.current?.postMessage({ 
            type: 'played', 
            url: currentAudio 
          });
        }
        break;
        
      case 'idle':
        setIsPlaying(false);
        setCurrentAudio(null);
        break;
        
      case 'error':
        console.error(`音频处理错误: ${error}`);
        // 出错时继续处理队列
        if (url) {
          workerRef.current?.postMessage({ 
            type: 'played', 
            url 
          });
        }
        break;
    }
  };

  // 预加载音频
  const preloadAudio = (url: string): void => {
    // 检查是否已经有这个URL的音频元素
    if (audioElementsRef.current.has(url)) {
      return; // 已经预加载过
    }
    
    // 创建新的音频元素
    const audio = new Audio();
    audio.preload = 'auto';
    audio.src = url;
    
    // 存储音频元素
    audioElementsRef.current.set(url, audio);
    
    // 追踪音频文件列表
    setAudioFiles(prev => {
      if (prev.includes(url)) return prev;
      return [...prev, url];
    });
  };

  // 播放音频
  const playAudio = async (url: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      // 获取音频元素
      let audio = audioElementsRef.current.get(url);
      
      // 如果没有预加载，创建新的音频元素
      if (!audio) {
        audio = new Audio(url);
        audioElementsRef.current.set(url, audio);
      }
      
      // 设置事件监听
      const onEnded = () => {
        audio!.removeEventListener('ended', onEnded);
        audio!.removeEventListener('error', onError);
        resolve();
      };
      
      const onError = (e: ErrorEvent) => {
        audio!.removeEventListener('ended', onEnded);
        audio!.removeEventListener('error', onError);
        reject(new Error(`音频播放错误: ${e.message}`));
      };
      
      audio.addEventListener('ended', onEnded);
      audio.addEventListener('error', onError);
      
      // 开始播放
      audio.play().catch(err => {
        audio!.removeEventListener('ended', onEnded);
        audio!.removeEventListener('error', onError);
        reject(err);
      });
    });
  };

  /**
   * 将音频URL添加到播放队列
   */
  const playAudioFromUrl = (audioUrl: string, priority: number = 0): void => {
    // 确保Worker已经初始化
    if (!workerRef.current) {
      console.error('音频处理Worker未初始化');
      return;
    }
    
    // 构建完整URL
    const fullUrl = audioUrl.startsWith('http') ? audioUrl : `${baseUrl}${audioUrl}`;
    
    // 发送到Worker处理
    workerRef.current.postMessage({
      type: 'queue',
      url: fullUrl,
      priority: priority
    });
  };

  /**
   * 暂停所有音频播放
   */
  const pauseAll = (): void => {
    if (workerRef.current) {
      workerRef.current.postMessage({
        type: 'control',
        operation: 'pause'
      });
    }
  };

  /**
   * 恢复所有音频播放
   */
  const resumeAll = (): void => {
    if (workerRef.current) {
      workerRef.current.postMessage({
        type: 'control',
        operation: 'resume'
      });
    }
  };

  /**
   * 跳过当前播放的音频
   */
  const skipCurrent = (): void => {
    if (workerRef.current) {
      workerRef.current.postMessage({
        type: 'control',
        operation: 'skip'
      });
    }
  };

  /**
   * 清理所有音频资源
   */
  const cleanup = (): void => {
    if (workerRef.current) {
      workerRef.current.postMessage({
        type: 'control',
        operation: 'clear'
      });
    }
    
    // 清理所有音频元素
    audioElementsRef.current.forEach(audio => {
      audio.pause();
      audio.src = '';
    });
    audioElementsRef.current.clear();
    
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
      queueLength
    };
  };

  return {
    playAudioFromUrl,
    pauseAll,
    resumeAll,
    skipCurrent,
    cleanup,
    getAudioStatus,
    audioFiles
  };
};