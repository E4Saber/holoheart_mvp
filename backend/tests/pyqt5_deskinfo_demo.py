import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QDesktopWidget, QSystemTrayIcon
from PyQt5.QtGui import QScreen, QGuiApplication, QIcon
from PyQt5.QtCore import QSize, QStyle

class DesktopInfoApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('桌面信息查看器')
        self.setGeometry(100, 100, 500, 600)
        
        # 创建中心部件和布局
        central_widget = QWidget()
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        
        # 获取桌面信息
        desktop_info = self.get_desktop_info()
        
        # 显示信息的标签
        for info in desktop_info:
            label = QLabel(info)
            layout.addWidget(label)
    
    def get_desktop_info(self):
        # 获取桌面信息的方法
        info_list = []
        
        # 使用 QDesktopWidget 获取屏幕信息
        desktop = QApplication.desktop()
        
        # 屏幕数量
        screen_count = desktop.screenCount()
        info_list.append(f"屏幕数量: {screen_count}")
        
        # 主屏幕信息
        primary_screen = desktop.primaryScreen()
        info_list.append(f"主屏幕序号: {primary_screen}")
        
        # 获取屏幕几何信息
        for i in range(screen_count):
            screen_rect = desktop.screenGeometry(i)
            info_list.append(f"屏幕 {i} 分辨率: {screen_rect.width()} x {screen_rect.height()}")
        
        # 使用 QGuiApplication 获取屏幕信息
        screens = QGuiApplication.screens()
        for idx, screen in enumerate(screens):
            # 屏幕物理尺寸
            physical_size = screen.physicalSize()
            info_list.append(f"屏幕 {idx} 物理尺寸: {physical_size.width()} x {physical_size.height()} mm")
            
            # 屏幕逻辑分辨率
            logical_size = screen.size()
            info_list.append(f"屏幕 {idx} 逻辑分辨率: {logical_size.width()} x {logical_size.height()}")
            
            # 屏幕缩放因子
            dpi = screen.logicalDotsPerInch()
            info_list.append(f"屏幕 {idx} DPI: {dpi}")
        
        # 系统托盘图标信息
        if QSystemTrayIcon.isSystemTrayAvailable():
            info_list.append("系统托盘可用")
        else:
            info_list.append("系统托盘不可用")
        
        return info_list

def main():
    app = QApplication(sys.argv)
    window = DesktopInfoApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

# 额外的屏幕信息获取示例
def get_more_desktop_details():
    """获取更多桌面和系统详细信息的额外方法"""
    # 获取所有屏幕
    screens = QGuiApplication.screens()
    
    for idx, screen in enumerate(screens):
        # 屏幕名称
        print(f"屏幕 {idx} 名称: {screen.name()}")
        
        # 屏幕可用几何区域（排除任务栏等）
        available_geometry = screen.availableGeometry()
        print(f"屏幕 {idx} 可用区域: {available_geometry.width()} x {available_geometry.height()}")
        
        # 颜色深度
        color_depth = screen.depth()
        print(f"屏幕 {idx} 颜色深度: {color_depth}")

# 获取系统图标的示例
def get_system_icons():
    """获取系统图标"""
    # 获取应用程序图标
    app_icon = QApplication.windowIcon()
    
    # 获取系统图标（如果支持）
    # 注意：具体图标可能因操作系统而异
    style = QApplication.style()
    
    # 一些常见的系统图标
    icon_types = [
        'SP_ComputerIcon',
        'SP_DesktopIcon',
        'SP_TrashIcon',
        'SP_FileIcon',
        'SP_DirOpenIcon',
        'SP_DirClosedIcon'
    ]
    
    for icon_type in icon_types:
        icon = style.standardIcon(getattr(QStyle, icon_type))
        print(f"{icon_type} 图标大小: {icon.actualSize(QSize(32, 32))}")