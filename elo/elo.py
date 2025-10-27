import json
import os
from typing import Dict, List

K_FACTOR = 32

# Get the directory where this file is located
ELO_DIR = os.path.dirname(os.path.abspath(__file__))
ELO_FILE = os.path.join(ELO_DIR, "elo.json")

def load_elo() -> Dict[int, float]:
    """Load ELO ratings from JSON file, or return default ratings."""
    if os.path.exists(ELO_FILE) and os.path.getsize(ELO_FILE) > 0:
        try:
            with open(ELO_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_elo(elo: Dict[int, float]):
    """Save ELO ratings to JSON file."""
    with open(ELO_FILE, "w") as f:
        json.dump(elo, f)

def update_elo(game_name: str, agents: Dict, rewards: Dict):
    """
    Update ELO ratings based on game results.
    ELO ratings are automatically loaded from and saved to elo.json.
    Args:
        game_name: The name of the game (e.g., "Werewolf-v0")
        agents: Dictionary of player_id -> agent object
        rewards: Dictionary of player_id -> reward value
    """
    elo_data = load_elo()
    
    # Get or create game-specific ELO dict
    if game_name not in elo_data:
        elo_data[game_name] = {}
    
    game_elo = elo_data[game_name]
    
    # Initialize ELO for each agent if it doesn't exist
    for pid, agent in agents.items():
        agent_id = agent.id
        if agent_id not in game_elo:
            game_elo[agent_id] = 1000.0
    
    # Update ELO for each agent
    for pid, reward in rewards.items():
        agent = agents[pid]
        agent_id = agent.id
        
        if agent_id not in game_elo:
            continue
        
        actual_score = 1.0 if reward > 0 else 0.0
        
        # Get other agents' IDs
        other_agent_ids = []
        for other_pid, other_agent in agents.items():
            if other_pid != pid:
                other_agent_id = other_agent.id
                if other_agent_id in game_elo:
                    other_agent_ids.append(other_agent_id)
        
        if not other_agent_ids:
            continue
        
        avg_opponent_rating = sum(game_elo[other_id] for other_id in other_agent_ids) / len(other_agent_ids)
        expected_score = 1 / (1 + 10 ** ((avg_opponent_rating - game_elo[agent_id]) / 400))
        delta = K_FACTOR * (actual_score - expected_score)
        game_elo[agent_id] = game_elo[agent_id] + delta
    
    elo_data[game_name] = game_elo
    save_elo(elo_data)


