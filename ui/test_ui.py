from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout
from qfluentwidgets import SubtitleLabel, LineEdit, PushButton, BodyLabel
from bridge.reply import Reply, ReplyType
from Channel.pinduoduo.utils.API.send_message import SendMessage

class TestUI(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName("TestUI")

        # 创建布局
        self.vBoxLayout = QVBoxLayout(self)
        
        # 创建标题
        self.title_label = SubtitleLabel("测试", self)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        
        # 创建提交按钮
        self.submit_button = PushButton("提交", self)
        self.submit_button.clicked.connect(self.on_submit_clicked)
        
        # 添加到布局
        self.vBoxLayout.addWidget(self.title_label)
        self.vBoxLayout.addWidget(self.submit_button)
        
        # 设置布局边距
        # self.vBoxLayout.setContentsMargins(30, 30, 30, 30)
    
    
    def on_submit_clicked(self):
        """提交按钮点击事件"""
        # fuck 594493095 170207412 9892976793329
        shop_id = "594493095"
        # 客服id
        user_id = "170207412"
        # 客户id
        from_uid = "9892976793329"
        sender = SendMessage(shop_id, user_id)
        sender.send_text(from_uid, "收到测试")
        
        # 这里可以添加你的处理逻辑
