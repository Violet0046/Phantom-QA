from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import logging
import uuid
import os
import time
import base64
import sys

from backend.services.push_deer import push_to_phone
from backend.agents.supervisor import supervisor


app = FastAPI(title="VisionQA Concurrent Gateway")

# 定义兼容 PyInstaller 打包的路径获取函数
def get_gateway_base_path():
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 exe，返回 exe 所在的目录
        return os.path.dirname(sys.executable)
    else:
        # 如果是未打包的 .py 源码，返回项目根目录
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 使用新函数来定位和创建图片存放目录
BASE_DIR = get_gateway_base_path()
SERVER_IMG_DIR = os.path.join(BASE_DIR, "server_images")
os.makedirs(SERVER_IMG_DIR, exist_ok=True)

# 挂载静态目录，方便前端网页直接通过 URL 访问图片
app.mount("/images", StaticFiles(directory=SERVER_IMG_DIR), name="images")

# 内存数据库，记录所有的任务状态供网页端读取
TASK_STORE = []


class ImageBatch(BaseModel):
    images_base64: list[str]


def process_task_in_background(images: list[str], task_id: str):
    """后台核心逻辑：存图 -> 占位 -> 调AI -> 更新结果 -> 推送"""
    try:
        # 1. 异步将内存图片持久化到服务器磁盘，供网页端展示
        image_urls = []
        for idx, img_b64 in enumerate(images):
            if img_b64.startswith("data:image"):
                img_b64 = img_b64.split(",", 1)[1]
            img_data = base64.b64decode(img_b64)
            filename = f"{task_id}_{idx}.png"
            filepath = os.path.join(SERVER_IMG_DIR, filename)
            with open(filepath, "wb") as f:
                f.write(img_data)
            image_urls.append(f"/images/{filename}")

        # 2. 在看板中注册任务占位符 (插在列表最前面，保证最新任务在最上)
        task_record = {
            "task_id": task_id,
            "timestamp": time.strftime("%H:%M:%S"),
            "status": "processing",  # 思考中状态
            "image_urls": image_urls,
            "snippet": "正在呼叫 AI 提取题干...",
            "answer": "处理中 ⏳"
        }
        TASK_STORE.insert(0, task_record)

        # 3. 呼叫大模型
        intent = supervisor.analyze_intent(images)
        snippet = intent.get("question_snippet", "提取失败")
        fast_answer = intent.get("answer")

        # 【修改这里】无论是选择题还是算法题，只要有答案就直接采用
        final_answer = fast_answer if fast_answer else "未能获取答案"

        # 4. 更新看板数据
        task_record["status"] = "done"
        task_record["snippet"] = snippet
        task_record["answer"] = final_answer

        # 5. 推送手机（去掉包裹 final_answer 的星号，让 Markdown 代码块自然渲染）
        push_content = f"**【题目】{snippet}...**\n\n---\n{final_answer}"
        push_to_phone(f"解答完毕 ({task_id[:4]})", push_content)

    except Exception as e:
        logging.error(f"[后台任务 {task_id}] 异常: {e}")
        # 如果出错，也要在看板里体现出来
        for task in TASK_STORE:
            if task["task_id"] == task_id:
                task["status"] = "error"
                task["answer"] = f"异常: {e}"


@app.post("/upload_batch")
async def receive_screenshot_batch(data: ImageBatch, background_tasks: BackgroundTasks):
    images = data.images_base64
    if not images:
        return {"status": "error", "message": "没有收到图片"}

    task_id = str(uuid.uuid4())[:8]
    push_to_phone(f"任务入列 ({task_id[:4]})", "已接收图片，正在解析中...")

    # 毫无阻力，直接甩给后台线程
    background_tasks.add_task(process_task_in_background, images, task_id)

    return {"status": "success", "task_id": task_id}


# =================前端展示层接口=================

@app.get("/api/tasks")
async def get_tasks_api():
    """提供给网页端轮询的 API"""
    return TASK_STORE


@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    """返回支持 Markdown 渲染的控制台网页 (左右分栏布局)"""
    html_content = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>VisionQA</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.0/marked.min.js"></script>
        <style>
            .no-scrollbar::-webkit-scrollbar { display: none; }
            .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

            /* 美化滚动条 */
            ::-webkit-scrollbar { width: 6px; height: 6px; }
            ::-webkit-scrollbar-track { background: #1f2937; border-radius: 4px; }
            ::-webkit-scrollbar-thumb { background: #4b5563; border-radius: 4px; }
            ::-webkit-scrollbar-thumb:hover { background: #6b7280; }

            .md-content pre { 
                background-color: #1e293b; 
                padding: 1rem; 
                border-radius: 0.5rem; 
                margin: 1rem 0; 
                border: 1px solid #334155; 
                white-space: pre-wrap;     /* 强制代码自动换行，避免横向滚动 */
                word-wrap: break-word;
            }
            .md-content code { font-family: ui-monospace, SFMono-Regular, Consolas, monospace; color: #a78bfa; font-size: 0.95rem; line-height: 1.6; }
            .md-content p { margin-bottom: 0.75rem; line-height: 1.6; }
            .md-content blockquote { border-left: 4px solid #4b5563; padding-left: 1rem; color: #9ca3af; }

            /* 侧边栏选中高亮效果 */
            .task-card.active { border-color: #3b82f6; background-color: #1e293b; box-shadow: 0 0 10px rgba(59, 130, 246, 0.3); }
        </style>
    </head>
    <body class="bg-gray-900 text-gray-200 font-sans h-screen flex flex-col overflow-hidden">

        <header class="h-16 flex justify-between items-center px-6 bg-gray-800 border-b border-gray-700 flex-shrink-0">
            <h1 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-green-400 to-blue-500">
                VisionQA Live Room
            </h1>
            <div class="flex items-center gap-3">
                <span class="text-xs text-gray-400 bg-gray-700 px-3 py-1 rounded-full">Device: pc-001</span>
                <span class="text-xs text-green-400 animate-pulse flex items-center gap-1">
                    <span class="block w-2 h-2 bg-green-400 rounded-full"></span> Live connected
                </span>
            </div>
        </header>

        <div class="flex-grow flex overflow-hidden p-4 gap-4">

            <main class="flex-grow bg-gray-800 rounded-xl border border-gray-700 flex flex-col overflow-hidden shadow-lg w-2/3">
                <div class="p-4 border-b border-gray-700 bg-gray-800/50 flex justify-between items-center flex-shrink-0">
                    <h2 class="text-lg font-bold text-gray-300">详细分析 (Main View)</h2>
                    <span id="main-status-badge" class="text-xs font-bold px-2 py-1 rounded bg-gray-700 text-gray-400">WAITING</span>
                </div>
                <div id="main-view-content" class="flex-grow overflow-y-auto p-6">
                    <div class="text-center text-gray-500 mt-20">
                        <p class="text-xl mb-2">👈 请在右侧选择一个任务查看详情</p>
                        <p class="text-sm">支持实时自动更新结果，不打断代码阅读体验</p>
                    </div>
                </div>
            </main>

            <aside class="w-80 lg:w-96 bg-gray-800 rounded-xl border border-gray-700 flex flex-col flex-shrink-0 shadow-lg">
                <div class="p-4 border-b border-gray-700 bg-gray-800/50 flex-shrink-0">
                    <h2 class="text-lg font-bold text-gray-300">Recent Tasks</h2>
                </div>
                <div id="sidebar-tasks" class="flex-grow overflow-y-auto p-3 space-y-3">
                    </div>
            </aside>

        </div>

        <script>
            let globalTasks = [];
            let activeTaskId = null;
            let mainViewTaskStatus = null; // 用于记录当前主展示区任务的状态，避免不必要的重绘

            async function fetchTasks() {
                try {
                    const res = await fetch('/api/tasks');
                    if (!res.ok) throw new Error("网络请求失败");
                    globalTasks = await res.json();

                    renderSidebar();
                    autoSelectTaskIfNeeded();
                    updateMainViewIfNeeded();

                } catch (error) {
                    console.error("获取数据失败:", error);
                }
            }

            // 渲染右侧列表
            function renderSidebar() {
                const container = document.getElementById('sidebar-tasks');
                // 记忆滚动条位置
                const scrollPos = container.scrollTop;

                let htmlStr = '';
                // 截取最近10条（视你的后端 TASK_STORE 长度而定，也可以全量展示）
                const displayTasks = globalTasks.slice(0, 15); 

                displayTasks.forEach(task => {
                    const isProcessing = task.status === 'processing';
                    const isError = task.status === 'error';

                    // 状态灯颜色
                    let dotColor = 'bg-green-500';
                    if (isProcessing) dotColor = 'bg-yellow-500 animate-pulse';
                    if (isError) dotColor = 'bg-red-500';

                    const isActive = task.task_id === activeTaskId ? 'active' : 'border-gray-700 hover:border-gray-500';

                    // 提取第一张图作为缩略图
                    const thumbImg = task.image_urls.length > 0 ? 
                        `<img src="${task.image_urls[0]}" class="h-12 w-20 object-cover rounded border border-gray-600">` : 
                        `<div class="h-12 w-20 bg-gray-700 rounded border border-gray-600 flex items-center justify-center text-xs text-gray-500">No Img</div>`;

                    htmlStr += `
                    <div onclick="selectTask('${task.task_id}')" class="task-card cursor-pointer bg-gray-800/80 rounded-lg p-3 border transition-all duration-200 flex gap-3 ${isActive}">
                        ${thumbImg}
                        <div class="flex-grow overflow-hidden flex flex-col justify-center">
                            <div class="flex justify-between items-center mb-1">
                                <span class="text-xs font-mono text-gray-400">#${task.task_id.substring(0,4)}</span>
                                <span class="text-xs text-gray-500">${task.timestamp}</span>
                            </div>
                            <h4 class="text-sm font-bold text-gray-200 truncate">${task.snippet}</h4>
                            <div class="flex items-center gap-1 mt-1">
                                <span class="block w-2 h-2 ${dotColor} rounded-full"></span>
                                <span class="text-xs text-gray-400 capitalize">${task.status}</span>
                            </div>
                        </div>
                    </div>
                    `;
                });

                container.innerHTML = htmlStr;
                // 恢复滚动条位置
                container.scrollTop = scrollPos;
            }

            // 首次加载或没有选中时，自动选择最新的已完成任务
            function autoSelectTaskIfNeeded() {
                if (activeTaskId === null && globalTasks.length > 0) {
                    // 优先找最新 done 的，找不到就找第一个
                    const targetTask = globalTasks.find(t => t.status === 'done') || globalTasks[0];
                    if (targetTask) {
                        selectTask(targetTask.task_id);
                    }
                }
            }

            // 如果当前选中的任务正在处理且后台状态变成了 done，则安静地更新主视图
            function updateMainViewIfNeeded() {
                if (!activeTaskId) return;
                const currentTask = globalTasks.find(t => t.task_id === activeTaskId);
                if (currentTask && currentTask.status !== mainViewTaskStatus) {
                    renderMainView(currentTask);
                }
            }

            // 点击侧边栏，手动切换任务
            function selectTask(taskId) {
                activeTaskId = taskId;
                const task = globalTasks.find(t => t.task_id === taskId);
                if (task) {
                    renderMainView(task);
                    renderSidebar(); // 重新渲染侧边栏以更新高亮框
                }
            }

            // 渲染左侧主展示区
            function renderMainView(task) {
                mainViewTaskStatus = task.status; // 记录状态
                const container = document.getElementById('main-view-content');
                const badge = document.getElementById('main-status-badge');

                // 更新顶部 Badge
                let badgeClass = 'bg-green-500/20 text-green-400 border border-green-500/50';
                if (task.status === 'processing') badgeClass = 'bg-yellow-500/20 text-yellow-400 border border-yellow-500/50 animate-pulse';
                if (task.status === 'error') badgeClass = 'bg-red-500/20 text-red-400 border border-red-500/50';
                badge.className = `text-xs font-bold px-3 py-1 rounded-full ${badgeClass}`;
                badge.innerText = task.status.toUpperCase();

                // 解析 Markdown
                const safeAnswer = task.answer ? String(task.answer) : "暂无内容";
                const parsedAnswer = marked.parse(safeAnswer);

                // 图片区域 (放在题干下方)
                let imgTags = task.image_urls.map(url => `<img src="${url}" class="max-h-64 object-contain rounded border border-gray-600 hover:scale-105 transition duration-300">`).join('');
                let imageContainer = imgTags ? `<div class="flex gap-4 mb-6 overflow-x-auto pb-2 no-scrollbar">${imgTags}</div>` : '';

                container.innerHTML = `
                    <div class="mb-6 border-b border-gray-700 pb-4">
                        <div class="flex items-center gap-3 mb-3">
                            <span class="bg-gray-700 text-gray-300 px-2 py-1 rounded text-sm font-mono">ID: ${task.task_id}</span>
                            <span class="text-gray-500 text-sm">提交时间: ${task.timestamp}</span>
                        </div>
                        <h1 class="text-2xl font-bold text-white mb-4 leading-relaxed">${task.snippet}</h1>
                        ${imageContainer}
                    </div>

                    <div class="md-content text-gray-300 text-lg">
                        ${parsedAnswer}
                    </div>
                `;
            }

            // 启动定时器，每2秒悄悄在后台拉取一次数据
            setInterval(fetchTasks, 2000);
            fetchTasks(); // 立即执行一次
        </script>
    </body>
    </html>
    """
    return html_content

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)