import argparse
import os
import subprocess
import sys
import time
import ctypes

# ========== 【核心护盾】==========
# 防止 --no console 模式下找不到输出流而崩溃
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

# =================================

def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def run_backend(host: str, port: int) -> int:
    import uvicorn
    from backend.gateway import app
    uvicorn.run(app, host=host, port=port)
    return 0


def run_catcher() -> int:
    from local_catcher import main  # 确保这里是你 local_catcher.py 里的主函数名
    main()
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--mode", choices=["launcher", "backend", "catcher"], default="launcher")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args(argv)


def run_launcher() -> int:
    from backend.core.config import config
    if _is_frozen():
        child_cmd_prefix = [sys.executable]
    else:
        this_script = os.path.abspath(__file__)
        child_cmd_prefix = [sys.executable, this_script]

    processes: list[subprocess.Popen] = []

    # 幽灵隐身术：不创建控制台窗口
    creation_flags = 0x08000000 if sys.platform == "win32" else 0

    try:
        # 1. 启动后端大脑 (静默)
        p_backend = subprocess.Popen([*child_cmd_prefix, "--mode", "backend"], creationflags=creation_flags)
        processes.append(p_backend)



        # 2. 启动前端捕获 (静默)
        p_frontend = subprocess.Popen([*child_cmd_prefix, "--mode", "catcher"], creationflags=creation_flags)
        processes.append(p_frontend)
        time.sleep(3)
        # 3. 运行时弹窗提示一次
        if p_backend.poll() is None and p_frontend.poll() is None:
            # 只有两个进程都健康活着，才提示成功
            if sys.platform == "win32":
                ctypes.windll.user32.MessageBoxW(
                    0,
                    "VisionQA 后台服务已成功启动。\n\n快捷键说明：\n[Alt + A] 准备截图 (左键点击两点框选，右键取消)\n[Alt + S] 发送截图\n[Alt + Q] 退出程序并清理后台",
                    "VisionQA 运行提示",
                    0x40
                )

        # 4. 幽灵主监控循环
        while True:
            # 如果任何一个子进程退出了（比如你在 catcher 里按了 Alt+Q 触发了 break 退出）
            if p_backend.poll() is not None or p_frontend.poll() is not None:
                break  # 打破循环，进入 finally 销毁所有进程
            time.sleep(1)

    except KeyboardInterrupt:
        pass
    finally:
        # 【核心清理逻辑】：无痕撤退
        for p in processes:
            try:
                p.terminate()
            except Exception:
                pass
        return 0


def main():
    args = parse_args(sys.argv[1:])
    if args.mode == "backend":
        return run_backend(host=args.host, port=args.port)
    elif args.mode == "catcher":
        return run_catcher()
    return run_launcher()


if __name__ == "__main__":
    sys.exit(main())