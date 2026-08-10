from datetime import datetime
import json5 as json
from .utils.views import print_agent_output
from .utils.llms import call_model

sample_json = """
{
  "table_of_contents": 基于研究报告各章节标题与子标题生成的 Markdown 格式目录（使用 '-' 列表项）,
  "introduction": 对研究主题的深入介绍，使用 Markdown 语法并附相关来源的超链接引用,
  "conclusion": 基于全部研究数据对整个研究得出的结论，使用 Markdown 语法并附相关来源的超链接引用,
  "sources": 包含研究中使用的全部来源链接的字符串列表，使用 Markdown 语法与 APA 引用格式。例如：['- 标题, 年份, 作者 [来源链接](source)', ...]
}
"""


class WriterAgent:
    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers

    def get_headers(self, research_state: dict):
        return {
            "title": research_state.get("title"),
            "date": "日期",
            "introduction": "引言",
            "table_of_contents": "目录",
            "conclusion": "结论",
            "references": "参考文献",
        }

    async def write_sections(self, research_state: dict):
        query = research_state.get("title")
        data = research_state.get("research_data")
        task = research_state.get("task")
        follow_guidelines = task.get("follow_guidelines")
        guidelines = task.get("guidelines")

        fact_notes = research_state.get('fact_check_notes')
        fact_notes_str = f"事实核查意见：{fact_notes}。你必须修订引言和结论以解决上述问题。\n" if fact_notes else ""

        prompt = [
            {
                "role": "system",
                "content": "你是一位行业研究写作专家。你的唯一职责是基于研究结果与调研信息，"
                "针对指定主题撰写一份高质量的中文行业研究报告。\n ",
            },
            {
                "role": "user",
                "content": f"今天是 {datetime.now().strftime('%Y年%m月%d日')}\n"
                f"研究主题：{query}\n"
                f"研究数据：{str(data)}\n"
                f"{fact_notes_str}"
                f"你的任务是基于提供的研究数据，为研究报告撰写深入、严谨、详尽的中文引言与结论。"
                f"输出结果中不要包含任何章节标题。\n"
                f"你必须在引言与结论中附上所有相关来源的 Markdown 超链接——"
                f"例如：'这是示例文本。([来源网址](url))'\n\n"
                f"{f'你必须遵循以下写作指南：{guidelines}' if follow_guidelines else ''}\n"
                f"你必须只返回一个 JSON（不要包含 json markdown 标记），格式如下：\n"
                f"{sample_json}\n\n",
            },
        ]

        response = await call_model(
            prompt,
            task.get("model"),
            response_format="json",
        )
        return response

    async def revise_headers(self, task: dict, headers: dict):
        prompt = [
            {
                "role": "system",
                "content": """你是一位行业研究写作专家。
你的唯一职责是根据给定的写作指南修订报告章节标题数据。""",
            },
            {
                "role": "user",
                "content": f"""你的任务是根据给定的写作指南修订给定的章节标题 JSON。
你必须遵循写作指南，但标题取值应为简单字符串，忽略所有 Markdown 语法。
你必须只返回一个与给定 headers 数据格式完全一致的 JSON。
写作指南：{task.get("guidelines")}\n
标题数据：{headers}\n
""",
            },
        ]

        response = await call_model(
            prompt,
            task.get("model"),
            response_format="json",
        )
        return {"headers": response}

    async def run(self, research_state: dict):
        if self.websocket and self.stream_output:
            await self.stream_output(
                "logs",
                "writing_report",
                f"正在基于研究数据撰写最终研究报告...",
                self.websocket,
            )
        else:
            print_agent_output(
                f"正在基于研究数据撰写最终研究报告...",
                agent="WRITER",
            )

        research_layout_content = await self.write_sections(research_state)

        if research_state.get("task").get("verbose"):
            if self.websocket and self.stream_output:
                research_layout_content_str = json.dumps(
                    research_layout_content, indent=2
                )
                await self.stream_output(
                    "logs",
                    "research_layout_content",
                    research_layout_content_str,
                    self.websocket,
                )
            else:
                print_agent_output(research_layout_content, agent="WRITER")

        headers = self.get_headers(research_state)
        if research_state.get("task").get("follow_guidelines"):
            if self.websocket and self.stream_output:
                await self.stream_output(
                    "logs",
                    "rewriting_layout",
                    "正在根据写作指南重写报告布局...",
                    self.websocket,
                )
            else:
                print_agent_output(
                    "正在根据写作指南重写报告布局...", agent="WRITER"
                )
            headers = await self.revise_headers(
                task=research_state.get("task"), headers=headers
            )
            headers = headers.get("headers")

        return {**research_layout_content, "headers": headers}
