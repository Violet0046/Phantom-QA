# VisionQA Agent 👁️

VisionQA Agent 是一个极度隐蔽（幽灵模式）、极速响应的 AI 视觉解题与辅助工作流工具。
它潜伏在系统后台，通过全局快捷键无痕唤醒，截取屏幕内容并一键发送至大模型（支持多模态视觉大模型）进行分析解答，最后通过本地网页或手机推送展示结果。

## ✨ 核心特性

- 👻 **终极幽灵模式**：无控制台黑框，无系统托盘图标，彻底潜伏在后台运行。
- 🎯 **两点无痕狙击**：采用创新的“左键点击两点定位”法，支持右键一键取消，丝滑且精准。
- ⚡ **极速并发架构**：后端（FastAPI 大脑）与捕获端（Pynput 探子）多进程并发监控，主进程严格守护，绝不产生僵尸进程。
- 🌐 **本地战况看板**：内置精美的 Web Dashboard，实时支持 Markdown 渲染和代码高亮。

## ⚠️ 重要依赖说明（必看）

1. **🤖 AI 模型兼容性限制：**
   本项目的核心网络请求模块采用了标准的 **OpenAI API 格式**规范。因此，你配置的大模型服务**必须兼容 OpenAI 的接口标准**（例如：智谱 GLM-4v、阿里通义千问 Qwen-VL、GPT-4o 等视觉模型）。不支持采用私有 API 规范的模型（如原生 Gemini、文心一言原生接口等）。
   
2. **📱 手机推送限制：**
   目前的手机通知推送模块**仅支持 [PushDeer](https://www.pushdeer.com/)**。如果在配置文件中留空，系统将自动跳过推送步骤，你依然可以通过本地 Web 看板查看解答。

## 🚀 快速开始

### 1. 环境安装
确保你安装了 Python 3.10+，然后安装依赖库：

```bash
pip install fastapi uvicorn pydantic requests pynput keyboard pillow aiofiles
```

### 2. 首次运行与配置
直接运行主程序：

```bash
python main_launcher.py
```

初次运行时，程序会拦截启动，并在根目录下自动生成一份 `visionqa_config.json` 默认配置文件。请打开该 JSON 文件，填入你的配置信息：

```json
{
    "LLM_API_KEY": "你的真实大模型API_KEY",
    "LLM_API_URL": "兼容OpenAI格式的请求URL(如阿里云百炼)",
    "Multimodal_MODEL": "视觉模型名称(如 qwen-vl-plus)",
    "PUSHDEER_KEY": "你的PushDeer Key(可选)",
    "PUSHDEER_URL": "[https://api2.pushdeer.com/message/push](https://api2.pushdeer.com/message/push)"
}
```

配置完成后，再次运行 `python main_launcher.py` 即可成功启动后台服务。

## 🎮 操作指令 (全局快捷键)

程序启动并在后台就绪后，你可以随时在任何界面使用以下快捷键：

- **`Alt + A`** : 准备截图。此时鼠标移动到目标区域，**左键点击一次**确定左上角，**再点击一次**确定右下角。（点击**右键**可随时取消截图）。
- **`Alt + S`** : 确认发射。将截取的图片立刻发送给 AI 大脑进行处理。
- **`Alt + Q`** : 安全撤退。一键结束所有后台守护进程和端口占用，彻底清理痕迹。

## 📦 编译打包 (PyInstaller)

如果你想将其打包为独立的 `.exe` 发给朋友使用，请在项目根目录执行以下单行指令：

```bash
pyinstaller --name VisionQA_Agent --onedir --noconsole --hidden-import=uvicorn --hidden-import=fastapi --hidden-import=pydantic --hidden-import=keyboard --hidden-import=pynput main_launcher.py
```

打包完成后，将 `dist/VisionQA_Agent/` 文件夹（**记得删除里面的 `visionqa_config.json` 和 `server_images` 文件夹**）打包压缩分享即可。