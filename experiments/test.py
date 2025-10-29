import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from experiment import run_experiments_in_parallel
import textarena as ta
from elo.elo import apply_elo_algorithm, check_elo_improvement, save_elo
from dotenv import load_dotenv
load_dotenv()

agents = {
    0: ta.agents.OpenRouterAgent(model_name="anthropic/claude-sonnet-4"),
    1: ta.agents.OpenRouterAgent(model_name="openai/gpt-4.1"),
    2: ta.agents.OpenRouterAgent(model_name="google/gemini-2.5-flash"),
    3: ta.agents.OpenRouterAgent(model_name="openai/gpt-4"),
    4: ta.agents.OpenRouterAgent(model_name="meta-llama/llama-4-maverick:free"),
    5: ta.agents.OpenRouterAgent(model_name="anthropic/claude-haiku-4.5"),
  }

def run_agent_modification_test(env_id, agents, testing_agent_index, num_games=2):
  if testing_agent_index not in agents:
    raise ValueError(f"testing_agent_index {testing_agent_index} not found in agents dict. Valid indices: {list(agents.keys())}")
  results = run_experiments_in_parallel(env_id, agents, num_games)
  testing_agent = agents[testing_agent_index]
  proposed_elo = apply_elo_algorithm(env_id, agents, results, testing_agent)
  if (check_elo_improvement(env_id, testing_agent, proposed_elo)):
    print("Elo improvement detected")
    response = input("Do you want to save the new ELO? (yes/no): ").strip().lower()
    if response in ['yes', 'y']:
      save_elo(proposed_elo)
      print("ELO saved successfully")
    else:
      print("ELO not saved")

def run_test(env_id, agents, num_games=2):
  results = run_experiments_in_parallel(env_id, agents, num_games)
  proposed_elo = apply_elo_algorithm(env_id, agents, results)
  save_elo(proposed_elo)

run_test("Werewolf-v0", agents, 5)