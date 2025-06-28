import sys
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QProgressBar,
    QLabel, QVBoxLayout, QWidget, QDialog, QTreeWidget,
    QTreeWidgetItem, QSplitter, QFileDialog, QPushButton, 
    QMessageBox
)
from PyQt6.QtCore import QUrl, QTimer, QPropertyAnimation, QEasingCurve, Qt, QPoint
from PyQt6.QtGui import QAction, QFont, QIcon, QPalette, QActionGroup
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply


# 检测系统是否为深色模式
def is_dark_mode():
    app = QApplication.instance()
    if not app:
        return False
    if not app or not isinstance(app, QApplication):
        return False

    # 获取窗口背景色
    bg_color = app.palette().color(QPalette.ColorRole.Window)
    # 计算亮度 (0-255)
    brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) // 1000
    # 如果亮度低于128，则认为是深色模式
    return brightness < 128


# 获取动态样式表
def get_dynamic_stylesheet():
    if is_dark_mode():
        # 深色模式样式表
        return """
            QMainWindow {
                background-color: #2D2D2D;
            }
            QMenuBar {
                background-color: #333333;
                padding: 2px;
                color: #E0E0E0;
            }
            QMenuBar::item {
                padding: 4px 10px;
                background: transparent;
                color: #E0E0E0;
            }
            QMenuBar::item:selected {
                background-color: #555555;
            }
            QMenu {
                background-color: #333333;
                border: 1px solid #444444;
                padding: 5px;
                color: #E0E0E0;
            }
            QMenu::item {
                padding: 5px 30px 5px 20px;
                color: #E0E0E0;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QTreeWidget {
                background-color: #252525;
                border: 1px solid #444444;
                border-radius: 4px;
                color: #E0E0E0;
            }
            QTreeWidget::item {
                color: #E0E0E0;
            }
            QTreeWidget::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QHeaderView::section {
                background-color: #333333;
                color: #E0E0E0;
                padding: 4px;
                border: 1px solid #444444;
            }
            QSplitter::handle {
                background-color: #444444;
            }
            QLabel {
                color: #E0E0E0;
            }
            QStatusBar {
                color: #E0E0E0;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #333333;
                color: #888888;
            }
            QProgressBar {
                border: 2px solid #444444;
                border-radius: 5px;
                text-align: center;
                background-color: #333333;
                height: 20px;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """
    else:
        # 浅色模式样式表
        return """
            QMainWindow {
                background-color: #f0f0f0;
            }
            QMenuBar {
                background-color: #e0e0e0;
                padding: 2px;
            }
            QMenuBar::item {
                padding: 4px 10px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background-color: #d0d0d0;
            }
            QMenu {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 30px 5px 20px;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QTreeWidget {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QSplitter::handle {
                background-color: #d0d0d0;
            }
            QProgressBar {
                border: 2px solid #5c5c5c;
                border-radius: 5px;
                text-align: center;
                background-color: #333333;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """


class DownloadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("下载进度")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 动态设置样式表
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(50, 50, 50, 220);
                border-radius: 10px;
                padding: 15px;
            }
            QLabel {
                font-size: 12pt;
            }
            QProgressBar {
                border-radius: 5px;
                text-align: center;
                background-color: #333333;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)

        # 创建布局和控件
        layout = QVBoxLayout(self)

        self.title_label = QLabel("正在下载...")
        self.title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        self.filename_label = QLabel("")
        self.filename_label.setFont(QFont("Arial", 10))
        self.filename_label.setStyleSheet("color: #CCCCCC;")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)

        layout.addWidget(self.title_label)
        layout.addWidget(self.filename_label)
        layout.addWidget(self.progress_bar)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        self.setFixedSize(350, 150)

        # 动画效果
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(1000)  # 1秒动画
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.fade_animation.finished.connect(self.hide)

    def set_download_info(self, title, filename):
        """设置下载信息"""
        self.title_label.setText(title)
        self.filename_label.setText(f"文件: {filename}")
        self.progress_bar.setValue(0)

    def update_progress(self, value):
        """更新进度"""
        self.progress_bar.setValue(value)

    def fade_out(self):
        """淡出动画"""
        self.fade_animation.start()

    def show_at_bottom_right(self, parent):
        """在父窗口右下角显示"""
        if parent:
            # 计算右下角位置
            parent_rect = parent.geometry()
            x = parent_rect.right() - self.width() - 20
            y = parent_rect.bottom() - self.height() - 20
            self.move(QPoint(x, y))
        self.show()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("期末无挂")
        self.setGeometry(100, 100, 1000, 700)
        # 存储目录数据
        self.directory_data = None

        # 当前选中的文件信息
        self.selected_file = None

        # 下载源
        self.current_source = "gitee"

        # 配置文件路径
        self.config_file = "config.json"

        # 加载配置
        self.load_config()

        # 网络管理器
        self.network_manager = QNetworkAccessManager()

        # 下载对话框
        self.download_dialog = DownloadDialog(self)

        # 创建菜单栏
        self.create_menubar()

        # 状态栏
        self.status_bar = self.statusBar()
        if self.status_bar is None:
            print("状态栏未正确初始化")
            return
        self.update_source_indicator()
        self.status_bar.showMessage("就绪")

        # 创建中心部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 创建分割器（左侧目录树，右侧文件详情）
        splitter = QSplitter()
        main_layout.addWidget(splitter)

        # 左侧：目录树
        self.tree_widget = QTreeWidget()
        self.tree_widget.setHeaderLabels(["名称", "类型", "大小"])
        self.tree_widget.setColumnWidth(0, 300)
        self.tree_widget.itemSelectionChanged.connect(self.on_item_selected)
        splitter.addWidget(self.tree_widget)

        # 右侧：文件详情区域
        file_details_widget = QWidget()
        file_details_layout = QVBoxLayout(file_details_widget)

        # 文件信息区域
        file_info_group = QWidget()
        file_info_layout = QVBoxLayout(file_info_group)
        file_info_layout.setContentsMargins(10, 10, 10, 10)

        self.file_name_label = QLabel("未选择文件")
        self.file_name_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))

        self.file_path_label = QLabel("")
        self.file_size_label = QLabel("")
        self.file_url_label = QLabel("")

        file_info_layout.addWidget(QLabel("文件信息:"))
        file_info_layout.addWidget(self.file_name_label)
        file_info_layout.addWidget(self.file_path_label)
        file_info_layout.addWidget(self.file_size_label)
        file_info_layout.addWidget(self.file_url_label)
        file_info_layout.addStretch()

        # 下载按钮区域
        download_group = QWidget()
        download_layout = QVBoxLayout(download_group)

        self.download_button = QPushButton("下载文件")
        self.download_button.setIcon(QIcon.fromTheme("document-save"))
        self.download_button.clicked.connect(self.download_selected_file)
        self.download_button.setEnabled(False)

        download_layout.addWidget(QLabel("操作:"))
        download_layout.addWidget(self.download_button)
        download_layout.addStretch()

        # 添加到右侧布局
        file_details_layout.addWidget(file_info_group)
        file_details_layout.addWidget(download_group)

        splitter.addWidget(file_details_widget)

        # 设置分割器初始比例
        splitter.setSizes([400, 300])

        # 应用动态样式
        self.apply_dynamic_styles()

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.current_source = config.get("source", "github")
        except Exception as e:
            print(f"加载配置失败: {e}")

    def save_config(self):
        """保存配置文件"""
        try:
            config = {"source": self.current_source}
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def apply_dynamic_styles(self):
        """应用动态样式到控件"""
        # 设置树形控件样式
        if is_dark_mode():
            self.tree_widget.setStyleSheet("""
                QTreeWidget {
                    background-color: #252525;
                    color: #E0E0E0;
                    border: 1px solid #444444;
                }
                QTreeWidget::item {
                    color: #E0E0E0;
                }
                QTreeWidget::item:selected {
                    background-color: #4CAF50;
                    color: white;
                }
                QHeaderView::section {
                    background-color: #333333;
                    color: #E0E0E0;
                    border: 1px solid #444444;
                }
            """)
        else:
            self.tree_widget.setStyleSheet("""
                QTreeWidget {
                    background-color: white;
                    color: black;
                    border: 1px solid #cccccc;
                }
                QTreeWidget::item:selected {
                    background-color: #4CAF50;
                    color: white;
                }
            """)

        # 设置按钮样式
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)

    def create_menubar(self):
        menubar = self.menuBar()
        if menubar is None:
            print("菜单栏未正确初始化")
            return
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        if file_menu is None:
            print("文件菜单未正确创建")
            return

        # 更新动作
        update_action = QAction("更新目录结构", self)
        update_action.setShortcut("Ctrl+U")
        update_action.triggered.connect(self.download_directory_structure)
        file_menu.addAction(update_action)

        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 设置菜单
        settings_menu = menubar.addMenu("设置")
        if settings_menu is None:
            print("设置菜单未正确创建")
            return
        
        # GitHub源
        github_action = QAction("使用 GitHub 源", self)
        github_action.setCheckable(True)
        github_action.setChecked(self.current_source == "github")
        github_action.triggered.connect(lambda: self.set_source("github"))
        settings_menu.addAction(github_action)

        # Gitee源
        gitee_action = QAction("使用 Gitee 源", self)
        gitee_action.setCheckable(True)
        gitee_action.setChecked(self.current_source == "gitee")
        gitee_action.triggered.connect(lambda: self.set_source("gitee"))
        settings_menu.addAction(gitee_action)

        # 创建动作组确保单选
        source_group = QActionGroup(self)
        source_group.addAction(github_action)
        source_group.addAction(gitee_action)

        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        if help_menu is None:
            print("帮助菜单未正确创建")
            return
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def update_source_indicator(self):
        if self.status_bar is None:
            return
        """更新状态栏的源指示器"""
        source_text = f"当前源: {'GitHub' if self.current_source == 'github' else 'Gitee'}"
        if hasattr(self, 'source_label'):
            self.source_label.setText(source_text)
        else:
            self.source_label = QLabel(source_text)
            self.status_bar.addPermanentWidget(self.source_label)

    def set_source(self, source):
        if self.status_bar is None:
            return
        """设置下载源"""
        if source in ["github", "gitee"] and source != self.current_source:
            self.current_source = source
            self.save_config()
            # 更新状态栏显示
            self.status_bar.showMessage(f"已切换到 {'GitHub' if source == 'github' else 'Gitee'} 源")
            # 更新右下角标签
            self.update_source_indicator()
            # 自动重新加载目录结构
            self.download_directory_structure()

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于期末无挂",
                          "用于下载 JNU-EXAM 考试资料\n\n"
                          "版本: 1.0\n"
                          "作者: 顾白\n"
                          "qq: 470014599\n"
                          "期末无挂qq群：757343447\n"
                          "GitHub: https://github.com/gubaiovo/JNU-EXAM-Downloader\n"
                          "程序遵循 MIT 协议，完全开源")

    def download_directory_structure(self):
        if self.status_bar is None:
            return
        """下载目录结构JSON"""
        if self.current_source == "github":
            url = "https://raw.githubusercontent.com/gubaiovo/JNU-EXAM/main/directory_structure.json"
        else:
            url = "https://gitee.com/gubaiovo/jnu-exam/raw/main/directory_structure.json"

        self.status_bar.showMessage(
            f"正在从 {'GitHub' if self.current_source == 'github' else 'Gitee'} 下载目录结构...")

        # 显示下载对话框
        self.download_dialog.set_download_info(
            f"正在更新目录结构 ({'GitHub' if self.current_source == 'github' else 'Gitee'})",
            "directory_structure.json"
        )
        self.download_dialog.show_at_bottom_right(self)

        # 发送网络请求
        request = QNetworkRequest(QUrl(url))
        self.json_reply = self.network_manager.get(request)
        if self.json_reply is None:
            return
        # 连接信号
        self.json_reply.downloadProgress.connect(self.update_json_download_progress)
        self.json_reply.finished.connect(self.json_download_finished)

    def update_json_download_progress(self, bytes_received, bytes_total):
        """更新JSON下载进度"""
        if bytes_total > 0:
            percent = int((bytes_received / bytes_total) * 100)
            self.download_dialog.update_progress(percent)

    def json_download_finished(self):
        if self.json_reply is None:
            return
        if self.status_bar is None:
            return
        """JSON下载完成处理"""
        # 检查错误
        error = self.json_reply.error()
        if error == QNetworkReply.NetworkError.NoError:
            # 读取数据
            data = self.json_reply.readAll()
            self.status_bar.showMessage(
                f"目录结构更新成功! (源: {'GitHub' if self.current_source == 'github' else 'Gitee'})")
            try:
                # 解析JSON
                self.directory_data = json.loads(data.data().decode('utf-8'))
                self.status_bar.showMessage("目录结构更新成功!")

                # 处理JSON数据
                self.process_directory_data()

            except json.JSONDecodeError as e:
                self.status_bar.showMessage(f"JSON解析错误: {str(e)}")
                QMessageBox.critical(self, "错误", f"无法解析目录结构: {str(e)}")
        else:
            error_msg = self.json_reply.errorString()
            self.status_bar.showMessage(f"下载失败: {error_msg}")
            QMessageBox.critical(self, "下载失败", f"无法下载目录结构: {error_msg}")

        # 清理资源
        self.json_reply.deleteLater()

        # 启动淡出动画
        self.download_dialog.fade_out()

    def process_directory_data(self):
        """处理目录数据并填充树形视图（根据路径重建层级）"""
        self.tree_widget.clear()

        if not self.directory_data:
            return

        # 添加根节点
        root_item = QTreeWidgetItem(self.tree_widget, ["期末无挂", "目录", ""])
        root_item.setExpanded(True)

        # 创建路径到树节点的映射
        path_to_node = {"": root_item}  # 根路径映射到根节点

        # 添加目录（按路径长度排序确保父目录先创建）
        if 'dirs' in self.directory_data:
            # 按路径深度排序（父目录在前）
            sorted_dirs = sorted(self.directory_data['dirs'], key=lambda d: d['path'].count('/'))

            for dir_info in sorted_dirs:
                path = dir_info['path']
                parent_path = os.path.dirname(path)

                # 确保父节点存在
                if parent_path not in path_to_node:
                    # 创建缺失的父目录
                    parts = parent_path.split('/')
                    current_path = ""
                    parent_node = root_item

                    for part in parts:
                        if part:  # 跳过空部分
                            current_path = os.path.join(current_path, part) if current_path else part
                            if current_path not in path_to_node:
                                # 创建中间目录节点
                                node = QTreeWidgetItem(parent_node, [part, "目录", ""])
                                node.setExpanded(False)
                                path_to_node[current_path] = node
                            parent_node = path_to_node[current_path]

                # 获取父节点
                parent_node = path_to_node.get(parent_path, root_item)

                # 创建当前目录节点
                dir_name = os.path.basename(path)
                dir_item = QTreeWidgetItem(parent_node, [dir_name, "目录", ""])
                path_to_node[path] = dir_item
                dir_item.setExpanded(False)

                # 添加目录下的文件
                if 'files' in dir_info:
                    for file_info in dir_info['files']:
                        size_mb = file_info['size'] / (1024 * 1024)
                        size_text = f"{size_mb:.2f} MB" if size_mb >= 0.1 else f"{file_info['size']} bytes"
                        item = QTreeWidgetItem(dir_item, [file_info['name'], "文件", size_text])
                        item.setData(0, Qt.ItemDataRole.UserRole, file_info)

        # 添加根目录下的文件
        if 'files' in self.directory_data:
            for file_info in self.directory_data['files']:
                size_mb = file_info['size'] / (1024 * 1024)
                size_text = f"{size_mb:.2f} MB" if size_mb >= 0.1 else f"{file_info['size']} bytes"
                item = QTreeWidgetItem(root_item, [file_info['name'], "文件", size_text])
                item.setData(0, Qt.ItemDataRole.UserRole, file_info)

        # 展开第一级
        for i in range(root_item.childCount()):
            child_item = root_item.child(i)
            if child_item is not None:
                child_item.setExpanded(False)

    def add_directories(self, parent_item, dirs):
        """递归添加目录"""
        for dir_info in dirs:
            # 创建目录项
            dir_item = QTreeWidgetItem(parent_item, [dir_info['name'], "目录", ""])
            dir_item.setExpanded(False)

            # 添加目录下的文件
            if 'files' in dir_info:
                for file_info in dir_info['files']:
                    size_mb = file_info['size'] / (1024 * 1024)
                    size_text = f"{size_mb:.2f} MB" if size_mb >= 0.1 else f"{file_info['size']} bytes"
                    item = QTreeWidgetItem(dir_item, [file_info['name'], "文件", size_text])
                    item.setData(0, Qt.ItemDataRole.UserRole, file_info)

            # 递归添加子目录
            if 'dirs' in dir_info:
                self.add_directories(dir_item, dir_info['dirs'])

    def on_item_selected(self):
        """当树形视图中的项被选中时调用"""
        selected_items = self.tree_widget.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        file_info = item.data(0, Qt.ItemDataRole.UserRole)

        if not file_info or 'name' not in file_info:
            # 选中的是目录
            self.selected_file = None
            self.file_name_label.setText("未选择文件")
            self.file_path_label.setText("")
            self.file_size_label.setText("")
            self.file_url_label.setText("")
            self.download_button.setEnabled(False)
            return

        # 更新文件信息
        self.selected_file = file_info
        self.file_name_label.setText(f"名称: {file_info['name']}")
        self.file_path_label.setText(f"路径: {file_info['path']}")

        size_mb = file_info['size'] / (1024 * 1024)
        if size_mb >= 1:
            size_text = f"{size_mb:.2f} MB"
        else:
            size_kb = file_info['size'] / 1024
            size_text = f"{size_kb:.2f} KB" if size_kb >= 1 else f"{file_info['size']} bytes"

        self.file_size_label.setText(f"大小: {size_text}")
        self.file_url_label.setText(f"URL: {file_info['github_raw_url']}")
        self.download_button.setEnabled(True)

    def download_selected_file(self):
        """下载选中的文件"""
        if not self.selected_file:
            QMessageBox.warning(self, "警告", "请先选择一个文件")
            return

        # 获取文件信息
        if self.current_source == "github":
            url = self.selected_file['github_raw_url']
        else:
            url = self.selected_file['gitee_raw_url']

        filename = self.selected_file['name']

        # 选择保存位置
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存文件",
            os.path.join(os.path.expanduser("~"), "Downloads", filename),
            "All Files (*)"
        )

        if not save_path:
            return  # 用户取消了

        # 显示下载对话框
        self.download_dialog.set_download_info("正在下载文件", filename)
        self.download_dialog.show_at_bottom_right(self)

        # 发送网络请求
        request = QNetworkRequest(QUrl(url))
        self.file_reply = self.network_manager.get(request)
        if self.file_reply is None:
            return
        # 连接信号
        self.file_reply.downloadProgress.connect(self.update_file_download_progress)
        self.file_reply.finished.connect(lambda: self.file_download_finished(save_path))

    def update_file_download_progress(self, bytes_received, bytes_total):
        """更新文件下载进度"""
        if bytes_total > 0:
            percent = int((bytes_received / bytes_total) * 100)
            self.download_dialog.update_progress(percent)

    def file_download_finished(self, save_path):
        if self.file_reply is None:
            return
        if self.status_bar is None:
            return
        """文件下载完成处理"""
        # 检查错误
        error = self.file_reply.error()
        if error == QNetworkReply.NetworkError.NoError:
            # 读取数据
            data = self.file_reply.readAll()

            # 保存文件
            try:
                with open(save_path, 'wb') as f:
                    f.write(data.data())

                self.status_bar.showMessage(f"文件保存成功: {os.path.basename(save_path)}")
                QMessageBox.information(self, "下载完成", f"文件已保存到:\n{save_path}")

            except Exception as e:
                self.status_bar.showMessage(f"文件保存失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"无法保存文件: {str(e)}")
        else:
            error_msg = self.file_reply.errorString()
            self.status_bar.showMessage(f"下载失败: {error_msg}")
            QMessageBox.critical(self, "下载失败", f"无法下载文件: {error_msg}")

        # 清理资源
        self.file_reply.deleteLater()

        # 启动淡出动画
        self.download_dialog.fade_out()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion") 

    app.setStyleSheet(get_dynamic_stylesheet())

    window = MainWindow()
    window.showMaximized()

    QTimer.singleShot(1000, window.download_directory_structure)

    sys.exit(app.exec())