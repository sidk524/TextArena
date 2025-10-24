import ast
from dataclasses import dataclass, field
from enum import Enum
import re, random
from typing import ClassVar, Set, Tuple, Dict, Optional, List, Type, TypeVar, TypedDict
import textarena as ta
from textarena.envs.Werewolf.renderer import render_game_state
from collections import defaultdict

MIN_PLAYERS = 6
MAX_PLAYERS = 15

WEREWOLF_RULES = """
You are playing Werewolf, a hidden-role social deduction game.
WEREWOLF GAME RULES

The Werewolf game is a hidden-role social deduction game.
Each player belongs to one of two sides:

• The Good side: Villagers, Seer, Witch
• The Evil side: Werewolves

Only the Werewolves know who each other are.
All other players know only their own role.

The game proceeds through alternating Night and Day phases.
Each round has one Night phase and one Day phase.
The game continues until one side wins.

1. Night Phase

During the Night, only players with special roles act.
The sequence of actions is fixed and happens privately.

Step 1. Werewolves act first.
All Werewolves secretly agree on a single living target to eliminate.
If they fail to agree, no one is killed that night.
Their target is hidden from all other players except the Witch later.

Step 2. The Seer acts next.
The Seer privately selects one living player to inspect.
The game reveals to the Seer whether that player is a Werewolf or not.
This information is private and cannot be shared except through discussion during the Day.

Step 3. The Witch acts last.
The Witch learns who was attacked by the Werewolves.
The Witch may use one of two potions:

Cure potion: Save the attacked player from dying. This can be used once in the entire game.

Poison potion: Eliminate any living player of their choice. This can also be used once in the entire game.
The Witch can choose to do nothing.
Both potions cannot be used on the same night.

When the Night phase ends, the game records which players live or die and moves to the Day phase.

2. Day Phase

All surviving players wake up and discuss what happened.
Players may speak freely, share theories, lie, or defend themselves.
No player actions such as killing or revealing are allowed during discussion.

After discussion, every living player must vote publicly for one player to eliminate.
The player with the most votes is executed and removed from the game.
If there is a tie, the engine may either execute no one or choose randomly; this rule must be consistent for the entire game.
Dead players can no longer act, vote, or speak.

3. Game Progression

After the Day phase, the next Night phase begins.
The cycle of Night and Day repeats until a win condition is reached.

4. Win Conditions

Good side wins if all Werewolves have been eliminated.
Evil side wins if the number of living Werewolves is equal to or greater than the number of living non-Werewolves.

5. Role Descriptions and Behavioral Rules

Villager:
Has no special powers. Participates in discussion and daytime voting only.

Werewolf:
Knows all other Werewolves.
Acts at night to collectively choose one target to eliminate.
Must pretend to be innocent during the day to avoid detection.

Seer:
At night, may reveal the true alignment of one player.
Must keep this information secret and use it strategically to influence votes without being exposed.

Witch:
Has one Cure potion and one Poison potion to use across the entire game.
Learns the Werewolves’ target each night and may choose to save or kill someone.
Must decide strategically when to use each potion.

6. Rules on Information and Communication

• All actions performed at night are private. Only the relevant player(s) are informed.
• All speech during the day is public and heard by every living player.
• Werewolves communicate secretly only during the Night phase.
• The Seer and Witch should avoid revealing their identities to avoid being killed.
• Dead players cannot act, vote, or communicate.

7. Phase-Specific Action Restrictions

Each role can only act during its designated phase.
No player may act outside their allowed time.

• During the Werewolf phase: Only Werewolves may choose a target.
• During the Seer phase: Only the Seer may choose someone to reveal.
• During the Witch phase: Only the Witch may decide to cure, poison, or do nothing.
• During the Day discussion phase: All living players may talk, but no one may act.
• During the Day vote phase: All living players must vote once, and no one may talk or perform special actions.

Any attempt to act outside of your permitted phase or without authorization results in immediate elimination.

8. Moderator and System Behavior

• The game engine enforces phase transitions automatically.
• The engine communicates only the information relevant to each role.
• The engine announces deaths and public outcomes at the start of each Day.
• The engine checks for win conditions after each Day and Night.

9. Example Turn Summary (for reasoning)

Night:

Werewolves choose one player to attack.

Seer chooses one player to inspect.

Witch learns the attack target and optionally saves or poisons.
Day:

The game announces who died overnight.

All living players discuss and then vote.

The most-voted player dies.

The next night begins.

10. Behavioral Objective for the Agent

Your objective depends on your role:

If you are a Werewolf: survive and eliminate all non-Werewolves. Deceive others during the day to avoid discovery.

If you are a Villager, Seer, or Witch: identify and eliminate all Werewolves through reasoning, communication, and strategic action.

You must reason about hidden information, social cues, and game state to decide your next move.
"""

VILLAGER_NAME = "Villager"
WEREWOLF_NAME = "Werewolf"
SEER_NAME = "Seer"
WITCH_NAME = "Witch"

# Alignment sets
EVIL_NAMES = {WEREWOLF_NAME}
GOOD_NAMES = {VILLAGER_NAME, SEER_NAME, WITCH_NAME}

# Base role descriptions
BASE_ROLE_DESCRIPTIONS = {
    VILLAGER_NAME: (
        "A regular Villager with no special powers. "
        "Participates in discussions and voting during the day to find and eliminate Werewolves."
    ),
    WEREWOLF_NAME: (
        "An Evil player who knows the other Werewolves. "
        "Each night, the Werewolves secretly agree on one player to eliminate. "
        "During the day, they must hide their identity and mislead others."
    ),
    SEER_NAME: (
        "A Good player with the ability to see the true identity of one player each night. "
        "Uses this information to guide the village without revealing their role."
    ),
    WITCH_NAME: (
        "A Good player with two potions usable at night: "
        "one Cure potion to save a player targeted by the Werewolves (once per game), "
        "and one Poison potion to eliminate a player of their choice (once per game). "
        "Must decide wisely when to use these powers."
    ),
}

class Phase(Enum):
    WEREWOLF_DISCUSSION = "Werewolf-Discussion"
    WEREWOLF_VOTE = "Werewolf-Vote"
    SEER_REVEAL = "Seer-Reveal"
    WITCH_CHOICE = "Witch-Choice"
    DAY_DISCUSSION = "Day-Discussion"
    DAY_VOTE = "Day-Vote"

INITIAL_PHASE = Phase.WEREWOLF_DISCUSSION

def get_team(role_name: str) -> str:
    if role_name in GOOD_NAMES:
        team = "Good"
    elif role_name in EVIL_NAMES:
        team = "Evil"
    else:
        raise ValueError(f"Team unknown for name: {role_name}")
    return team

def get_role_description(role_name: str) -> str:
    team = get_team(role_name)
    base_role_description = BASE_ROLE_DESCRIPTIONS[role_name]
    description = f"{role_name} ({team}):\n{base_role_description}"
    return description

def get_role_descriptions(role_names: List[str]) -> str:
    descriptions = [get_role_description(role) for role in role_names]
    return "\n".join(descriptions)

@dataclass
class Role:
    name: ClassVar[str]
    team: ClassVar[str]
    description: ClassVar[str]
    _registry: ClassVar[Dict[str, Type["Role"]]] = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.name = cls.__name__
        cls.team = get_team(cls.name)
        cls.description = get_role_description(cls.name)
        Role._registry[cls.__name__] = cls
    
    @classmethod
    def create(cls, name: str) -> "Role":
        try:
            return cls._registry[name]()
        except KeyError:
            raise ValueError(f"Tried to create unknown role: {name}")

    def get_prompt(self, player_id: int, game_state: Dict) -> str:
        return self.base_prompt(player_id, game_state)
    
    def base_prompt(self, player_id: int, game_state: Dict) -> str:
        player_roles = game_state["player_roles"]
        num_players = game_state["num_players"]
        unique_roles = set(player_roles.values())
        role_descriptions = get_role_descriptions(unique_roles)
        return (
            f"{WEREWOLF_RULES}\n"
            "Players will be given one of the following roles:\n"
            f"{role_descriptions}\n"
            f"---\n"
            f"There are {num_players} players in this game: {', '.join([f'Player {i}' for i in range(num_players)])}\n\n"
            f"You are Player {player_id}.\n"
            f"Role: {self.name}\nTeam: {self.team}\nDescription: {self.description}\n"
            f"{self.team_prompt(player_roles)}\n"
        )

    def team_prompt(self, player_roles: Dict[int, str]) -> str:
        """Return the team's win condition message"""
        if self.team == "Good":
            return (
                "Win conditions:\n"
                f"You win if all Werewolves are eliminated."
            )
        elif self.team == "Evil":
            return (
                "Win conditions:\n"
                f"You win if the number of Werewolves is equal to or greater than the number of remaining non-Werewolves."
            )
        else:
            raise ValueError("Unknown team configuration")


class Villager(Role):
    pass

class Werewolf(Role):
    def get_prompt(self, player_id: int, game_state: Dict) -> str:
        player_roles = game_state["player_roles"]
        return self.base_prompt(player_id, game_state) + (
            "\nYou know the other Werewolves:\n"
            + "\n".join([f"Player {pid}: {role}" for pid, role in player_roles.items() if role == WEREWOLF_NAME])
        )

class Seer(Role):
    def get_prompt(self, player_id: int, game_state: Dict) -> str:
        player_roles = game_state["player_roles"]
        return self.base_prompt(player_id, game_state) + (
            "\nEach night, you can reveal one new player to learn their true role." +
            f"You know the following players roles:\n"
            + "\n".join([f"Player {pid}: {player_roles[pid]}" for pid in game_state["revealed_player_ids"]])
        )

class Witch(Role):
    def get_prompt(self, player_id: int, game_state: Dict) -> str:
        base = self.base_prompt(player_id, game_state)
        
        if game_state.get("attacked_player_id") is not None:
            attacked_player = game_state["attacked_player_id"]
            attacked_info = f"Player {attacked_player} was attacked by the Werewolves this night.\n"
        else:
            attacked_info = "No one was attacked by the Werewolves this night.\n"
        
        return base + (
            f"You know who was attacked by the Werewolves each night:\n"
            f"{attacked_info}"
            f"You have one Cure potion and one Poison potion. You can use them to save a player or kill a player {game_state['num_cures']} times and {game_state['num_poisons']} times respectively."
        )
    
class WerewolfParser:
    # Witch cure pattern: <cure></cure>
    cure_pattern = re.compile(r"<cure>\s*</cure>", re.IGNORECASE)
    
    # Witch poison pattern: <poison>(any number)</poison>
    poison_pattern = re.compile(r"<poison>\s*(\d+)\s*</poison>", re.IGNORECASE)
    
    # Witch no action pattern: <no_action></no_action>
    no_action_pattern = re.compile(r"<no_action>\s*</no_action>", re.IGNORECASE)
    
    # Werewolf kill vote pattern: <kill>(any number)</kill>
    kill_pattern = re.compile(r"<kill>\s*(\d+)\s*</kill>", re.IGNORECASE)
    
    # Seer reveal pattern: <reveal>(any number)</reveal>
    reveal_pattern = re.compile(r"<reveal>\s*(\d+)\s*</reveal>", re.IGNORECASE)
    
    # Vote pattern: <vote>(any number)</vote>
    vote_pattern = re.compile(r"<vote>\s*(\d+)\s*</vote>", re.IGNORECASE)


    @staticmethod
    def parse_kill(text: str) -> Optional[int]:
        """
        Parses a werewolf kill vote from text.
        Returns the target player ID, or None if not found.
        """
        m = WerewolfParser.kill_pattern.search(text)
        return int(m.group(1)) if m else None

    @staticmethod
    def parse_reveal(text: str) -> Optional[int]:
        """
        Parses a seer reveal action from text.
        Returns the target player ID, or None if not found.
        """
        m = WerewolfParser.reveal_pattern.search(text)
        return int(m.group(1)) if m else None

    @staticmethod
    def parse_vote(text: str) -> Optional[int]:
        """
        Parses a day vote from text.
        Returns the target player ID, or None if not found.
        """
        m = WerewolfParser.vote_pattern.search(text)
        return int(m.group(1)) if m else None

    @staticmethod
    def parse_witch_choice(text: str) -> Tuple[Optional[str], Optional[int]]:
        """
        Parses a witch choice from text.
        Returns (action_type, target_player_id) where action_type is 'cure', 'poison', 'no_action', or None.
        """
        # Check for cure first
        if WerewolfParser.cure_pattern.search(text):
            return ("cure", None)
        
        # Check for poison
        m = WerewolfParser.poison_pattern.search(text)
        if m:
            return ("poison", int(m.group(1)))
        
        # Check for no action
        if WerewolfParser.no_action_pattern.search(text):
            return ("no_action", None)
        
        return (None, None)

class GameState(TypedDict):
    num_players: int
    phase: Phase
    alive_player_ids: List[int]
    eliminated_player_ids: List[int]
    player_roles: Dict[int, str]
    role_pids: Dict[str, List[int]]
    attacked_player_id: Optional[int]
    poisoned_player_id: Optional[int]
    voted_player_id: Optional[int]
    revealed_player_ids: List[int]
    num_cures: int
    num_poisons: int
    cure_used: bool
    poison_used: bool
    werewolf_ratio: float
    werewolf_votes: Dict[int, int]
    day_votes: Dict[int, int]

def init_game_state(num_players: int, player_roles: Dict[int, str], werewolf_ratio: float, num_cures: int = 1, num_poisons: int = 1) -> GameState:
    role_pids = defaultdict(list)
    for pid, role in player_roles.items():
        role_pids[role].append(pid)
    
    return GameState(
        num_players=num_players,
        phase=INITIAL_PHASE,
        alive_player_ids=list(range(num_players)),
        eliminated_player_ids=[],
        player_roles=player_roles,
        role_pids=role_pids,
        attacked_player_id=None,
        poisoned_player_id=None,
        voted_player_id=None,
        revealed_player_ids=[],
        num_cures=num_cures,
        num_poisons=num_poisons,
        cure_used=False,
        poison_used=False,
        werewolf_ratio=werewolf_ratio,
        werewolf_votes={},
        day_votes={},
    )

def count_alive_roles(game_state: GameState) -> tuple[int, int]:
    """Count alive werewolves and good players from current alive players."""
    alive_players = game_state["alive_player_ids"]
    player_roles = game_state["player_roles"]
    
    alive_werewolves = sum(1 for pid in alive_players if player_roles.get(pid) == WEREWOLF_NAME)
    alive_good = len(alive_players) - alive_werewolves
    
    return alive_werewolves, alive_good

class WerewolfEnv(ta.Env):
    def __init__(self, werewolf_ratio: float = 0.33):
        self.werewolf_ratio = werewolf_ratio

    def reset(self, num_players: int, seed: Optional[int] = None):
        assert MIN_PLAYERS <= num_players <= MAX_PLAYERS, f"Player count must be between {MIN_PLAYERS} and {MAX_PLAYERS}. Got {num_players} players."
        self.state = ta.TeamMultiPlayerState(num_players=num_players, seed=seed)
        self._assign_roles(num_players)
        self.phase: Phase = INITIAL_PHASE
        game_state = init_game_state(num_players, self.player_roles, self.werewolf_ratio, num_cures=1, num_poisons=1)
        self.state.reset(game_state=game_state, player_prompt_function=self._prompt, secret_roles=self.player_roles)
        self._render_game_state()

        self._send_phase_prompts() # populate self.next_player_ids
        self.state.manually_set_current_player_id(self.next_player_ids.pop())
    
    def _render_game_state(self):
        game_state = self.state.game_state
        role_pids = self.state.game_state.get("role_pids", {})
        alive_ids = set(self.state.game_state.get("alive_player_ids", []))
        
        # Send role-specific boards to special roles
        witch_ids = role_pids.get(WITCH_NAME, [])
        if witch_ids:
            witch_pid = witch_ids[0]
            if witch_pid in alive_ids:
                witch_board = render_game_state(game_state, viewer_is_witch=True)
                self.state.add_observation(to_id=witch_pid, message=witch_board, observation_type=ta.ObservationType.GAME_BOARD)

        seer_ids = role_pids.get(SEER_NAME, [])
        if seer_ids:
            seer_pid = seer_ids[0]
            if seer_pid in alive_ids:
                seer_board = render_game_state(game_state, viewer_is_seer=True)
                self.state.add_observation(to_id=seer_pid, message=seer_board, observation_type=ta.ObservationType.GAME_BOARD)
        
        # Send public board to all other players (Villagers, Werewolves, and any other roles)
        public_board = render_game_state(game_state)
        for player_id in alive_ids:
            # Skip Witch and Seer as they already got their specific boards
            if (player_id not in (witch_ids + seer_ids) or 
                (not witch_ids and not seer_ids) or
                (player_id not in witch_ids and player_id not in seer_ids)):
                self.state.add_observation(to_id=player_id, message=public_board, observation_type=ta.ObservationType.GAME_BOARD)

    def _assign_roles(self, num_players: int):
        self.player_roles = {}
        self.roles = {}
        role_pool = self.generate_roles(num_players)
        for pid, r_name in enumerate(role_pool):
            self.player_roles[pid] = r_name
            self.roles[pid] = Role.create(r_name)

    def _prompt(self, player_id: int, game_state: dict) -> str:
        role_obj = self.roles[player_id]
        return role_obj.get_prompt(player_id=player_id, game_state=game_state)

    def generate_roles(self, num_players: int) -> List[str]:
        num_werewolves = max(1, round(num_players * self.werewolf_ratio))
        num_villagers = num_players - num_werewolves - 2  # 1 seer + 1 witch
        role_pool = ["Werewolf"] * num_werewolves + ["Villager"] * num_villagers + ["Seer", "Witch"]
        random.shuffle(role_pool)
        return role_pool

    def step(self, action: str) -> Tuple[bool, ta.Info]:
        pid = self.state.current_player_id
        phase_dispatch = {
            Phase.WEREWOLF_DISCUSSION: self._handle_werewolf_discussion,
            Phase.WEREWOLF_VOTE: self._handle_werewolf_vote,
            Phase.SEER_REVEAL: self._handle_seer_reveal,
            Phase.WITCH_CHOICE: self._handle_witch_choice,
            Phase.DAY_DISCUSSION: self._handle_day_discussion,
            Phase.DAY_VOTE: self._handle_day_vote,
        }
        phase_dispatch[self.phase](pid, action)
        self._after_player_action() # rotate / advance phase
        return self.state.step(rotate_player=False)

    def _handle_werewolf_discussion(self, pid: int, action: str):
        # Send message from current werewolf to all other werewolves
        alive_werewolves = [p for p in self.state.game_state["alive_player_ids"] if self.player_roles[p] == WEREWOLF_NAME]
        print(f"DEBUG: Werewolf {pid} says: \"{action}\"")
        for other_werewolf in alive_werewolves:
            if other_werewolf != pid:  # Don't send to self
                self.state.add_observation(from_id=pid, to_id=other_werewolf, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)

    def _handle_werewolf_vote(self, pid: int, action: str):
        target = WerewolfParser.parse_kill(action)
        alive = set(self.state.game_state["alive_player_ids"])
        if target is None or target not in alive:
            fatal = self.state.set_invalid_move("Invalid kill target.")
            if not fatal: 
                return
            else: # player was eliminated by invalid move
                self.state.made_invalid_move = False  # such that we can rotate off the player 
                return
        self.state.game_state["werewolf_votes"][pid] = target

    def _handle_seer_reveal(self, pid: int, action: str):
        target = WerewolfParser.parse_reveal(action)
        if target is None or target not in self.state.game_state["alive_player_ids"]:
            fatal = self.state.set_invalid_move("Invalid reveal target.")
            if not fatal: 
                return
            else: # player was eliminated by invalid move
                self.state.made_invalid_move = False  # such that we can rotate off the player 
                return
        self.state.game_state["revealed_player_ids"].append(target)
        print(f"DEBUG: Seer {pid} reveals Player {target}")

    def _handle_witch_choice(self, pid: int, action: str):
        action_type, target = WerewolfParser.parse_witch_choice(action)
        if action_type is None:
            fatal = self.state.set_invalid_move("Invalid witch choice. Use <cure></cure>, <poison>X</poison>, or <no_action></no_action>.")
            if not fatal: 
                return
            else: # player was eliminated by invalid move
                self.state.made_invalid_move = False  # such that we can rotate off the player 
                return
    
        if action_type == "cure":
            if self.state.game_state["num_cures"] <= 0:
                fatal = self.state.set_invalid_move("You have no more Cure potions left.")
                if not fatal: 
                    return
                else: # player was eliminated by invalid move
                    self.state.made_invalid_move = False  # such that we can rotate off the player 
                    return
            self.state.game_state["num_cures"] -= 1
            self.state.game_state["cure_used"] = True
            self.state.game_state["attacked_player_id"] = None
            print(f"DEBUG: Witch {pid} uses CURE potion")
        elif action_type == "poison":
            if self.state.game_state["num_poisons"] <= 0:
                fatal = self.state.set_invalid_move("You have no more Poison potions left.")
                if not fatal: 
                    return
                else: # player was eliminated by invalid move
                    self.state.made_invalid_move = False  # such that we can rotate off the player 
                    return
            if target is None or target not in self.state.game_state["alive_player_ids"]:
                fatal = self.state.set_invalid_move("Invalid poison target.")
                if not fatal: 
                    return
                else: # player was eliminated by invalid move
                    self.state.made_invalid_move = False  # such that we can rotate off the player 
                    return
            self.state.game_state["num_poisons"] -= 1
            self.state.game_state["poison_used"] = True
            self.state.game_state["poisoned_player_id"] = target
            print(f"DEBUG: Witch {pid} uses POISON on Player {target}")
        elif action_type == "no_action":
            print(f"DEBUG: Witch {pid} chooses NO ACTION")
            pass

    def _handle_day_discussion(self, pid: int, action: str):
        print(f"DEBUG: Player {pid} says: \"{action}\"")
        self.state.add_observation(from_id=pid, message=action, observation_type=ta.ObservationType.PLAYER_ACTION)

    def _handle_day_vote(self, pid: int, action: str):
        target = WerewolfParser.parse_vote(action)
        alive = set(self.state.game_state["alive_player_ids"])
        if target is None or target not in alive:
            fatal = self.state.set_invalid_move("Invalid vote target.")
            if not fatal: 
                return
            else: # player was eliminated by invalid move
                self.state.made_invalid_move = False  # such that we can rotate off the player 
                return
        self.state.game_state["day_votes"][pid] = target
        print(f"DEBUG: Player {pid} votes for Player {target}")

    def _after_player_action(self):
        if self.state.made_invalid_move: return
        if self.next_player_ids:
            self.state.manually_set_current_player_id(self.next_player_ids.pop())
            return
        # Phase complete ─ evaluate votes / killings, decide next phase, queue players
        match self.phase:
            case Phase.WEREWOLF_VOTE:
                self._resolve_werewolf_vote()
            case Phase.SEER_REVEAL:
                self._resolve_seer_reveal()
            case Phase.WITCH_CHOICE:
                self._resolve_night_actions()
            case Phase.DAY_VOTE:
                self._resolve_day_vote()

        if self.state.done: return

        # Reset round state after day vote (start of new round)
        if self.phase == Phase.DAY_VOTE:
            self._reset_round_state()

        # Advance to next phase
        while True:
            self.phase = self._compute_next_phase()
            print(f"DEBUG: Phase transition to {self.phase.value}")
            self.state.game_state["phase"] = self.phase
            self._render_game_state()
            self._send_phase_prompts()
            if self.next_player_ids:
                break
        self.state.manually_set_current_player_id(self.next_player_ids.pop())
    
    def _resolve_seer_reveal(self):
        revealed_players = self.state.game_state["revealed_player_ids"]
        if revealed_players:
            # Get the most recently revealed player (last in the list)
            target = revealed_players[-1]
            role = self.player_roles[target]
            is_wolf = role == WEREWOLF_NAME
            message = f"Player {target} is {'a Werewolf' if is_wolf else 'not a Werewolf'}."
            if SEER_NAME in self.state.game_state["role_pids"]:
                seer_pid = self.state.game_state["role_pids"][SEER_NAME][0]
                if seer_pid in self.state.game_state["alive_player_ids"]:
                    self.state.add_observation(to_id=seer_pid, message=message, observation_type=ta.ObservationType.GAME_MESSAGE)

    def _resolve_werewolf_vote(self):
        # Count votes from werewolves only
        target_vote_counts = {}
        alive_werewolves = []
        
        # Get all alive werewolves
        for pid in self.state.game_state["alive_player_ids"]:
            if self.player_roles[pid] == WEREWOLF_NAME:
                alive_werewolves.append(pid)
        
        print(f"DEBUG: Werewolf vote resolution:")
        print(f"  - alive_werewolves: {alive_werewolves}")
        print(f"  - all_werewolf_votes: {self.state.game_state['werewolf_votes']}")
        
        # Count votes from alive werewolves only
        for voter_id, target_id in self.state.game_state["werewolf_votes"].items():
            if voter_id in alive_werewolves and target_id in self.state.game_state["alive_player_ids"]:
                target_vote_counts[target_id] = target_vote_counts.get(target_id, 0) + 1
                print(f"  - Valid vote: Werewolf {voter_id} votes for Player {target_id}")
            else:
                print(f"  - Invalid vote: Werewolf {voter_id} votes for Player {target_id} (voter_alive: {voter_id in alive_werewolves}, target_alive: {target_id in self.state.game_state['alive_player_ids']})")
                pass
        
        print(f"  - target_vote_counts: {target_vote_counts}")
        
        # Check for unanimous consensus among alive werewolves
        if target_vote_counts and len(alive_werewolves) > 0:
            max_votes = max(target_vote_counts.values())
            print(f"  - max_votes: {max_votes}, required_for_unanimity: {len(alive_werewolves)}")
            # Unanimous consensus: all alive werewolves must vote for the same target
            if max_votes == len(alive_werewolves):
                # Find the target that received all votes
                unanimous_targets = [target_id for target_id, vote_count in target_vote_counts.items() if vote_count == max_votes]
                if len(unanimous_targets) == 1:
                    self.state.game_state["attacked_player_id"] = unanimous_targets[0]
                    print(f"  - UNANIMOUS CONSENSUS: Attack Player {unanimous_targets[0]}")
                else:
                    self.state.game_state["attacked_player_id"] = None
                    print(f"  - Multiple unanimous targets (shouldn't happen): {unanimous_targets}")
            else:
                # No unanimous consensus - no attack
                self.state.game_state["attacked_player_id"] = None
                print(f"  - NO CONSENSUS: {max_votes}/{len(alive_werewolves)} werewolves agreed")
        else:
            self.state.game_state["attacked_player_id"] = None
            print(f"  - NO VOTES: No valid werewolf votes")

    def _resolve_night_actions(self):
        attacked = self.state.game_state["attacked_player_id"]
        poisoned = self.state.game_state["poisoned_player_id"]
        
        # Debug: Print werewolf attack resolution
        print(f"DEBUG: Werewolf attack resolution:")
        print(f"  - attacked_player_id: {attacked}")
        print(f"  - cure_used: {self.state.game_state['cure_used']}")
        print(f"  - werewolf_votes: {self.state.game_state['werewolf_votes']}")
        print(f"  - alive_werewolves: {[pid for pid in self.state.game_state['alive_player_ids'] if self.player_roles[pid] == WEREWOLF_NAME]}")
        
        # Apply cure if used (prevents werewolf kill)
        if self.state.game_state["cure_used"]:
            print(f"  - Cure was used, preventing werewolf attack on Player {attacked}")
            attacked = None
        
        if attacked is not None:
            print(f"  - Werewolves successfully kill Player {attacked}")
            self._eliminate_player(attacked, "was killed by Werewolves during the night")
        else:
            print(f"  - No werewolf kill this night")
            pass

        if self.state.game_state["poison_used"] and poisoned is not None:
            print(f"  - Witch poisons Player {poisoned}")
            self._eliminate_player(poisoned, "was poisoned by the Witch during the night")

    def _resolve_day_vote(self):
        # Count all day votes
        vote_counts = {}
        for pid, target in self.state.game_state["day_votes"].items():
            vote_counts[target] = vote_counts.get(target, 0) + 1
        
        print(f"DEBUG: Day vote results: {vote_counts}")
        
        if vote_counts:
            # Find the player with the most votes, with random tie-breaker
            max_votes = max(vote_counts.values())
            candidates = [p for p, v in vote_counts.items() if v == max_votes]
            eliminated_player = random.choice(candidates)
            self.state.game_state["voted_player_id"] = eliminated_player
            
            print(f"DEBUG: Player {eliminated_player} eliminated by vote ({max_votes} votes)")
            # Eliminate the player
            self._eliminate_player(eliminated_player, "was eliminated by village vote")
        else:
            self.state.game_state["voted_player_id"] = None
            print(f"DEBUG: No votes cast")
        
    def _reset_round_state(self):
        self.state.game_state["cure_used"] = False
        self.state.game_state["poison_used"] = False
        self.state.game_state["voted_player_id"] = None
        self.state.game_state["attacked_player_id"] = None
        self.state.game_state["werewolf_votes"] = {}
        self.state.game_state["day_votes"] = {}

    def _compute_next_phase(self) -> Phase:
        match self.phase:
            case Phase.WEREWOLF_DISCUSSION:
                return Phase.WEREWOLF_VOTE
            case Phase.WEREWOLF_VOTE:
                return Phase.SEER_REVEAL
            case Phase.SEER_REVEAL:
                return Phase.WITCH_CHOICE
            case Phase.WITCH_CHOICE:
                return Phase.DAY_DISCUSSION
            case Phase.DAY_DISCUSSION:
                return Phase.DAY_VOTE
            case Phase.DAY_VOTE:
                return Phase.WEREWOLF_DISCUSSION

    def _send_phase_prompts(self):
        gs = self.state.game_state
        player_ids = gs["alive_player_ids"]
        self.next_player_ids = []

        match self.phase:

            # Werewolf discussion
            case Phase.WEREWOLF_DISCUSSION:
                message = (
                    "Night has fallen. You are a Werewolf.\n" +
                    "Talk privately with the other Werewolves to decide who to attack tonight.\n" +
                    "Speak naturally like a human would, no more than 5 sentences. Do not vote or use tags in this phase."
                )
                werewolf_ids = [pid for pid in player_ids if self.player_roles[pid] == WEREWOLF_NAME]
                for pid in werewolf_ids:
                    self.state.add_observation(to_id=pid, message=message, observation_type=ta.ObservationType.GAME_MESSAGE)
                self.next_player_ids = werewolf_ids

            # Werewolf vote
            case Phase.WEREWOLF_VOTE:
                message = (
                    "Night action: Werewolves must now choose one living player to eliminate.\n" +
                    "Reply only with your choice in this exact format: <kill>player_id</kill>\n" +
                    "Example: <kill>3</kill>"
                )
                werewolf_ids = [pid for pid in player_ids if self.player_roles[pid] == WEREWOLF_NAME]
                for pid in werewolf_ids:
                    self.state.add_observation(to_id=pid, message=message, observation_type=ta.ObservationType.GAME_MESSAGE)
                self.next_player_ids = werewolf_ids

            # Seer reveal
            case Phase.SEER_REVEAL:
                if SEER_NAME in gs["role_pids"]:
                    seer_pid = gs["role_pids"][SEER_NAME][0]
                    if seer_pid in gs["alive_player_ids"]:
                        message = (
                            "Night action: You are the Seer.\n" +
                            "Choose one living player to reveal their true role.\n" +
                            "Reply only with your choice: <reveal>player_id</reveal>\n" +
                            "Example: <reveal>2</reveal>"
                        )
                        self.state.add_observation(to_id=seer_pid, message=message, observation_type=ta.ObservationType.GAME_MESSAGE)
                        self.next_player_ids = [seer_pid]
                    else:
                        self.next_player_ids = []
                else:
                    self.next_player_ids = []

            # Witch choice
            case Phase.WITCH_CHOICE:
                if WITCH_NAME in gs["role_pids"]:
                    witch_pid = gs["role_pids"][WITCH_NAME][0]
                    if witch_pid in gs["alive_player_ids"]:
                        message = (
                            "Night action: You are the Witch.\n" +
                            "You know who was attacked. Choose one action:\n" +
                            "- Save them: <cure></cure>\n" +
                            "- Poison someone: <poison>player_id</poison>\n" +
                            "- Do nothing: <no_action></no_action>\n" +
                            "Example: <poison>4</poison>"
                        )
                        self.state.add_observation(to_id=witch_pid, message=message, observation_type=ta.ObservationType.GAME_MESSAGE)
                        self.next_player_ids = [witch_pid]
                    else:
                        self.next_player_ids = []
                else:
                    self.next_player_ids = []

            # Day discussion
            case Phase.DAY_DISCUSSION:
                message = (
                    "Day has broken. All players may now speak. All players can see the message you send now.\n" +
                    "Discuss who you think the Werewolves are. Share suspicions or defend yourself.\n" +
                    "Speak naturally like a human would, no more than 5 sentences. Do not vote or use action tags yet"
                )
                self.state.add_observation(to_id=-1, message=message, observation_type=ta.ObservationType.GAME_MESSAGE)
                self.next_player_ids = player_ids.copy()

            # Day vote
            case Phase.DAY_VOTE:
                message = (
                    "Voting time. Choose one player to eliminate.\n" +
                    "Reply only with your vote in this format: <vote>player_id</vote>\n" +  
                    "Example: <vote>5</vote>"
                )
                self.state.add_observation(to_id=-1, message=message, observation_type=ta.ObservationType.GAME_MESSAGE)
                self.next_player_ids = player_ids.copy()

            case _:
                raise RuntimeError("Unknown phase")


    def _eliminate_player(self, pid: int, reason: str):
        if pid in self.state.game_state["alive_player_ids"]:
            self.state.game_state["alive_player_ids"].remove(pid)
            # Add to eliminated players list
            self.state.game_state["eliminated_player_ids"].append(pid)
            # Remove from next_player_ids queue if present
            if hasattr(self, 'next_player_ids') and pid in self.next_player_ids:
                self.next_player_ids.remove(pid)
            print(f"DEBUG: Player {pid} eliminated - {reason}")
            self.state.add_observation(message=f"Player {pid} {reason}.", observation_type=ta.ObservationType.GAME_MESSAGE)
            self._check_win()

    def _check_win(self):
        alive = self.state.game_state["alive_player_ids"]
        werewolves = [p for p in alive if self.player_roles[p] == WEREWOLF_NAME]
        if not werewolves:
            print(f"DEBUG: GAME OVER - Village wins! Werewolves eliminated: {[p for p in self.state.game_state['eliminated_player_ids'] if self.player_roles[p] == WEREWOLF_NAME]}")
            self.state.set_winners(player_ids=alive, reason="All Werewolves were eliminated. Village wins!")
        elif len(werewolves) >= len(alive) / 2:
            print(f"DEBUG: GAME OVER - Werewolves win! Alive werewolves: {werewolves}, Total alive: {len(alive)}")
            self.state.set_winners(player_ids=werewolves, reason="Werewolves reached parity with villagers. Werewolves win!")
