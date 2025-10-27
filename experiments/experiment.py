from dotenv import load_dotenv
load_dotenv()

import textarena as ta 
import elo.elo as e

def run_experiment(env_id, agents, num_games):
    for game_idx in range(num_games):
        print(f"Starting game {game_idx+1}...")
        env = ta.make(env_id=env_id)
        env.reset(num_players=len(agents))
        done = False 
        while not done:
            player_id, observation = env.get_observation() 
            action = agents[player_id](observation)
            done, step_info = env.step(action=action)
        rewards, game_info = env.close()
        e.update_elo(env_id, agents, rewards)