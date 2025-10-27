import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import textarena as ta
from experiment import run_experiment

agents = {
    0: ta.agents.OpenRouterAgent(model_name="anthropic/claude-sonnet-4"),
    1: ta.agents.OpenRouterAgent(model_name="openai/gpt-4.1"),
    2: ta.agents.OpenRouterAgent(model_name="google/gemini-2.5-flash"),
    3: ta.agents.OpenRouterAgent(model_name="openai/gpt-4"),
    4: ta.agents.OpenRouterAgent(model_name="meta-llama/llama-4-maverick:free"),
    5: ta.agents.OpenRouterAgent(model_name="anthropic/claude-haiku-4.5"),
  }

run_experiment(env_id="Werewolf-v0", agents=agents, num_games=1)