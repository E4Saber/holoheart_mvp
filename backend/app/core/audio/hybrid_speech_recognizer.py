# 混合识别器的简化实现示例
class HybridSpeechRecognizer:
    def __init__(self, local_model_path, server_address=None):
        # 初始化本地模型
        self.local_model = self._init_local_model(local_model_path)
        
        # 设置服务器连接
        self.server_address = server_address
        self.server_available = self._check_server_connection() if server_address else False
    
    def _init_local_model(self, model_path):
        """初始化本地Vosk模型"""
        from vosk import Model, KaldiRecognizer
        model = Model(model_path)
        recognizer = KaldiRecognizer(model, 16000)
        return recognizer
    
    def _check_server_connection(self):
        """检查与服务器的连接状态"""
        try:
            # 简单的连接测试代码
            import socket
            host, port = self.server_address.split(':')
            socket.create_connection((host, int(port)), timeout=1)
            return True
        except:
            return False
    
    def recognize_audio(self, audio_data, force_local=False, force_server=False):
        """混合模式识别音频"""
        # 确定使用哪种模式
        use_server = False
        if force_local:
            use_server = False
        elif force_server:
            use_server = self.server_available
        else:
            # 自动决定：在线优先使用服务器
            use_server = self.server_available
        
        # 根据决定使用相应模型
        if use_server:
            return self._server_recognition(audio_data)
        else:
            return self._local_recognition(audio_data)
    
    def _local_recognition(self, audio_data):
        """使用本地模型识别"""
        if self.local_model.AcceptWaveform(audio_data):
            result = json.loads(self.local_model.Result())
            return result["text"], "local"
        return "", "local"
    
    def _server_recognition(self, audio_data):
        """发送到服务器识别"""
        try:
            # 实际实现中应使用适当的网络通信代码
            # 这里仅为示例
            import requests
            response = requests.post(
                f"http://{self.server_address}/recognize",
                data=audio_data,
                timeout=3
            )
            if response.status_code == 200:
                result = response.json()
                return result["text"], "server"
        except Exception as e:
            print(f"服务器识别失败: {e}")
            # 如果服务器识别失败，自动回退到本地识别
            return self._local_recognition(audio_data)
        
        return "", "local"