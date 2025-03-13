import sys
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget, QMainWindow, QDesktopWidget
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl

# 宠物角色
class DesktopPet(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background: red;")
        self.setText("🐾 点击我看看~")
        self.setStyleSheet("font-size: 18px; color: white; background: #4CAF50; padding: 10px; border-radius: 8px;")
        self.resize(120, 50)
        self.show()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.show_info_window()

    def show_info_window(self):
        self.info_window = InfoWindow()
        self.info_window.show()

# 信息窗体
class InfoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("信息展示")
        self.setGeometry(100, 100, 400, 300)

        # 内容展示区域
        layout = QVBoxLayout()

        # 文字
        text_label = QLabel("🌟 这是一个宠物触发的窗口，欢迎体验！")
        text_label.setStyleSheet("font-size: 20px; color: #333;")
        layout.addWidget(text_label)

        # 图片
        # img_label = QLabel()
        # img_label.setPixmap("example_image.png")  # 替换成您的图片
        # layout.addWidget(img_label)

        # 视频
        # video_widget = QVideoWidget()
        # self.media_player = QMediaPlayer()
        # self.media_player.setMedia(QMediaContent(QUrl.fromLocalFile("example_video.mp4")))  # 替换成您的视频
        # self.media_player.setVideoOutput(video_widget)
        # self.media_player.play()
        # layout.addWidget(video_widget)

        # 关闭按钮
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)

        # 设置主窗口布局
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = DesktopPet()
    sys.exit(app.exec_())
