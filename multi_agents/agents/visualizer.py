from .utils.views import print_agent_output
from .utils.llms import call_model

class VisualizerAgent:
    def __init__(self, websocket=None, stream_output=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.headers = headers or {}

    async def generate_visualizations(self, research_state: dict):
        task = research_state.get("task")
        data = research_state.get("research_data", [])
        
        prompt = [
            {
                "role": "system",
                "content": "你是一位数据可视化专家。你的职责是从提供的研究数据中提取关键数据点、流程或时间线，并生成一幅相关的 Mermaid.js 图（如饼图、流程图或时间线图），使研究报告更易于阅读。",
            },
            {
                "role": "user",
                "content": f"研究数据：\n{data}\n\n请生成一个能够呈现该数据中最具代表性或结构性特征的 Mermaid 图块。请务必使用标准 markdown ```mermaid ... ``` 语法。如果完全没有适合绘制的数据，请务必只返回字符串 'None'。"
            }
        ]

        response = await call_model(prompt, model=task.get("model"))
        return response

    async def run(self, research_state: dict):
        if self.websocket and self.stream_output:
            await self.stream_output(
                "logs",
                "visualizing",
                f"正在为研究报告生成可视化图表...",
                self.websocket,
            )
        else:
            print_agent_output(f"正在为研究报告生成可视化图表...", agent="VISUALIZER")

        diagram_output = await self.generate_visualizations(research_state)

        diagrams = []
        if "None" not in diagram_output:
            diagrams.append(diagram_output)
            if self.websocket and self.stream_output:
                await self.stream_output("logs", "visualizing", f"可视化图表已生成。", self.websocket)
            else:
                print_agent_output(f"可视化图表已生成。", agent="VISUALIZER")
        else:
            if self.websocket and self.stream_output:
                await self.stream_output("logs", "visualizing", "没有适合生成可视化图表的数据。", self.websocket)
            else:
                print_agent_output("没有适合生成可视化图表的数据。", agent="VISUALIZER")

        return {"diagrams": diagrams}
