import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import textarena as ta 
from elo.elo import initialize_elo, update_elo, get_elo

def make_agents():
  return {
    0: ta.agents.OpenRouterAgent(model_name="anthropic/claude-sonnet-4"),
    1: ta.agents.OpenRouterAgent(model_name="openai/gpt-4.1"),
    2: ta.agents.OpenRouterAgent(model_name="google/gemini-2.5-flash"),
    3: ta.agents.OpenRouterAgent(model_name="openai/gpt-4"),
    4: ta.agents.OpenRouterAgent(model_name="meta-llama/llama-4-maverick:free"),
    5: ta.agents.OpenRouterAgent(model_name="anthropic/claude-haiku-4.5"),
  }

agents = make_agents()
initialize_elo(list(agents.keys()))

print(f"Initial Elo ratings: {get_elo()}")

for game_idx in range(5):
  print(f"Starting game {game_idx+1}...")

  env = ta.make(env_id="Werewolf-v0")
  env.reset(num_players=len(agents))

  done = False 
  while not done:
    player_id, observation = env.get_observation()
    action = agents[player_id](observation)
    done, step_info = env.step(action=action)

  rewards, game_info = env.close()
  print(f"Game {game_idx+1} Rewards: {rewards}")
  
  # Update ELO - it now automatically loads from and saves to elo.json
  update_elo("Werewolf-v0", agents, rewards)
  print(f"Elo after Game {game_idx+1}: {get_elo()}")

print(f"Final Elo Ratings: {get_elo()}")

