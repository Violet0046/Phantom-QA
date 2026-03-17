import requests
import time
import logging

from backend.core.config import config

def push_to_phone(title: str, content: str) -> bool:
    """
    通用推送服务：将消息推送到手机
    :param title: 通知栏显示的短标题
    :param content: 点开后看到的 Markdown 长文本
    :return: bool 表示推送是否成功
    """
    # 动态从内存中获取配置
    push_key = config.get("PUSHDEER_KEY")
    # 如果配置里没有写 URL，给个默认的官方地址兜底
    push_url = "https://api2.pushdeer.com/message/push"

    # 安全检查：如果没有配 Key，优雅降级
    if not push_key or push_key == "YOUR_PUSHDEER_KEY_HERE":
        logging.warning(f"[推送服务] 暂未配置 PushDeer Key，跳过推送: {title}")
        return False

    # 统一的美化排版（加上时间戳，让通知更专业）
    formatted_content = (
        f"{content}\n\n"
        f"--- \n"
        f"⏳ *VisionQA Agent | {time.strftime('%H:%M:%S')}*"
    )

    params = {
        "pushkey": push_key,
        "text": title,
        "desp": formatted_content,
        "type": "markdown"
    }

    try:
        # 设置 timeout 防止网络卡死导致整个系统阻塞
        response = requests.get(push_url, params=params, timeout=10)

        if response.status_code == 200:
            return True
        else:
            logging.error(f"[推送服务] 发送失败，HTTP 状态码: {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        logging.error(f"[推送服务] 网络请求异常: {e}")
        return False