#Werewolf minimal script

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import textarena as ta 

agents = {
    0: ta.agents.OpenRouterAgent(model_name="anthropic/claude-sonnet-4"),
    1: ta.agents.OpenRouterAgent(model_name="openai/gpt-4.1"),
    2: ta.agents.OpenRouterAgent(model_name="google/gemini-2.5-flash"),
    3: ta.agents.OpenRouterAgent(model_name="openai/gpt-4.1"),
    4: ta.agents.OpenRouterAgent(model_name="openai/gpt-4.1"),
    5: ta.agents.OpenRouterAgent(model_name="anthropic/claude-haiku-4.5"),
}

# initialize the environment
env = ta.make(env_id="Werewolf-v0")
env.reset(num_players=len(agents))

# main game loop
done = False 
while not done:
  player_id, observation = env.get_observation()
  action = agents[player_id](observation)
  done, step_info = env.step(action=action)
rewards, game_info = env.close()

print(f"Game Info: {game_info}")

