import re
import requests
import json
import logging
from backend.core.config import config


class SupervisorAgent:
    """
    智能管家 Agent (Router & Fast Solver)
    职责：分析截图。如果是选择题/简单题，直接给出极简答案；如果是复杂算法题，交给专家。
    """

    def __init__(self):
        self.api_key = config.get("LLM_API_KEY")
        self.api_url = config.get("LLM_API_URL")
        # 使用极速模型做判断和简单题直答
        self.model = "glm-4.6v"

    def analyze_intent(self, base64_images: list) -> dict:
        """
        return: 包含 task_type 和 answer 的字典
        """
        # 核心：融合任务路由、题目摘要与极简作答的引擎规则
        prompt = """
                你是一个专精于计算机科学与软件工程领域的极简解题引擎与任务路由管家。
                请精准阅读截图中的技术类题目，严格输出一个 JSON 对象，不要包含任何 markdown 标记（JSON外部不要有```json等标记）。

                【输出格式严格要求】
                {
                    "task_type": "CHOICE" 或 "ALGORITHM",
                    "question_snippet": "提取题干最核心的前10个字，用于标识题目",
                    "answer": "具体的解答内容"
                }

                【answer 字段作答规则】
                1. 任务类型为 "CHOICE"（选择题，包含单选、多选或不定项）：
                   - 仅限字母或序号：直接输出正确选项的字母（如 "C" 或 "ACD"），若无标号则输出序号（如 "第2个选项"）。
                   - 绝对静默：不要任何解释，严格只输出最终结果。

                2. 任务类型为 "ALGORITHM"（算法大题/代码实现）：
                   - 请直接给出完整且最优的代码实现。
                   - 请优先使用 Java 语言编写核心逻辑。
                   - 必须使用 Markdown 格式排版：先用两句话写「解题思路」，然后紧跟 Markdown 代码块（```java ... ```）。不要多余废话。
                """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # 组装多模态消息体
        content_list = [{"type": "text", "text": prompt}]
        for img in base64_images:
            content_list.append({
                "type": "image_url",
                "image_url": {"url": img}
            })

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": content_list}],
            "temperature": 0.1  # 保持极低温度，确保 JSON 格式稳定和选择题不出幻觉
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()

            result_text = response.json()["choices"][0]["message"]["content"]
            match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if match:
                result_text = match.group(0)
            else:
                logging.warning("[管家 Agent] 未检测到标准的 JSON 结构，尝试直接解析。")

            intent_data = json.loads(result_text)

            return intent_data

        except Exception as e:
            logging.error(f"[管家 Agent] 处理异常: {e}")
            return {"task_type": "GENERAL", "answer": f"处理异常: {e}"}

# 实例化单例
supervisor = SupervisorAgent()