import os
import sys
import json
import logging
import ctypes

def get_base_path():
    """获取程序运行时的根目录，兼容 PyInstaller 打包环境"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE_DIR = get_base_path()
CONFIG_FILE = os.path.join(BASE_DIR, "visionqa_config.json")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

DEFAULT_CONFIG = {
    "LLM_API_KEY": "YOUR_API_KEY_HERE",
    "LLM_API_URL": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
    "Multimodal_MODEL": "glm-4.6v",
    "PUSHDEER_KEY": "YOUR_PUSHDEER_KEY_HERE",
    "PUSHDEER_URL": "https://api2.pushdeer.com/message/push",
}

class ConfigManager:
    def __init__(self):
        self.config_data = {}
        self.load_and_validate()

    def _show_alert(self, msg, title="VisionQA 配置错误", icon=0x10):
        """【新增】系统级弹窗方法 (0x10 是红叉报错，0x40 是蓝i提示)"""
        if getattr(sys, 'frozen', False) and sys.platform == "win32":
            ctypes.windll.user32.MessageBoxW(0, msg, title, icon)

    def load_and_validate(self):
        # 1. 检查文件是否存在
        if not os.path.exists(CONFIG_FILE):
            self._generate_template()
            msg = f"检测到初次运行或配置文件丢失！\n\n已为您在软件根目录生成了默认配置：\n{CONFIG_FILE}\n\n请用记事本打开该文件，填入您的真实 LLM_API_KEY，保存后重新启动本软件。"
            logging.critical(msg)
            self._show_alert(msg, "VisionQA 初始化", 0x40)  # 弹出友好提示
            sys.exit(1)

        # 2. 读取文件并捕获 JSON 语法错误
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                self.config_data = json.load(f)
        except json.JSONDecodeError as e:
            msg = f"配置文件 JSON 格式错误！请检查语法是否缺少逗号或双引号。\n\n详情: {e}"
            logging.critical(msg)
            self._show_alert(msg)  # 弹出红叉报错
            sys.exit(1)

        # 3. 校验必填项
        self._validate_keys()

    def _generate_template(self):
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)

    def _validate_keys(self):
        api_key = self.get("LLM_API_KEY")
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            msg = f"未配置 LLM_API_KEY！\n\n大模型无法工作。请打开配置文件填入真实的鉴权密钥，然后再重启本软件。"
            logging.critical(msg)
            self._show_alert(msg)  # 弹出红叉报错
            sys.exit(1)

        push_key = self.get("PUSHDEER_KEY")
        if not push_key or push_key == "YOUR_PUSHDEER_KEY_HERE":
            logging.warning("PUSHDEER_KEY 未配置，系统将跳过手机推送。")
            self.config_data["PUSHDEER_KEY"] = ""

    def get(self, key, default=None):
        return self.config_data.get(key, default)

config = ConfigManager()