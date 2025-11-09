

import textarena as ta 

agents = {
    0: ta.agents.OpenRouterAgent(model_name="minimax/minimax-m2:free"),
    1: ta.agents.OpenRouterAgent(model_name="alibaba/tongyi-deepresearch-30b-a3b:free"),
    2: ta.agents.OpenRouterAgent(model_name="meituan/longcat-flash-chat:free"),
    3: ta.agents.OpenRouterAgent(model_name="deepseek/deepseek-chat-v3.1:free"),
    4: ta.agents.OpenRouterAgent(model_name="openai/gpt-oss-20b:free"),
    5: ta.agents.OpenRouterAgent(model_name="z-ai/glm-4.5-air:free"),
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

