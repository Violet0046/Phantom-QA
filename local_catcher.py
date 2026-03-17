import time
import keyboard
import logging
import requests
import base64
import io
from PIL import ImageGrab
from pynput import mouse

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

API_URL = "http://127.0.0.1:8000/upload_batch"

# 全局状态变量
is_armed = False
start_pos = None

# 【新增】使用内存列表代替本地文件夹，实现真正的无痕捕获
memory_buffer = []


def on_snip_hotkey():
    global is_armed
    if not is_armed:
        is_armed = True


def on_click(x, y, button, pressed):
    global is_armed, start_pos

    # 如果当前没有按下 Alt+A，直接忽略所有鼠标操作
    if not is_armed:
        return

    # 如果点错了，直接按下鼠标右键即可取消本次截图
    if button == mouse.Button.right and pressed:
        is_armed = False
        start_pos = None
        return

    # 过滤掉除了左键以外的其他按键
    if button != mouse.Button.left:
        return

    # 处理鼠标左键按下的逻辑
    if pressed:
        if start_pos is None:
            # 第一次点击：记录左上角坐标
            start_pos = (x, y)
        else:
            # 第二次点击：记录右下角坐标，并执行截图
            end_pos = (x, y)
            is_armed = False  # 无论成功与否，立刻解除武装

            # 计算两点构成的矩形区域
            x1, y1 = min(start_pos[0], end_pos[0]), min(start_pos[1], end_pos[1])
            x2, y2 = max(start_pos[0], end_pos[0]), max(start_pos[1], end_pos[1])

            # 如果宽和高都大于 100 像素，才认为是有效的框选
            if x2 - x1 > 100 and y2 - y1 > 100:
                capture_silent_snip(x1, y1, x2, y2)

            # 清空坐标，为下一次 Alt+A 做准备
            start_pos = None


def capture_silent_snip(x1, y1, x2, y2):
    try:
        img = ImageGrab.grab(bbox=(x1, y1, x2, y2))

        # 【核心改变】不存硬盘，直接转存到内存缓冲区
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        memory_buffer.append(f"data:image/png;base64,{img_base64}")
    except Exception as e:
        logging.error(f"截图提取失败: {e}")


def on_send_hotkey():
    if not memory_buffer:
        logging.warning("内存缓冲区为空，请先 Alt+A 截图！")
        return
    send_batch_to_bot()


def send_batch_to_bot():
    try:
        # 直接发送内存中的 base64 列表
        response = requests.post(API_URL, json={"images_base64": memory_buffer}, timeout=60)

        if response.status_code == 200:
            memory_buffer.clear()  # 发送成功后一键清空内存
        else:
            logging.error(f"发送失败，HTTP 状态码: {response.status_code}")
    except Exception as e:
        logging.error(f"网络请求异常: {e}")


def main():
    keyboard.add_hotkey('alt + a', on_snip_hotkey)
    keyboard.add_hotkey('alt + s', on_send_hotkey)
    mouse_listener = mouse.Listener(on_click=on_click)
    mouse_listener.start()

    while True:
        if keyboard.is_pressed('alt + q'):
            break
        time.sleep(0.1)

    mouse_listener.stop()


if __name__ == "__main__":
    main()