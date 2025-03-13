# file_manager.py
import os
import shutil
import time
import tempfile

class AudioFileManager:
    """管理临时音频文件"""
    
    def __init__(self, temp_dir=None):
        # 如果没有指定临时目录，创建一个
        if temp_dir is None:
            self.temp_dir = os.path.join(tempfile.gettempdir(), f"kimi_tts_{int(time.time())}")
        else:
            self.temp_dir = temp_dir
        
        # 确保目录存在
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 初始化文件路径列表
        self.file_paths = []
        
        print(f"音频文件管理器初始化，临时目录: {self.temp_dir}")
    
    def add_file(self, file_path):
        """添加文件路径到管理列表"""
        if file_path and os.path.exists(file_path):
            self.file_paths.append(file_path)
            return True
        return False
    
    def create_temp_file(self, suffix=".mp3"):
        """创建临时文件并返回路径"""
        fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=self.temp_dir)
        os.close(fd)  # 关闭文件描述符
        
        # 添加到管理列表
        self.file_paths.append(temp_path)
        
        return temp_path
    
    def cleanup(self):
        """清理所有临时文件"""
        # 清理单个文件
        for path in self.file_paths:
            try:
                if os.path.exists(path):
                    os.unlink(path)
            except Exception as e:
                print(f"清理文件失败 {path}: {str(e)}")
        
        # 重置文件列表
        self.file_paths = []
        
        # 尝试清理整个临时目录
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"已删除临时目录: {self.temp_dir}")
        except Exception as e:
            print(f"删除临时目录失败 {self.temp_dir}: {str(e)}")
        
        # 重新创建临时目录
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def __del__(self):
        """析构函数，清理资源"""
        try:
            self.cleanup()
        except Exception as e:
            print(f"文件管理器析构时出错: {str(e)}")

# 测试代码
if __name__ == "__main__":
    # 创建文件管理器
    manager = AudioFileManager()
    
    # 创建几个临时文件
    paths = []
    for i in range(3):
        path = manager.create_temp_file()
        paths.append(path)
        
        # 写入一些测试数据
        with open(path, 'wb') as f:
            f.write(b'Test data')
        
        print(f"创建了临时文件: {path}")
    
    # 验证文件存在
    for path in paths:
        if os.path.exists(path):
            print(f"文件存在: {path}")
        else:
            print(f"文件不存在: {path}")
    
    # 清理文件
    print("清理文件...")
    manager.cleanup()
    
    # 验证文件已删除
    for path in paths:
        if os.path.exists(path):
            print(f"文件仍然存在: {path}")
        else:
            print(f"文件已删除: {path}")