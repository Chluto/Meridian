from .utils.views import print_agent_output
from .utils.llms import call_model

class FactCheckerAgent:
    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}

    async def check_facts(self, research_state: dict):
        task = research_state.get("task")
        
        # 为事实核查组装草稿表示
        intro = research_state.get("introduction", "")
        conclusion = research_state.get("conclusion", "")
        data = research_state.get("research_data", [])
        
        draft = f"引言：\n{intro}\n\n章节数据：\n{data}\n\n结论：\n{conclusion}"

        prompt = [
            {
                "role": "system",
                "content": "你是一位严谨的事实核查专家。你的职责是基于提供的研究背景材料，审阅研究报告草稿，识别其中可能存在的事实性错误、虚构内容或不一致之处，并判断是否需要将其退回写作专家进行修订。",
            },
            {
                "role": "user",
                "content": f"请对以下草稿进行事实准确性审阅：\n\n{draft}\n\n如果你发现关键性错误，请列出错误清单，以便写作专家据此修订草稿。如果草稿事实无误、可以接受，请务必只返回字符串 'None'，不要返回任何其他文本。"
            }
        ]

        response = await call_model(prompt, model=task.get("model"))
        return response

    async def run(self, research_state: dict):
        if self.websocket and self.stream_output:
            await self.stream_output(
                "logs",
                "fact_checking",
                f"正在核查组装草稿中的事实准确性...",
                self.websocket,
            )
        else:
            print_agent_output(f"正在核查组装草稿中的事实准确性...", agent="FACT_CHECKER")

        review = await self.check_facts(research_state)

        from .utils.none_sentinels import is_none_accept_response

        if is_none_accept_response(review):
            review = None
            if self.websocket and self.stream_output:
                await self.stream_output("logs", "fact_checking", "事实核查通过，草稿已被接受。", self.websocket)
            else:
                print_agent_output("事实核查通过，草稿已被接受。", agent="FACT_CHECKER")
        else:
            if self.websocket and self.stream_output:
                await self.stream_output("logs", "fact_checking", f"事实核查发现问题：{review}...", self.websocket)
            else:
                print_agent_output(f"事实核查发现问题：{review}...", agent="FACT_CHECKER")

        out = {"fact_check_notes": review}
        if review is not None:
            out["fact_check_revision_count"] = research_state.get(
                "fact_check_revision_count", 0
            ) + 1
        return out
