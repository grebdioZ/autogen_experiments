import os, nest_asyncio
nest_asyncio.apply()
import asyncio
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.tools import TeamTool

def main():
    print("Hello from research-assistant!")
    model_client = OllamaChatCompletionClient(
        model="qwen3",
        parallel_tool_calls=False,
    )
    researcher   = AssistantAgent(name="Researcher", system_message="Gather and summarize factual info.", model_client=model_client)
    factchecker  = AssistantAgent(name="FactChecker", system_message="Verify facts and cite sources.",       model_client=model_client)
    critic       = AssistantAgent(name="Critic",    system_message="Critique clarity and logic.",         model_client=model_client)
    summarizer   = AssistantAgent(name="Summarizer",system_message="Condense into a brief executive summary.", model_client=model_client)
    editor       = AssistantAgent(name="Editor",    system_message="Do some language polishing and signal APPROVED when done.", model_client=model_client)
        
    max_msgs = MaxMessageTermination(max_messages=20)
    text_term = TextMentionTermination(text="APPROVED", sources=["Editor"])
    termination = max_msgs | text_term
    team = RoundRobinGroupChat(
        participants=[researcher, factchecker, critic, summarizer, editor],
        termination_condition=termination
    )

    deepdive_tool = TeamTool(team=team, name="DeepDive", description="Collaborative multi-agent deep dive")    

    host = AssistantAgent(
        name="Host",
        model_client=model_client,
        tools=[deepdive_tool],
        system_message="You have access to a DeepDive tool for in-depth research.",
    )

    async def run_deepdive(topic: str):
        result = await host.run(task=f"Deep dive on: {topic}")
        print("🔍 DeepDive result:\n", result)
        await model_client.close()

    topic = "Impacts of Model Context Protocol on Agentic AI"
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_deepdive(topic))    

if __name__ == "__main__":
    main()
