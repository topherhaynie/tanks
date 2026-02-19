# Phase 6: Reinforcement Learning & Self-Play

**Status**: 🚧 IN PROGRESS  
**Framework**: PyTorch  
**Algorithms**: DQN (first) → PPO (second)  
**Training Mode**: Headless (fast) + Visual (debug)

## Overview

Phase 6 adds reinforcement learning capabilities to enable bots to learn optimal tank combat strategies through self-play and competitive co-evolution. Bots will train by playing thousands of matches against themselves and other learning agents, gradually improving their tactics.

## Goals

1. Enable bots to learn through trial and error
2. Develop diverse combat strategies via self-play
3. Support multiple RL algorithms (DQN, PPO)
4. Provide training visualization and metrics
5. Create checkpointing system for iterative improvement
6. Support both discrete and continuous action spaces

## Architecture

### Module Structure

```
src/tanks/
├── training/              # Training environment
│   ├── __init__.py
│   ├── env.py            # Headless training environment
│   ├── episode.py        # Episode management and reset
│   ├── rewards.py        # Reward function definitions
│   └── parallel.py       # Batch environment support
│
├── rl/                   # RL infrastructure
│   ├── __init__.py
│   ├── state.py          # State representation (sensor → tensor)
│   ├── actions.py        # Action space definitions
│   ├── replay_buffer.py  # Experience replay buffer
│   │
│   ├── models/           # Neural network architectures
│   │   ├── __init__.py
│   │   ├── dqn.py       # Deep Q-Network
│   │   ├── ppo.py       # Proximal Policy Optimization
│   │   └── common.py    # Shared network components
│   │
│   ├── trainers/         # Training loops
│   │   ├── __init__.py
│   │   ├── dqn_trainer.py     # DQN training loop
│   │   ├── ppo_trainer.py     # PPO training loop
│   │   ├── self_play.py       # Self-play framework
│   │   └── coach.py           # Competitive co-evolution
│   │
│   └── metrics/          # Metrics and visualization
│       ├── __init__.py
│       ├── tensorboard.py     # TensorBoard logging
│       ├── elo.py            # ELO rating system
│       └── evaluator.py      # Bot evaluation suite
```

## Sub-Phase 6.1: Foundation (Training Environment)

### Objectives
- Create headless game mode (no rendering overhead)
- Implement episode management (reset, initialization)
- Define state representation (sensor data → tensor)
- Define action space (discrete actions for DQN)
- Implement basic reward function

### Components

#### 1. Headless Training Environment (`training/env.py`)

**Purpose**: Run game logic without pygame rendering for maximum training speed.

**Key Features**:
- Inherits from core game logic
- No rendering calls (skip all pygame.draw operations)
- Fast-forward physics (configurable tick rate)
- Episode termination conditions (death, timeout)
- Observation and reward extraction
- Reset functionality

**API**:
```python
class TrainingEnvironment:
    def __init__(self, map_config, bot_count=2, max_steps=3000):
        """Initialize training environment."""
        
    def reset(self) -> dict[str, np.ndarray]:
        """Reset environment and return initial observations."""
        
    def step(self, actions: dict[str, int]) -> tuple[
        dict[str, np.ndarray],  # observations
        dict[str, float],        # rewards
        dict[str, bool],         # dones
        dict[str, dict]         # info
    ]:
        """Execute one step and return results."""
        
    def close(self):
        """Clean up resources."""
```

#### 2. State Representation (`rl/state.py`)

**Purpose**: Convert sensor data into fixed-size neural network input.

**Proposed Vector State** (for DQN):
```python
State Vector (78 dimensions):
  - Self state (7): [x, y, angle, turret_angle, hp, velocity, angular_velocity]
  - Weapon state (5): [bullet_cooldown, missile_cooldown, mine_cooldown, mine_count, ammo_state]
  - Nearest enemy (8): [distance, bearing, angle, hp, velocity, vx, vy, visible]
  - Nearest bullet (5): [distance, bearing, velocity, vx, vy]
  - Nearest mine (3): [distance, bearing, armed]
  - Radar summary (10): [count_N, count_NE, count_E, ..., count_NW, avg_distance, closest_distance]
  - Fog summary (8): [revealed_fraction, center_x, center_y, bounds_min_x, bounds_min_y, bounds_max_x, bounds_max_y, explored_area]
  - Wall proximity (8): [N, NE, E, SE, S, SW, W, NW distances]
  - Recent damage (4): [damage_dealt_1s, damage_taken_1s, shots_fired_1s, hits_1s]
  - Strategic (10): [map_center_distance, edge_distance, enemy_los_count, cover_quality, time_alive, kills, deaths, accuracy, aggression_score, defensive_score]
  - Tactical flags (10): [under_fire, low_hp, enemy_visible, enemy_close, mine_available, missile_available, stuck, cornered, advantageous_position, retreat_needed]
```

**Alternative: CNN State** (for spatial awareness):
- 64x64 grid with channels: [terrain, friendly_units, enemy_units, projectiles, mines]
- More complex but captures spatial relationships

**Initial Implementation**: Vector state (simpler, faster)

#### 3. Action Space (`rl/actions.py`)

**Discrete Action Space** (for DQN):
```python
Actions (12 discrete):
  0: NOOP (no action)
  1: MOVE_FORWARD
  2: MOVE_BACKWARD
  3: TURN_LEFT
  4: TURN_RIGHT
  5: MOVE_FORWARD + TURN_LEFT
  6: MOVE_FORWARD + TURN_RIGHT
  7: MOVE_BACKWARD + TURN_LEFT
  8: MOVE_BACKWARD + TURN_RIGHT
  9: SHOOT (current turret direction)
  10: FIRE_MISSILE
  11: PLACE_MINE
```

**Turret Control**: 
- Option A: Turret auto-aims at nearest enemy (simplifies action space)
- Option B: Separate turret actions TURN_TURRET_LEFT, TURN_TURRET_RIGHT (more control)
- **Proposed**: Auto-aim for DQN, manual for PPO

**Continuous Action Space** (for PPO, future):
```python
Actions (4 continuous floats):
  - move_speed: [-1.0, 1.0] (backward to forward)
  - turn_rate: [-1.0, 1.0] (left to right)
  - turret_angle: [0.0, 2π] (absolute angle or relative)
  - shoot_threshold: [0.0, 1.0] (confidence threshold for shooting)
```

#### 4. Reward Function (`training/rewards.py`)

**Baseline Reward Structure**:
```python
Reward Components:
  Combat:
    +10.0  per bullet hit on enemy
    +15.0  per missile hit on enemy
    +20.0  per mine kill on enemy
    +100.0 per kill
    -100.0 per death
    -5.0   per bullet hit taken
    -10.0  per missile hit taken
    -1.0   per bullet wasted (miss)
    
  Survival:
    +0.1   per second alive
    +50.0  for winning match
    
  Positioning (optional shaping):
    +1.0   for maintaining safe distance (not too close/far)
    +2.0   for good cover position
    +1.0   for facing enemy when enemy visible
    -0.5   for standing still too long (encourage exploration)
    
  Strategic (optional shaping):
    +5.0   for revealing new terrain
    +3.0   for controlling map center
    -2.0   for getting cornered
```

**Configuration**:
- Reward weights should be configurable
- Start with sparse rewards (hits, kills, deaths)
- Add shaping gradually if needed

#### 5. Episode Management (`training/episode.py`)

**Episode Termination**:
- All enemy tanks destroyed (victory)
- Learning bot destroyed (defeat)
- Maximum steps reached (3000 steps = ~100 seconds at 30 Hz)
- Stalemate detection (no action for 1000 steps)

**Episode Reset**:
- Respawn all tanks at spawn points
- Reset HP, ammo, cooldowns
- Clear bullets, missiles, mines
- Reset fog of war memory
- Randomize spawn positions (prevent overfitting)

### Implementation Order

1. **Basic TrainingEnvironment** (headless game loop)
2. **State representation** (vector conversion from sensors)
3. **Action space** (discrete actions + translation to BotAction)
4. **Reward calculator** (track events and compute rewards)
5. **Episode manager** (reset logic and termination)
6. **Unit tests** (verify state/action/reward correctness)

### Success Criteria

- Environment runs at 10x real-time (300 ticks/second)
- State vector correctly represents game state
- Actions correctly control tank behavior
- Rewards align with desired learning objectives
- Episodes reset cleanly without memory leaks

---

## Sub-Phase 6.2: DQN Implementation

### Objectives
- Implement Deep Q-Network architecture
- Create experience replay buffer
- Build DQN training loop with epsilon-greedy exploration
- Add target network with periodic updates
- Implement checkpoint saving/loading

### Components

#### 1. DQN Network (`rl/models/dqn.py`)

**Architecture**:
```python
Input: State vector (78 dimensions)
  ↓
Dense(256) + ReLU + Dropout(0.2)
  ↓
Dense(256) + ReLU + Dropout(0.2)
  ↓
Dense(128) + ReLU
  ↓
Output: Q-values (12 actions)
```

**Enhancements** (optional):
- Dueling DQN: Split into value stream and advantage stream
- Noisy Networks: Learned exploration instead of epsilon-greedy
- Rainbow DQN: Combine multiple improvements

**Initial**: Standard DQN with 3-layer network

#### 2. Experience Replay Buffer (`rl/replay_buffer.py`)

**Purpose**: Store and sample past experiences for training.

**Data Structure**:
```python
Experience = (state, action, reward, next_state, done)
Buffer: Circular buffer with capacity 100,000
Sampling: Uniform random sampling (batch_size=64)
```

**Features**:
- Efficient numpy-based storage
- Fast batch sampling
- Prioritized replay (future enhancement)

#### 3. DQN Trainer (`rl/trainers/dqn_trainer.py`)

**Training Loop**:
```python
for episode in range(num_episodes):
    state = env.reset()
    episode_reward = 0
    
    for step in range(max_steps):
        # Epsilon-greedy action selection
        action = agent.select_action(state, epsilon)
        
        # Execute action
        next_state, reward, done, info = env.step(action)
        
        # Store experience
        replay_buffer.add(state, action, reward, next_state, done)
        
        # Train if enough samples
        if len(replay_buffer) > batch_size:
            batch = replay_buffer.sample(batch_size)
            loss = agent.train_step(batch)
        
        # Update target network periodically
        if step % target_update_freq == 0:
            agent.update_target_network()
        
        state = next_state
        episode_reward += reward
        
        if done:
            break
    
    # Decay epsilon
    epsilon = max(epsilon_min, epsilon * epsilon_decay)
    
    # Log metrics
    log_episode_metrics(episode, episode_reward, epsilon, loss)
```

**Hyperparameters**:
```python
learning_rate: 1e-4
gamma (discount): 0.99
epsilon_start: 1.0
epsilon_end: 0.05
epsilon_decay: 0.995
batch_size: 64
buffer_size: 100,000
target_update_freq: 1000 steps
```

### Implementation Order

1. **DQN network architecture** (forward pass, Q-value computation)
2. **Replay buffer** (add, sample, capacity management)
3. **Training step** (loss calculation, backprop, optimizer)
4. **Epsilon-greedy** (action selection with exploration)
5. **Target network** (copy weights, periodic updates)
6. **Training loop** (episode iteration, logging)
7. **Checkpoint system** (save/load weights)

### Success Criteria

- Network trains without NaN losses
- Epsilon decays smoothly over episodes
- Replay buffer samples correctly
- Target network reduces training instability
- Agent improves over random baseline

---

## Sub-Phase 6.3: Self-Play & Training

### Objectives
- Implement self-play framework (bot vs frozen past versions)
- Add visual training mode (watch bot learn)
- Integrate TensorBoard logging
- Create checkpoint management system
- Enable training resumption from checkpoints

### Components

#### 1. Self-Play Framework (`rl/trainers/self_play.py`)

**Purpose**: Train bot against frozen versions of itself to encourage strategy diversity.

**Algorithm**:
```python
1. Initialize learner bot with random weights
2. Create checkpoint pool (empty initially)
3. For each episode:
    a. Sample opponent:
       - 80% chance: Random checkpoint from pool
       - 20% chance: Current learner (self-mirror)
    b. Run episode (learner vs opponent)
    c. Update learner with gradients
    d. Every N episodes:
       - Evaluate learner vs all checkpoints
       - If win_rate > threshold:
           - Save new checkpoint to pool
           - Keep last K checkpoints (e.g., K=10)
```

**Benefits**:
- Prevents catastrophic forgetting
- Encourages diverse strategies
- Automatic curriculum (plays against progressively better opponents)

#### 2. Visual Training Mode (`training/env.py` extension)

**Purpose**: Watch training progress with optional rendering.

**Features**:
- Toggle rendering on/off during training
- Slow-motion playback (adjustable speed)
- Display current state vector (for debugging)
- Show Q-values for each action
- Highlight chosen action
- Display reward signal in real-time

**Controls**:
- `V`: Toggle visual mode
- `+/-`: Adjust playback speed
- `Q`: Show Q-value overlay
- `R`: Show reward history

#### 3. TensorBoard Integration (`rl/metrics/tensorboard.py`)

**Logged Metrics**:
```python
Episode Metrics:
  - episode_reward (total)
  - episode_length (steps)
  - win_rate (rolling average)
  - kills_per_episode
  - deaths_per_episode
  - accuracy (shots_hit / shots_fired)
  
Training Metrics:
  - loss (TD error)
  - q_value_mean (average Q across actions)
  - q_value_max (highest Q-value)
  - epsilon (exploration rate)
  - learning_rate
  
Combat Metrics:
  - damage_dealt
  - damage_taken
  - k/d_ratio
  - survival_time
  
Exploration Metrics:
  - action_distribution (histogram)
  - state_distribution (coverage)
  - new_terrain_revealed
```

**Visualization**:
- Reward curves (smoothed with window=100)
- Win rate over time
- Q-value evolution
- Action selection frequencies

#### 4. Checkpoint Management (`rl/trainers/checkpoint.py`)

**Structure**:
```python
checkpoint/
├── config.json          # Training configuration
├── best_model.pt        # Best performing model
├── latest_model.pt      # Most recent model
├── checkpoints/         # Periodic snapshots
│   ├── checkpoint_1000.pt
│   ├── checkpoint_2000.pt
│   └── ...
└── opponents/           # Self-play opponent pool
    ├── opponent_v1.pt
    ├── opponent_v2.pt
    └── ...
```

**Checkpoint Contents**:
```python
{
  'episode': 1000,
  'model_state_dict': {...},
  'optimizer_state_dict': {...},
  'epsilon': 0.5,
  'best_reward': 250.0,
  'win_rate': 0.65,
  'training_time': 3600.0,
  'hyperparameters': {...}
}
```

**Auto-save Logic**:
- Save every N episodes (e.g., 100)
- Save when best reward achieved
- Save when win rate improves
- Keep last K checkpoints + best

### Implementation Order

1. **Checkpoint save/load** (serialize model, optimizer, metadata)
2. **Self-play opponent pool** (sampling, evaluation, adding)
3. **TensorBoard logger** (metric recording, scalar/histogram)
4. **Visual training mode** (optional rendering, Q-value display)
5. **Training script** (CLI with arguments for all options)

### Success Criteria

- Self-play shows improvement over 1000 episodes
- TensorBoard displays clear learning curves
- Checkpoints can be loaded and resumed
- Visual mode helps debug training issues
- Win rate increases from 0% to >50% vs first checkpoint

---

## Sub-Phase 6.4: PPO Implementation

### Objectives
- Implement Proximal Policy Optimization algorithm
- Add continuous action space support
- Create actor-critic network architecture
- Implement Generalized Advantage Estimation (GAE)
- Support parallel environment collection

### Components

#### 1. Actor-Critic Network (`rl/models/ppo.py`)

**Architecture**:
```python
Input: State vector (78 dimensions)
  ↓
Shared Feature Extractor:
  Dense(256) + ReLU
  Dense(256) + ReLU
  ↓
Actor Head (Policy):               Critic Head (Value):
  Dense(128) + ReLU                Dense(128) + ReLU
  Dense(action_dim) + Tanh         Dense(1)
  (outputs action means)           (outputs state value)
  
Action distribution:
  - For continuous: Gaussian with learned std
  - For discrete: Softmax over action logits
```

**Features**:
- Shared feature extractor (efficient)
- Separate actor and critic heads
- Output both action distribution and value estimate

#### 2. PPO Trainer (`rl/trainers/ppo_trainer.py`)

**Algorithm**:
```python
1. Collect trajectories using current policy (N steps)
2. Compute advantages using GAE:
   A_t = δ_t + (γλ)δ_{t+1} + (γλ)²δ_{t+2} + ...
   where δ_t = r_t + γV(s_{t+1}) - V(s_t)
3. For K epochs:
   a. Sample mini-batches from trajectories
   b. Compute ratio: r = π_new(a|s) / π_old(a|s)
   c. Compute clipped objective:
      L_CLIP = min(r * A, clip(r, 1-ε, 1+ε) * A)
   d. Compute value loss: L_VF = (V(s) - V_target)²
   e. Compute entropy bonus: H = -Σ π(a|s) log π(a|s)
   f. Update: maximize L_CLIP + c1*L_VF + c2*H
4. Update old policy with new policy
```

**Hyperparameters**:
```python
learning_rate: 3e-4
gamma (discount): 0.99
gae_lambda: 0.95
clip_epsilon: 0.2
value_loss_coef: 0.5
entropy_coef: 0.01
max_grad_norm: 0.5
ppo_epochs: 10
batch_size: 64
n_steps: 2048 (trajectory length)
```

#### 3. Continuous Action Space (`rl/actions.py` extension)

**Continuous Actions** (4 floats):
```python
- move_speed: [-1.0, 1.0]     # -1=full back, 0=stop, 1=full forward
- turn_rate: [-1.0, 1.0]      # -1=full left, 0=straight, 1=full right
- turret_angle_delta: [-1.0, 1.0]  # Relative turret rotation
- shoot_confidence: [0.0, 1.0]     # Threshold for firing
```

**Additional Discrete Actions** (via threshold):
```python
- fire_missile: shoot_confidence > 0.8 and missile_ready
- place_mine: shoot_confidence > 0.9 and mine_ready
```

**Benefits**:
- Smooth, human-like movement
- Precise aiming and positioning
- Better exploration of action space
- More expressive behaviors

#### 4. Parallel Environments (`training/parallel.py`)

**Purpose**: Collect experiences from multiple environments simultaneously.

**Implementation**:
```python
class ParallelEnvironments:
    def __init__(self, env_count=8):
        self.envs = [TrainingEnvironment() for _ in range(env_count)]
    
    def reset(self) -> np.ndarray:
        return np.array([env.reset() for env in self.envs])
    
    def step(self, actions: np.ndarray) -> tuple:
        results = [env.step(a) for env, a in zip(self.envs, actions)]
        states, rewards, dones, infos = zip(*results)
        return np.array(states), np.array(rewards), np.array(dones), infos
```

**Benefits**:
- Faster data collection
- More diverse experiences
- Better sample efficiency
- Reduced correlation in batch

### Implementation Order

1. **Actor-critic network** (policy and value heads)
2. **GAE computation** (advantage estimation)
3. **PPO loss functions** (clipped objective, value, entropy)
4. **Trajectory collection** (rollout storage)
5. **PPO training step** (mini-batch updates, multiple epochs)
6. **Parallel environments** (batch collection)
7. **Continuous action space** (action sampling, log-prob)

### Success Criteria

- PPO converges faster than DQN (fewer episodes)
- Continuous actions enable smoother movement
- Parallel envs increase training throughput 4-8x
- Agent learns complex behaviors (kiting, ambush, retreat)
- Win rate >70% vs DQN agent

---

## Sub-Phase 6.5: Advanced Features

### Objectives
- Implement ELO rating system
- Add competitive co-evolution (multiple bots training)
- Create curriculum learning system
- Build comprehensive evaluation suite
- Enable tournament integration with learned bots

### Components

#### 1. ELO Rating System (`rl/metrics/elo.py`)

**Purpose**: Track relative skill levels of all bots (learning and scripted).

**Algorithm**:
```python
Expected score: E_A = 1 / (1 + 10^((R_B - R_A)/400))
Rating update: R_A' = R_A + K * (S_A - E_A)
  where:
    R_A, R_B = current ratings
    S_A = actual score (1=win, 0.5=draw, 0=loss)
    K = K-factor (32 for new, 16 for established)
```

**Features**:
- Track ELO per bot over training
- Matchmaking based on ELO (face similar-skilled opponents)
- ELO decay for inactive bots
- Leaderboard with confidence intervals

**Initial Ratings**:
- Random bot: 1000
- SimpleBot: 1200
- SmartBot: 1400
- Learning bot: 1000 (will evolve)

#### 2. Competitive Co-Evolution (`rl/trainers/coach.py`)

**Purpose**: Train multiple bots simultaneously in competitive setting.

**Algorithm**:
```python
1. Initialize population of N bots (different random seeds)
2. For each generation:
    a. Round-robin tournament (all bots vs all bots)
    b. Compute ELO ratings
    c. Parallel training:
       - Each bot trains against opponents from pool
       - Prioritize opponents with similar ELO
    d. Evaluate fitness (ELO + diversity metrics)
    e. Optional: Crossover and mutation (genetic algorithm)
    f. Save top K bots as new opponent pool
3. Best bot becomes champion
```

**Benefits**:
- Diverse strategies emerge
- Arms race dynamics (counter-strategies)
- More robust to exploitation
- Prevents overfitting to single opponent

#### 3. Curriculum Learning (`training/curriculum.py`)

**Purpose**: Gradually increase task difficulty as bot improves.

**Stages**:
```python
Stage 1: Basic Combat (episodes 0-500)
  - Small map (20x11)
  - 1v1 vs stationary target
  - Focus: Learn to aim and shoot
  
Stage 2: Simple Movement (episodes 500-1500)
  - Small map
  - 1v1 vs SimpleBot (wander only)
  - Focus: Learn to track and pursue
  
Stage 3: Tactical Combat (episodes 1500-3000)
  - Medium map (40x22)
  - 1v1 vs SmartBot
  - Focus: Learn positioning and cover
  
Stage 4: Advanced Combat (episodes 3000+)
  - Large map (60x34)
  - 1v1 vs checkpoint opponents
  - Focus: Master all weapons and tactics
  
Stage 5: Multi-Combat (episodes 5000+)
  - Large map
  - 1v3 or 2v2 scenarios
  - Focus: Team coordination and multi-target
```

**Progression Criteria**:
- Win rate >70% in current stage → advance
- Win rate <30% in new stage → regress
- Automatic stage adjustment

#### 4. Evaluation Suite (`rl/metrics/evaluator.py`)

**Purpose**: Comprehensive bot assessment beyond win rate.

**Metrics**:
```python
Combat Performance:
  - Win rate vs each opponent type
  - K/D ratio
  - Accuracy (hits / shots)
  - Damage efficiency (damage dealt / damage taken)
  - Average survival time
  
Strategic Performance:
  - Map coverage (exploration)
  - Positioning score (distance to cover)
  - Weapon usage (bullets vs missiles vs mines)
  - Aggression index (time spent pursuing)
  - Defensive index (time spent retreating)
  
Learning Metrics:
  - Sample efficiency (reward per step)
  - Training stability (loss variance)
  - Generalization (performance on new maps)
  - Robustness (performance vs unknown opponents)
```

**Evaluation Protocol**:
1. Freeze trained bot weights
2. Run 100 episodes vs each opponent type
3. Test on 5 different maps (including unseen maps)
4. Aggregate statistics with confidence intervals
5. Generate evaluation report

#### 5. RL Bot Integration (`bots/rl_bot.py`)

**Purpose**: Wrap trained RL models as standard bot controllers.

**Features**:
- Load checkpoint (DQN or PPO)
- Convert BotState → state tensor
- Inference (forward pass, action selection)
- Convert action → BotAction
- Support both discrete and continuous action spaces
- Tournament compatible

**Usage**:
```python
# Create RL bot from checkpoint
rl_bot = RLBot.from_checkpoint("checkpoints/best_model.pt")

# Use in tournament
tournament.add_bot("DQN Champion", rl_bot)
tournament.add_bot("SmartBot", SmartBot())
tournament.run()
```

### Implementation Order

1. **ELO rating system** (update formula, tracking)
2. **Evaluation suite** (metric computation, reporting)
3. **RLBot controller** (checkpoint loading, inference)
4. **Tournament integration** (RL bots in existing tournaments)
5. **Curriculum learning** (stage definitions, progression)
6. **Competitive co-evolution** (population training)

### Success Criteria

- ELO system correctly ranks bot skill levels
- Trained bot defeats SmartBot >80% of matches
- Curriculum accelerates learning vs flat training
- Co-evolution produces diverse strategies
- RL bots seamlessly integrate with tournament system

---

## Training Configuration

### Recommended Training Pipeline

**Phase A: DQN Baseline** (2-4 hours)
```bash
python -m tanks.rl.train \
  --algorithm dqn \
  --episodes 5000 \
  --epsilon-start 1.0 \
  --epsilon-end 0.05 \
  --map-size small \
  --opponent smart_bot \
  --checkpoint-dir checkpoints/dqn_baseline
```

**Phase B: Self-Play DQN** (4-8 hours)
```bash
python -m tanks.rl.train \
  --algorithm dqn \
  --episodes 10000 \
  --self-play \
  --opponent-pool-size 10 \
  --checkpoint-every 100 \
  --load checkpoints/dqn_baseline/best_model.pt
```

**Phase C: PPO with Curriculum** (6-12 hours)
```bash
python -m tanks.rl.train \
  --algorithm ppo \
  --episodes 20000 \
  --curriculum \
  --parallel-envs 8 \
  --checkpoint-dir checkpoints/ppo_curriculum
```

**Phase D: Competitive Co-Evolution** (12-24 hours)
```bash
python -m tanks.rl.train \
  --algorithm ppo \
  --episodes 50000 \
  --co-evolution \
  --population-size 4 \
  --parallel-envs 16 \
  --checkpoint-dir checkpoints/ppo_coevo
```

### Hardware Requirements

**Minimum**:
- CPU: 4 cores (parallel environments)
- RAM: 8 GB
- Training time: 24-48 hours for full pipeline

**Recommended**:
- CPU: 8+ cores
- GPU: NVIDIA GTX 1060 or better (PyTorch CUDA)
- RAM: 16 GB
- Training time: 6-12 hours for full pipeline

**Optimal**:
- CPU: 16+ cores
- GPU: NVIDIA RTX 3060 or better
- RAM: 32 GB
- Training time: 2-4 hours for full pipeline

---

## Success Metrics

### Phase 6 Complete When:

1. **DQN Agent** trains successfully:
   - Beats random bot >95% of matches
   - Beats SmartBot >50% of matches
   - Shows clear learning progress in TensorBoard

2. **PPO Agent** outperforms DQN:
   - Beats DQN agent >70% of matches
   - Beats SmartBot >80% of matches
   - Demonstrates smooth, human-like movement

3. **Self-Play** produces diversity:
   - Multiple distinct strategies observed
   - Performance continues improving over 10K episodes
   - No catastrophic forgetting

4. **System Integration**:
   - RL bots work in tournament mode
   - Checkpoints save/load reliably
   - Training can resume from interruption
   - Visual mode aids debugging

5. **Documentation**:
   - Training guide complete
   - Hyperparameter tuning guide written
   - Evaluation results documented
   - Example trained models provided

---

## Future Enhancements (Phase 7+)

- **Multi-Agent RL**: Team-based strategies, communication
- **Hierarchical RL**: High-level strategy + low-level tactics
- **Model-Based RL**: Learn world model, plan actions
- **Meta-Learning**: Learn to adapt quickly to new opponents
- **Transfer Learning**: Pre-train on simple tasks, fine-tune on complex
- **Adversarial Training**: Robust to worst-case opponents
- **Imitation Learning**: Learn from human gameplay demonstrations
- **Curriculum Generation**: Automatically create training tasks
- **Neural Architecture Search**: Optimize network architecture
- **Distributed Training**: Multi-machine training for faster results

---

## Design Decisions Summary

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| **Framework** | PyTorch | Pythonic, easier debugging, strong ecosystem |
| **Algorithm Priority** | DQN first, then PPO | DQN simpler to debug, PPO better performance |
| **State Representation** | Vector (78-dim) | Simpler than CNN, sufficient for current game |
| **Action Space (DQN)** | Discrete (12 actions) | Natural fit for DQN, easy to interpret |
| **Action Space (PPO)** | Continuous (4 floats) | Smooth movement, better expressiveness |
| **Training Mode** | Headless + Visual toggle | Fast training, visual debugging when needed |
| **Self-Play** | Yes, with checkpoint pool | Prevents forgetting, diverse strategies |
| **Curriculum** | Yes, 5 stages | Accelerates learning, stable convergence |
| **Co-Evolution** | Yes, 4+ bots | Robust strategies, fun to watch |
| **Visualization** | TensorBoard | Industry standard, rich features |

---

## References

- **DQN**: Mnih et al., "Playing Atari with Deep Reinforcement Learning" (2013)
- **PPO**: Schulman et al., "Proximal Policy Optimization Algorithms" (2017)
- **Self-Play**: Silver et al., "Mastering Chess and Shogi by Self-Play" (2017)
- **Curriculum Learning**: Bengio et al., "Curriculum Learning" (2009)
- **GAE**: Schulman et al., "High-Dimensional Continuous Control Using Generalized Advantage Estimation" (2016)
