from datetime import datetime
import asyncio
from typing import Dict, List, Optional

from langgraph.graph import StateGraph, END

from .utils.views import print_agent_output
from .utils.llms import call_model
from ..memory.draft import DraftState
from . import ResearchAgent, ReviewerAgent, ReviserAgent


class EditorAgent:
    """负责规划并统筹管理研究报告编排工作的智能体。"""

    def __init__(self, websocket=None, stream_output=None, tone=None, headers=None):
        self.websocket = websocket
        self.stream_output = stream_output
        self.tone = tone
        self.headers = headers or {}

    async def plan_research(self, research_state: Dict[str, any]) -> Dict[str, any]:
        """
        基于初步调研与任务参数规划研究大纲。

        :param research_state: 包含研究状态信息的字典
        :return: 包含标题、日期与规划章节的字典
        """
        initial_research = research_state.get("initial_research")
        task = research_state.get("task")
        include_human_feedback = task.get("include_human_feedback")
        human_feedback = research_state.get("human_feedback")
        max_sections = task.get("max_sections")

        prompt = self._create_planning_prompt(
            initial_research, include_human_feedback, human_feedback, max_sections)

        print_agent_output(
            "正在基于初步调研规划报告大纲...", agent="EDITOR")
        plan = await call_model(
            prompt=prompt,
            model=task.get("model"),
            response_format="json",
        )

        return {
            "title": plan.get("title"),
            "date": plan.get("date"),
            "sections": plan.get("sections"),
        }

    async def run_parallel_research(self, research_state: Dict[str, any]) -> Dict[str, List[str]]:
        """
        针对每个章节执行并行研究任务。

        :param research_state: 包含研究状态信息的字典
        :return: 包含各章节研究结果的字典
        """
        agents = self._initialize_agents()
        workflow = self._create_workflow()
        chain = workflow.compile()

        queries = research_state.get("sections")
        title = research_state.get("title")

        self._log_parallel_research(queries)

        final_drafts = [
            chain.ainvoke(self._create_task_input(
                research_state, query, title), config={"tags": ["gpt-researcher"]})
            for query in queries
        ]
        research_results = [
            result["draft"] for result in await asyncio.gather(*final_drafts)
        ]

        return {"research_data": research_results}

    def _create_planning_prompt(self, initial_research: str, include_human_feedback: bool,
                                human_feedback: Optional[str], max_sections: int) -> List[Dict[str, str]]:
        """创建研究规划提示词。"""
        return [
            {
                "role": "system",
                "content": "你是一位资深行业研究主编。你的职责是统筹研究项目从启动到完成的全部环节，"
                           "主要任务是基于初步研究摘要规划报告的章节结构。\n ",
            },
            {
                "role": "user",
                "content": self._format_planning_instructions(initial_research, include_human_feedback,
                                                              human_feedback, max_sections),
            },
        ]

    def _format_planning_instructions(self, initial_research: str, include_human_feedback: bool,
                                      human_feedback: Optional[str], max_sections: int) -> str:
        """格式化研究规划指令。"""
        today = datetime.now().strftime('%Y年%m月%d日')
        feedback_instruction = (
            f"人工反馈：{human_feedback}。你必须根据该人工反馈调整章节规划。"
            if include_human_feedback and human_feedback and human_feedback != 'no'
            else ''
        )

        return f"""今天是 {today}
                   研究摘要报告：'{initial_research}'
                   {feedback_instruction}
                   \n你的任务是基于上述研究摘要报告，为研究项目生成一份章节标题大纲。
                   你最多必须生成 {max_sections} 个章节标题。
                   你只能聚焦与课题相关的子主题，并且不要包含引言、结论和参考文献等章节。
                   你必须只返回一个 JSON，包含字段 'title'（字符串）与
                   'sections'（最多 {max_sections} 个章节标题），结构如下：
                   '{{title: 研究报告标题字符串, date: 今天的日期, 
                   sections: ['章节标题 1', '章节标题 2', '章节标题 3' ...]}}'."""

    def _initialize_agents(self) -> Dict[str, any]:
        """初始化研究、审阅与修订智能体。"""
        return {
            "research": ResearchAgent(self.websocket, self.stream_output, self.tone, self.headers),
            "reviewer": ReviewerAgent(self.websocket, self.stream_output, self.headers),
            "reviser": ReviserAgent(self.websocket, self.stream_output, self.headers),
        }

    def _create_workflow(self) -> StateGraph:
        """创建研究流程工作流。"""
        agents = self._initialize_agents()
        workflow = StateGraph(DraftState)

        workflow.add_node("researcher", agents["research"].run_depth_research)
        workflow.add_node("reviewer", agents["reviewer"].run)
        workflow.add_node("reviser", agents["reviser"].run)

        workflow.set_entry_point("researcher")
        workflow.add_edge("researcher", "reviewer")
        workflow.add_edge("reviser", "reviewer")
        workflow.add_conditional_edges(
            "reviewer",
            self._route_draft_review,
            {"accept": END, "revise": "reviser"},
        )

        return workflow

    def _log_parallel_research(self, queries: List[str]) -> None:
        """记录并行研究任务的启动。"""
        if self.websocket and self.stream_output:
            asyncio.create_task(self.stream_output(
                "logs",
                "parallel_research",
                f"正在针对以下研究主题并行开展研究：{queries}",
                self.websocket,
            ))
        else:
            print_agent_output(
                f"正在并行开展以下研究任务：{queries}...",
                agent="EDITOR",
            )

    def _create_task_input(self, research_state: Dict[str, any], query: str, title: str) -> Dict[str, any]:
        """创建单个研究任务的输入。"""
        return {
            "task": research_state.get("task"),
            "topic": query,
            "title": title,
            "headers": self.headers,
        }
