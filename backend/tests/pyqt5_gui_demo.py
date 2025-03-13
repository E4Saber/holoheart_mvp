import sys
import random
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QTimer

class DesktopCharacter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        # 设置窗口属性
        self.setWindowTitle('桌面小助手')
        self.setGeometry(100, 100, 300, 400)
        
        # 设置窗口始终置顶且无边框
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        
        # 创建中心widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建布局
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
        # 角色图像
        self.character_image = QLabel()
        # 这里可以替换成你自己的图片路径
        pixmap = QPixmap('character.png')  # 注意: 实际使用时需要准备图片
        self.character_image.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio))
        self.character_image.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.character_image)
        
        # 状态文本
        self.status_label = QLabel('你好,我是你的桌面助手!')
        self.status_label.setFont(QFont('微软雅黑', 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # 互动按钮
        self.interact_button = QPushButton('聊天')
        self.interact_button.clicked.connect(self.change_mood)
        layout.addWidget(self.interact_button)
        
        # 定时更新状态
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.random_status)
        self.timer.start(10000)  # 每10秒随机更新一次状态
        
    def change_mood(self):
        """模拟角色交互"""
        moods = ['开心', '惊讶', '困惑', '兴奋']
        mood = random.choice(moods)
        self.status_label.setText(f'现在我感到{mood}!')
        
    def random_status(self):
        """随机状态变化"""
        status_list = [
            '我在这里哦~',
            '需要帮助吗?',
            '今天过得怎么样?',
            '别忘了休息!'
        ]
        self.status_label.setText(random.choice(status_list))

def main():
    app = QApplication(sys.argv)
    character = DesktopCharacter()
    character.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()