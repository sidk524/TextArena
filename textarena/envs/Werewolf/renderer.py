def render_players_list(player_roles: dict, alive_players: list, show_roles: bool = False) -> str:
    """Render the player list in a clean, text-friendly format."""
    lines = []
    for pid in sorted(player_roles):
        status = "🟢 Alive" if pid in alive_players else "💀 Dead"
        lines.append(f"  • Player {pid}: {status}")
    return "\n".join(lines)


def render_alive_dead_lists(player_roles: dict, alive_players: list, eliminated_players: list) -> str:
    """Render separate lists of alive and dead players for public view."""
    alive_sorted = sorted(alive_players)
    dead_sorted = sorted(eliminated_players or [])

    lines = []
    lines.append("👥 Players:")

    # Alive
    lines.append("  🟢 Alive:")
    if alive_sorted:
        for pid in alive_sorted:
            lines.append(f"    • Player {pid}")
    else:
        lines.append("    • None")

    # Dead
    lines.append("  💀 Dead:")
    if dead_sorted:
        for pid in dead_sorted:
            lines.append(f"    • Player {pid}")
    else:
        lines.append("    • None")

    return "\n".join(lines)


def render_phase_info(game_state: dict) -> str:
    """Render current phase and round information."""
    phase = str(game_state.get("phase", "Unknown"))
    num_players = game_state.get("num_players", 0)
    alive_players = game_state.get("alive_player_ids", [])
    
    lines = []
    lines.append(f"🌙 Current Phase: {phase}")
    lines.append(f"👥 Alive Players: {len(alive_players)}/{num_players}")
    
    # Add phase-specific context
    if "Night" in phase or "Werewolf" in phase or "Seer" in phase or "Witch" in phase:
        lines.append("  🌃 It's night time - special roles are acting")
    elif "Day" in phase:
        lines.append("  ☀️ It's day time - all players can discuss and vote")
    
    return "\n".join(lines)


def render_night_actions(game_state: dict, viewer_is_witch: bool = False) -> str:
    """Render night phase actions and results."""
    phase = str(game_state.get("phase", "")).lower()
    if "day" in phase:
        return ""

    lines = []
    lines.append("🌙 Night Phase:")
    if viewer_is_witch:
        lines.append("  🌃 Night in progress.")
        attacked_player = game_state.get("attacked_player_id")
        if attacked_player is not None:
            lines.append(f"  ⚔️ Attack Info (Witch only): Player {attacked_player} was attacked")
    else:
        lines.append("  🌃 Night in progress. No public information is available.")
    return "\n".join(lines)


def render_day_actions(game_state: dict) -> str:
    """Render day phase actions and voting."""
    phase = str(game_state.get("phase", "")).lower()
    if "night" in phase or "werewolf" in phase or "seer" in phase or "witch" in phase:
        return ""
    
    lines = []
    lines.append("☀️ Day Actions:")
    
    # Day votes
    day_votes = game_state.get("day_votes", {})
    if day_votes:
        lines.append("  🗳️ Village Votes:")
        vote_counts = {}
        for voter, target in day_votes.items():
            vote_counts[target] = vote_counts.get(target, 0) + 1
        
        for target, count in sorted(vote_counts.items()):
            lines.append(f"    • Player {target}: {count} vote{'s' if count != 1 else ''}")
    else:
        lines.append("  🗳️ Village Votes: None yet")
    
    # Previous day results
    voted_player = game_state.get("voted_player_id")
    if voted_player is not None:
        lines.append(f"  ⚖️ Last Vote Result: Player {voted_player} was eliminated")
    
    return "\n".join(lines)


def render_game_progress(game_state: dict) -> str:
    """Render overall game progress and team composition."""
    alive_players = game_state.get("alive_player_ids", [])

    lines = []
    lines.append("📊 Game Progress:")
    lines.append(f"  👥 Players remaining: {len(alive_players)}")
    return "\n".join(lines)


def render_potion_status(game_state: dict) -> str:
    """Render Witch potion counts remaining (Witch-only)."""
    num_cures = game_state.get("num_cures", 0)
    num_poisons = game_state.get("num_poisons", 0)

    lines = []
    lines.append("🧪 Witch Potions:")
    lines.append(f"  💚 Cure potions left: {num_cures}")
    lines.append(f"  💀 Poison potions left: {num_poisons}")
    return "\n".join(lines)


def render_seer_info(game_state: dict) -> str:
    """Render Seer-only list of revealed players and their roles."""
    revealed = game_state.get("revealed_player_ids", []) or []
    player_roles = game_state.get("player_roles", {})

    lines = []
    lines.append("🔮 Seer Revelations:")
    if revealed:
        for pid in sorted(revealed):
            role = player_roles.get(pid, "Unknown")
            lines.append(f"  • Player {pid}: {role}")
    else:
        lines.append("  • No players revealed yet")
    return "\n".join(lines)

def render_game_state(
    game_state: dict,
    show_players: bool = False,
    show_roles: bool = False,
    viewer_is_witch: bool = False,
    viewer_is_seer: bool = False,
) -> str:
    """Main Werewolf board renderer."""
    phase = str(game_state.get("phase", "Unknown"))
    num_players = game_state.get("num_players", 0)
    player_roles = game_state.get("player_roles", {})
    alive_players = game_state.get("alive_player_ids", [])
    eliminated_players = game_state.get("eliminated_player_ids", [])
    
    lines = [
        f"🐺 WEREWOLF GAME STATUS",
        "",
    ]
    
    # Core game info
    lines.append(render_phase_info(game_state))
    lines.append("")
    
    # Game progress
    lines.append(render_game_progress(game_state))
    lines.append("")
    
    # Always show alive/dead lists
    lines.append(render_alive_dead_lists(player_roles, alive_players, eliminated_players))
    lines.append("")
    
    # Phase-specific actions
    night_actions = render_night_actions(game_state, viewer_is_witch=viewer_is_witch)
    if night_actions:
        lines.append(night_actions)
        lines.append("")
    
    day_actions = render_day_actions(game_state)
    if day_actions:
        lines.append(day_actions)
        lines.append("")

    # Witch-only information: potion availability
    if viewer_is_witch:
        lines.append(render_potion_status(game_state))

    # Seer-only information: revealed players and roles
    if viewer_is_seer:
        if lines and lines[-1] != "":
            lines.append("")
        lines.append(render_seer_info(game_state))
    
    return "\n".join(lines)
