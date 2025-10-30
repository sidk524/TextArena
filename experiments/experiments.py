import textarena as ta 
from concurrent.futures import ThreadPoolExecutor, as_completed
import textarena as ta
from dotenv import load_dotenv
load_dotenv()

def run_experiment(env_id, agents):
    print(f"Starting game...")
    env = ta.make(env_id=env_id)
    env.reset(num_players=len(agents))
    done = False 
    while not done:
        player_id, observation = env.get_observation() 
        action = agents[player_id](observation)
        done, step_info = env.step(action=action)
    rewards, game_info = env.close()
    return rewards, game_info

    
def run_experiments_in_parallel(env_id, agents, num_games):
    results = {}
    with ThreadPoolExecutor(max_workers=num_games) as executor:
        # Submit all games to run in parallel
        futures = {executor.submit(run_experiment, env_id, agents): game_idx 
                   for game_idx in range(num_games)}
        
        # Collect results as they complete
        completed = 0
        for future in as_completed(futures):
            game_idx = futures[future]
            try:
                rewards, game_info = future.result()
                results[game_idx] = {
                    "rewards": rewards,
                    "game_info": game_info
                }
                completed += 1
            except Exception as exc:
                results[game_idx] = {
                    "rewards": None,
                    "game_info": None,
                    "error": str(exc)
                }
                completed += 1
    
    successful = sum(1 for r in results.values() if "error" not in r)
    return results
