// src/workers/audioWorker.js

// 音频工作线程处理音频加载和解码
self.addEventListener('message', async function(e) {
    const { type, url, id } = e.data;
    
    if (type === 'load') {
      try {
        // 获取音频数据
        const response = await fetch(url);
        if (!response.ok) {
          throw new Error(`Failed to fetch audio: ${response.status}`);
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