// src/workers/audioProcessingWorker.js

// 音频处理工作线程
// 完全独立于主线程的渲染循环

// 音频队列
let audioQueue = [];
let isPlaying = false;
let audioContext = null;

// 处理从主线程接收的消息
self.addEventListener('message', async function(e) {
  const { type, url, priority, audioData, operation } = e.data;
  
  if (type === 'init') {
    // 初始化音频处理器
    // 注意：Web Worker中不能直接创建AudioContext
    // 而是处理音频数据并发送回主线程播放
    self.postMessage({ type: 'initialized' });
  } 
  else if (type === 'queue') {
    // 添加音频到队列
    audioQueue.push({ url, priority });
    
    // 按优先级排序
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
async function processNextAudio() {
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
  
  try {
    // 通知主线程开始播放此URL
    self.postMessage({ 
      type: 'play', 
      url: nextAudio.url 
    });
    
    // 等待主线程确认播放完成
    // 实际应用中，这里应实现一个Promise等待主线程的'played'消息
    
    // 为了简化示例，我们使用setTimeout模拟等待播放完成
    await new Promise(resolve => {
      // 设置一个消息处理器等待播放完成
      const messageHandler = function(evt) {
        if (evt.data.type === 'played' && evt.data.url === nextAudio.url) {
          self.removeEventListener('message', messageHandler);
          resolve();
        }
      };
      
      self.addEventListener('message', messageHandler);
      
      // 同时设置一个超时，防止无限等待
      setTimeout(() => {
        self.removeEventListener('message', messageHandler);
        resolve();
      }, 10000); // 最长等待10秒
    });
    
  } catch (error) {
    // 通知主线程错误情况
    self.postMessage({ 
      type: 'error', 
      url: nextAudio.url,
      error: error.message 
    });
  }
  
  // 处理下一个音频
  if (isPlaying) {
    // 添加一个微小延迟，避免过快处理
    setTimeout(() => processNextAudio(), 10);
  }
  
  // 更新队列状态
  self.postMessage({ 
    type: 'queueUpdate', 
    queueLength: audioQueue.length 
  });
}