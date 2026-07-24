import os
from typing import Optional, List, Dict, Any
from emoji_skills import EmojiMakerSkill

LLM_API_KEY = os.environ.get("OPENAI_API_KEY", "")
LLM_BASE_URL = os.environ.get("OPENAI_BASE_URL", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-3.5-turbo")


def get_llm():
    if not LLM_API_KEY:
        return None
    try:
        from langchain_openai import ChatOpenAI
        kwargs = {
            "model": LLM_MODEL,
            "temperature": 0,
        }
        if LLM_BASE_URL:
            kwargs["base_url"] = LLM_BASE_URL
        if LLM_API_KEY:
            kwargs["api_key"] = LLM_API_KEY
        return ChatOpenAI(**kwargs)
    except Exception as e:
        print(f"初始化LLM失败：{e}")
        return None


def build_skill_tools() -> List[Any]:
    from emoji_skills import get_all_tools
    return get_all_tools()


def get_skill_instance() -> EmojiMakerSkill:
    return EmojiMakerSkill()


def _create_agent_legacy(llm, tools, verbose: bool):
    try:
        from langchain.agents import initialize_agent, AgentType
        return initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=verbose,
            handle_parsing_errors=True,
            max_iterations=10,
        )
    except Exception:
        return None


def _create_agent_new(llm, tools, verbose: bool):
    try:
        from langchain.agents import create_agent
        system_prompt = (
            "你是一个专业的表情包生成助手，你可以使用提供的工具来处理图片。"
            "当用户给出图片处理需求时，你需要一步步调用合适的工具完成任务，"
            "最终返回处理结果路径。请尽量按顺序组合工具完成全流程：抠图→尺寸适配→美化→加文字→生成动图→压缩。"
        )
        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
            debug=verbose,
        )
        return agent
    except Exception as e:
        print(f"新版create_agent创建失败：{e}")
        return None


def create_emoji_agent(verbose: bool = True):
    llm = get_llm()
    tools = build_skill_tools()
    if llm is None:
        return None
    agent = _create_agent_legacy(llm, tools, verbose)
    if agent is None:
        agent = _create_agent_new(llm, tools, verbose)
    if agent is None:
        print("⚠️ 两种智能体创建方式均失败，仅保留规则模式可用")
    return agent


def _run_agent_legacy(agent, prompt: str) -> str:
    try:
        if hasattr(agent, "run"):
            return agent.run(prompt)
        if hasattr(agent, "invoke"):
            res = agent.invoke(prompt)
            if isinstance(res, dict):
                return res.get("output", str(res))
            return str(res)
    except Exception as e:
        raise e
    return "执行完成"


def _run_agent_new(agent, prompt: str) -> str:
    try:
        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
        messages = result.get("messages", [])
        if messages:
            last = messages[-1]
            content = getattr(last, "content", str(last))
            if isinstance(content, list):
                return "\n".join(str(c) for c in content)
            return str(content)
        return str(result)
    except Exception as e:
        raise e


def process_with_agent(prompt: str, agent=None) -> str:
    if agent is None:
        agent = create_emoji_agent()
    if agent is not None:
        for runner in (_run_agent_legacy, _run_agent_new):
            try:
                return runner(agent, prompt)
            except Exception as _e:
                last_err = _e
                continue
        return f"智能体执行失败：{last_err}，已切换到规则模式"
    return "未配置LLM，仅支持规则模式调用"


def rule_based_process(img_path: str, platform: str = "wechat",
                       dynamic_type: str = "shake", text: Optional[str] = None,
                       **kwargs) -> str:
    skill = get_skill_instance()
    return skill.full_pipeline_emoji.invoke({
        "img_path": img_path,
        "platform": platform,
        "make_dynamic": dynamic_type,
        "add_text": text,
    })
