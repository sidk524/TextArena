import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import textarena as ta 

K_FACTOR = 32

elo_ratings = {
  0: 1000,
  1: 1000,
  2: 1000,
  3: 1000,
  4: 1000,
  5: 1000,
}

def make_agents():
  return {
    0: ta.agents.OpenRouterAgent(model_name="anthropic/claude-sonnet-4"),
    1: ta.agents.OpenRouterAgent(model_name="openai/gpt-4.1"),
    2: ta.agents.OpenRouterAgent(model_name="google/gemini-2.5-flash"),
    3: ta.agents.OpenRouterAgent(model_name="openai/gpt-4"),
    4: ta.agents.OpenRouterAgent(model_name="meta-llama/llama-4-maverick:free"),
    5: ta.agents.OpenRouterAgent(model_name="anthropic/claude-haiku-4.5"),
  }

def update_elo(elo, rewards, game_info):
  for pid, reward in rewards.items():
    if pid not in elo:
      continue
    
    actual_score = 1.0 if reward > 0 else 0.0
    
    other_players = [other_pid for other_pid in rewards.keys() if other_pid != pid]
    if not other_players:
      continue
    
    avg_opponent_rating = sum(elo[other_pid] for other_pid in other_players) / len(other_players)
    expected_score = 1 / (1 + 10 ** ((avg_opponent_rating - elo[pid]) / 400))
    
    delta = K_FACTOR * (actual_score - expected_score)
    elo[pid] = elo[pid] + delta

print("Initial Elo ratings: ", elo_ratings)
for game_idx in range(5):
  agents = make_agents()
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
  update_elo(elo_ratings, rewards, game_info)
  print(f"Elo after Game {game_idx+1}: {elo_ratings}")

print(f"Final Elo Ratings: {elo_ratings}")