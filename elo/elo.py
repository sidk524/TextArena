import json
import os
import copy
from typing import Dict, List
from trueskill import Rating, rate

# TrueSkill default values 
DEFAULT_MU = 25.0  
DEFAULT_SIGMA = 25.0 / 3.0  

# Get the directory where this file is located
ELO_DIR = os.path.dirname(os.path.abspath(__file__))
ELO_FILE = os.path.join(ELO_DIR, "elo.json")

def load_elo() -> Dict:
    """Load ELO ratings from JSON file, or return default ratings.
    
    Returns:
        Dictionary with structure: {game_name: {agent_id: {"mu": float, "sigma": float}}}
    """
    if os.path.exists(ELO_FILE) and os.path.getsize(ELO_FILE) > 0:
        try:
            with open(ELO_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_elo(elo: Dict):
    """Save ELO ratings to JSON file.
    
    Args:
        elo: Dictionary with structure: {game_name: {agent_id: {"mu": float, "sigma": float}}}
    """
    with open(ELO_FILE, "w") as f:
        json.dump(elo, f, indent=2)

def check_elo_improvement(env_id, testing_agent, proposed_elo):
    """
    Check if the testing agent's ELO (mu) improved compared to the original stored mu.
    
    Args:
        env_id: The game name (e.g., "Avalon-v0")
        testing_agent: The agent object to check
        proposed_elo: The proposed ELO structure after updates
        
    Returns:
        True if the agent's mu (mean skill) improved compared to original stored mu, False otherwise
    """
    # Load original ELO from file to get the stored mu
    elo_data = load_elo()
    game_name = env_id
    if game_name not in elo_data:
        return False
    game_elo = elo_data[game_name]
    testing_agent_id = testing_agent.id
    if testing_agent_id not in game_elo:
        return False
    
    if game_name not in elo_data or testing_agent_id not in elo_data[game_name]:
        # No stored rating, so any improvement is valid
        original_mu = DEFAULT_MU
    else:
        original_rating = elo_data[game_name][testing_agent_id]
        original_mu = original_rating.get("mu", DEFAULT_MU)
    
    if game_name not in proposed_elo or testing_agent_id not in proposed_elo[game_name]:
        return False
    
    proposed_rating = proposed_elo[game_name][testing_agent_id]
    proposed_mu = proposed_rating.get("mu", DEFAULT_MU)
    
    return proposed_mu > original_mu


def apply_elo_algorithm(env_id, agents, results, testing_agent=None):
    """
    Load ELO from elo.json, clone it, and sequentially apply results.
    
    If testing_agent is provided, it will be reset to default mu/sigma in the cloned ELO before
    applying results. Otherwise, all agents keep their current ratings.
    
    Args:
        env_id: The name of the game (e.g., "Avalon-v0")
        agents: Dictionary of player_id -> agent object
        results: Dictionary of game_idx -> {"rewards": Dict, "game_info": Dict}
        testing_agent: Optional agent to test (will be reset to defaults in cloned ELO if provided)
    
    Returns:
        The cloned ELO data after applying all results sequentially
    """
    # Load and clone ELO data
    elo_data = load_elo()
    cloned_elo = copy.deepcopy(elo_data)
    game_name = env_id

    # Ensure game exists in cloned ELO
    if game_name not in cloned_elo:
        cloned_elo[game_name] = {}
    
    game_elo = cloned_elo[game_name]
    
    # Reset testing agent to default mu/sigma if provided
    if testing_agent is not None:
        testing_agent_id = testing_agent.id
        game_elo[testing_agent_id] = {"mu": DEFAULT_MU, "sigma": DEFAULT_SIGMA}
    
    # Sequentially apply each game's results
    for game_idx in sorted(results.keys()):
        game_result = results[game_idx]
        # Skip games with errors or missing rewards
        if "error" in game_result or game_result.get("rewards") is None:
            continue
        
        rewards = game_result["rewards"]
        # Apply ELO update to the cloned ELO (without saving to file)
        cloned_elo = update_elo(game_name, agents, rewards, cloned_elo)
    
    return cloned_elo

def _group_players_by_outcome(rewards: Dict) -> List[List[int]]:
    """
    Group players by their reward outcome to determine teams/rankings.
    
    Args:
        rewards: Dictionary of player_id -> reward value
        
    Returns:
        List of teams, ordered by outcome (best first, worst last)
        Each team is a list of player IDs with the same reward.
    """
    # Group players by reward value
    reward_groups = {}
    for pid, reward in rewards.items():
        if reward not in reward_groups:
            reward_groups[reward] = []
        reward_groups[reward].append(pid)
    
    # Sort by reward value (descending) to get ranking from best to worst
    sorted_rewards = sorted(reward_groups.keys(), reverse=True)
    teams = [reward_groups[reward] for reward in sorted_rewards]
    
    return teams


def update_elo(game_name: str, agents: Dict, rewards: Dict, elo: Dict) -> Dict:
    """
    Update ELO ratings using TrueSkill algorithm based on game results.
    
    Uses TrueSkill to update ratings for multi-agent team-based games.
    Groups players by reward outcome and updates ratings accordingly.
    
    Args:
        game_name: The name of the game (e.g., "Werewolf-v0")
        agents: Dictionary of player_id -> agent object
        rewards: Dictionary of player_id -> reward value (positive = winner, negative = loser)
        elo: ELO data dict to update (will be modified in place)
    
    Returns:
        The updated ELO data dict with structure: {game_name: {agent_id: {"mu": float, "sigma": float}}}
    """
    elo_data = elo
    
    # Get or create game-specific ELO dict
    if game_name not in elo_data:
        elo_data[game_name] = {}
    game_elo = elo_data[game_name]
    
    # Get agent IDs for all players
    agent_ids = {pid: agent.id for pid, agent in agents.items()}
    
    # Initialize ELO for each agent if it doesn't exist
    for pid, agent in agents.items():
        agent_id = agent_ids[pid]
        if agent_id not in game_elo:
            game_elo[agent_id] = {"mu": DEFAULT_MU, "sigma": DEFAULT_SIGMA}
    
    # Group players by outcome (reward value) to form teams
    teams = _group_players_by_outcome(rewards)
    
    if len(teams) < 2:
        # All players have same reward - no ranking, return unchanged
        return elo_data
    
    # Convert teams to TrueSkill Rating objects
    trueskill_teams = []
    team_agent_ids = []  # Track agent IDs for each team
    
    for team in teams:
        team_ratings = []
        team_ids = []
        for pid in team:
            if pid not in agent_ids:
                continue
            agent_id = agent_ids[pid]
            if agent_id not in game_elo:
                continue
            rating_dict = game_elo[agent_id]
            mu = rating_dict.get("mu", DEFAULT_MU)
            sigma = rating_dict.get("sigma", DEFAULT_SIGMA)
            rating = Rating(mu=mu, sigma=sigma)
            team_ratings.append(rating)
            team_ids.append(agent_id)
        
        if team_ratings:  # Only add non-empty teams
            trueskill_teams.append(team_ratings)
            team_agent_ids.append(team_ids)
    
    if len(trueskill_teams) < 2:
        # Need at least 2 teams to rank
        return elo_data
    
    # Update ratings using TrueSkill (rank 0 = best, rank 1 = second best, etc.)
    ranks = list(range(len(trueskill_teams)))
    updated_teams = rate(trueskill_teams, ranks=ranks)
    
    # Update the ELO data with new ratings
    for team_idx, updated_team in enumerate(updated_teams):
        agent_id_list = team_agent_ids[team_idx]
        for rating_idx, updated_rating in enumerate(updated_team):
            agent_id = agent_id_list[rating_idx]
            game_elo[agent_id] = {
                "mu": updated_rating.mu,
                "sigma": updated_rating.sigma
            }

    elo_data[game_name] = game_elo
    return elo_data


