import sys
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

class WebBrowserWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyQtWebEngine 浏览器')
        self.setGeometry(100, 100, 1024, 768)

        # 创建网页视图
        self.web_view = QWebEngineView()
        
        # 加载网页
        self.web_view.load(QUrl('http://localhost:5173/'))
        
        # 将网页视图设置为中心部件
        self.setCentralWidget(self.web_view)

# 更复杂的功能示例
class AdvancedWebBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('高级网页浏览器')
        self.setGeometry(100, 100, 1200, 800)

        # 创建网页视图
        self.web_view = QWebEngineView()
        
        # 添加导航栏
        self.create_navigation_bar()

        # 默认加载首页
        self.web_view.load(QUrl('https://www.python.org'))
        
        # 连接页面加载完成信号
        self.web_view.loadFinished.connect(self.on_page_load)

        # 将网页视图设置为中心部件
        self.setCentralWidget(self.web_view)

    def create_navigation_bar(self):
        # 这里可以添加前进、后退、刷新等按钮
        pass

    def on_page_load(self, ok):
        # 页面加载完成后的处理
        if ok:
            print("页面加载成功")
        else:
            print("页面加载失败")

def main():
    app = QApplication(sys.argv)
    browser = AdvancedWebBrowser()
    browser.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()