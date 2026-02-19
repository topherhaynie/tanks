# Training Regime Guide

Complete guide to training RL agents using the comprehensive training regime.

## Overview

The training regime consists of **3 phases** designed to progress from basic skills to expert-level combat using **self-play**:

1. **Phase A: Map-Specific Curriculum** - Learn fundamental skills (SmartBot guidance → self-play)
2. **Phase B: Random Map Generalization** - Pure self-play on diverse maps
3. **Phase C: Survival Training** - Self-play survival in outnumbered scenarios (1v2, 1v3)

**Philosophy**: The regime relies heavily on **self-play** (agent vs previous versions of itself) rather than coded bots. This produces more capable agents that learn from evolving opponents.

## Why Self-Play?

**Self-play advantages:**
- **Evolving difficulty**: Opponents improve as the agent improves (co-evolution)
- **No skill ceiling**: Unlike coded bots, self-play opponents can become arbitrarily skilled
- **Diverse strategies**: Different opponent snapshots exhibit varied learned behaviors
- **Realistic**: Best training for competitive scenarios (tournaments, PvP)

**When coded bots are used:**
- **Phase A, Stages 1-2**: SmartBot provides basic combat foundations
- **Benchmarking**: Use SmartBot to evaluate trained agent performance

## Quick Start

```bash
# Train DQN agent through full regime (recommended for beginners)
python -m tanks.scripts.train_regime --agent dqn

# Train PPO agent through full regime
python -m tanks.scripts.train_regime --agent ppo

# Quick test run (~1 hour)
python -m tanks.scripts.train_regime --agent dqn --episodes-per-stage 50 --phase-b-episodes 100 --phase-c-episodes 50
```

## Phase Breakdown

### Phase A: Map-Specific Curriculum (6 stages, ~900 episodes)

Each stage uses a specialized map to teach specific skills. **First 2 stages use SmartBot for basic skill building**, then switches to **self-play** for advanced tactics:

1. **Close Combat Arena** (30x17 tiles, dense obstacles)
   - Skills: Corner fighting, ricochet shots, obstacle usage
   - Opponent: **SmartBot** (foundational skills)
   - Goal: 70% win rate

2. **Open Arena** (50x28 tiles, minimal obstacles)
   - Skills: Long-range combat, positioning, evasion
   - Opponent: **SmartBot** (foundational skills)
   - Goal: 70% win rate

3. **Maze Arena** (40x23 tiles, complex corridors)
   - Skills: Navigation, radar usage, ambush tactics
   - Opponent: **Self-play** (opponent pool)
   - Goal: 65% win rate

4. **Rooms & Corridors** (45x25 tiles, connected rooms)
   - Skills: Door control, choke points, room clearing
   - Opponent: **Self-play** (opponent pool)
   - Goal: 65% win rate

5. **Fortress Assault** (50x28 tiles, central fortress)
   - Skills: Siege tactics, defensive positioning
   - Opponent: **Self-play** (opponent pool)
   - Goal: 60% win rate

6. **Mixed Tactics** (40x23 tiles, varied terrain)
   - Skills: Adaptability, general combat
   - Opponent: **Self-play** (opponent pool)
   - Goal: 75% win rate

### Phase B: Random Map Self-Play (~500 episodes)

**Purpose**: Generalize skills to unseen environments using **pure self-play**

**Features**:
- New random map every episode
- Size: 30-60 tiles (varied)
- Obstacle density: 10-35% (varied)
- Patterns: All 6 types mixed
- Opponents: **100% self-play** (past agent versions from opponent pool)

**Benefits**:
- Prevents overfitting to specific maps
- Trains adaptability
- Agent pool diversity (15 opponent snapshots)
- Opponents evolve with the agent (co-evolution)

**Why self-play?**: Agent learns from competent, evolving opponents rather than static coded bots. This produces more robust strategies.

### Phase C: Survival Training (3 stages, ~600 episodes)

**Purpose**: Learn defensive tactics when outnumbered using **self-play opponents**

1. **Close Quarters Survival (1v2)** (~200 episodes)
   - Map: 35x20 tiles, scattered obstacles
   - Opponents: **2 self-play agents** (from opponent pool)
   - Goal: 30% win rate OR 45s+ survival

2. **Tactical Survival (1v2)** (~200 episodes)
   - Map: 50x28 tiles, corridors
   - Opponents: **2 self-play agents** (from opponent pool)
   - Goal: 25% win rate OR 45s+ survival

3. **Extreme Survival (1v3)** (~200 episodes)
   - Map: 60x34 tiles, maze
   - Opponents: **3 self-play agents** (from opponent pool)
   - Goal: 20% win rate OR 45s+ survival

**Why self-play?**: Learning to survive against multiple competent, coordinated opponents (previous versions of yourself) teaches better defensive tactics than fighting coded bots.

## Addressing "Circling" Problem

The regime includes **boosted exploration rewards** to prevent agents from circling aimlessly:

### Default Reward Weights

```python
exploration_weight = 8.0  # Reward for revealing new terrain
standing_still_penalty = -1.0  # Penalty for not moving
```

### If Agent Still Circles:

```bash
# Increase exploration weight
python -m tanks.scripts.train_regime --agent dqn --exploration-weight 12.0

# Even more aggressive exploration
python -m tanks.scripts.train_regime --agent dqn --exploration-weight 15.0
```

### Fine-Tuning Map Sizes

If the arena is too small/large:

```python
# Edit src/tanks/training/map_specs.py
CLOSE_COMBAT_SPEC = TrainingMapSpec(
    config=GeneratorConfig(
        width=35,  # Increase from 30 if too small
        height=20,  # Increase from 17 if too small
        obstacle_density=0.30,  # Adjust 0.20-0.40
    ),
)
```

**Rule of thumb**:
- **Too small** (<25x15): Agent finds enemy too fast, doesn't learn exploration
- **Too large** (>70x40): Training slows down, agent gets lost
- **Sweet spot**: 30-60 tiles wide, 0.15-0.35 density

## Command Line Options

### Basic Usage

```bash
# Full regime with defaults
python -m tanks.scripts.train_regime --agent dqn

# Skip survival phase (faster training)
python -m tanks.scripts.train_regime --agent dqn --skip-phase-c

# Custom episode counts
python -m tanks.scripts.train_regime --agent dqn \
  --episodes-per-stage 200 \
  --phase-b-episodes 800 \
  --phase-c-episodes 300
```

### Using Config File

```bash
# Create config file (see example_regime_config.json)
python -m tanks.scripts.train_regime --agent dqn --config my_config.json
```

### Resume Training

```bash
# Resume from checkpoint
python -m tanks.scripts.train_regime --agent dqn \
  --resume checkpoints/regime/phase_a/checkpoints/latest_model.pt
```

### Advanced Tuning

```bash
# DQN hyperparameters
python -m tanks.scripts.train_regime --agent dqn \
  --dqn-lr 5e-4 \
  --dqn-epsilon-decay 100000 \
  --exploration-weight 10.0

# PPO hyperparameters
python -m tanks.scripts.train_regime --agent ppo \
  --ppo-lr 1e-3 \
  --ppo-clip 0.3 \
  --exploration-weight 10.0
```

## Expected Training Times

**Hardware**: 8-core CPU, 16GB RAM, RTX 3060 GPU

| Configuration | Phase A | Phase B | Phase C | Total |
|---------------|---------|---------|---------|-------|
| Quick Test | 1 hour | 30 min | 1 hour | **2.5 hours** |
| Default | 3 hours | 2 hours | 3 hours | **8 hours** |
| Full Training | 6 hours | 4 hours | 6 hours | **16 hours** |

**Note**: Times assume ~10 episodes/minute. Varies by hardware and agent type.

## Monitoring Training

### Progress Tracking

Training automatically displays:
- Real-time win rates
- Average rewards
- Survival times (Phase C)
- ELO ratings
- Opponent pool size

### Checkpoints

Checkpoints saved to `checkpoints/regime/`:
```
checkpoints/regime/
├── phase_a/
│   ├── checkpoints/
│   │   ├── episode_150.pt
│   │   ├── episode_300.pt
│   │   └── latest_model.pt
│   └── phase_a_results.json
├── phase_b/
│   ├── checkpoints/
│   └── opponents/  # Self-play opponent pool
└── phase_c/
    ├── checkpoints/
    └── phase_c_results.json
```

### Results Files

- `phase_X_results.json` - Detailed metrics per phase
- `final_report.txt` - Summary of entire regime
- `elo/ratings.json` - ELO ratings history

## Troubleshooting

### Problem: Agent Circles Without Engaging

**Solutions**:
1. Increase exploration weight: `--exploration-weight 12.0`
2. Reduce map size in `map_specs.py`
3. Check if SmartBot opponent is moving (run bot demo to verify)

### Problem: Agent Not Reaching Win Rate Thresholds

**Solutions**:
1. Increase episodes per stage: `--episodes-per-stage 250`
2. Lower advancement thresholds in `map_specs.py`:
   ```python
   success_threshold=0.65  # Down from 0.70
   ```
3. Verify reward calculator is working (check logs for positive rewards)

### Problem: Training Too Slow

**Solutions**:
1. Use quick test config: `--episodes-per-stage 50`
2. Skip Phase C: `--skip-phase-c`
3. Reduce Phase B episodes: `--phase-b-episodes 200`
4. Use GPU if available (automatic detection)

### Problem: Agent Overfits to One Map Type

**Indicator**: Phase A works great, Phase B win rate drops below 40%

**Solutions**:
1. Increase Phase B episodes: `--phase-b-episodes 1000`
2. Reduce Phase A per-stage episodes: `--episodes-per-stage 100`
3. Enable more aggressive random map variation

### Problem: Arena Too Small/Large

**Map Size Guidelines**:

| Scenario | Recommended Size | Density |
|----------|------------------|---------|
| Close Combat | 25-35 tiles | 0.30-0.40 |
| Open Arena | 45-60 tiles | 0.05-0.15 |
| Maze | 35-45 tiles | 0.35-0.45 |
| Survival 1v2 | 40-50 tiles | 0.20-0.30 |
| Survival 1v3 | 50-70 tiles | 0.25-0.35 |

**Edit** `src/tanks/training/map_specs.py` and adjust `width`, `height`, and `obstacle_density`.

## Advanced Customization

### Creating Custom Map Specs

```python
# In src/tanks/training/map_specs.py

CUSTOM_SPEC = TrainingMapSpec(
    name="My Custom Arena",
    description="Custom training scenario",
    config=GeneratorConfig(
        width=40,
        height=23,
        pattern=TerrainPattern.SCATTERED,
        obstacle_density=0.25,
        border_walls=True,
        num_spawn_points=4,
        symmetry=True,
    ),
    recommended_opponent="smart",
    success_threshold=0.70,
    min_episodes=150,
)

# Add to curriculum
STANDARD_CURRICULUM.append(CUSTOM_SPEC)
```

### Custom Reward Weights

```python
# In orchestrator or training script

weights = RewardWeights(
    kill=150.0,  # Increase for more aggressive play
    death=-150.0,  # Increase penalty for risky play
    survival_per_second=0.3,  # Encourage longer survival
    new_terrain_revealed=12.0,  # Strong exploration
    bullet_wasted=-2.0,  # Penalize missed shots
)
```

### Adjusting Curriculum Thresholds

```python
# In src/tanks/training/map_specs.py

# Make easier
CLOSE_COMBAT_SPEC.success_threshold = 0.60  # Down from 0.70

# Make harder
MIXED_SPEC.success_threshold = 0.85  # Up from 0.75

# Require more episodes
MAZE_SPEC.min_episodes = 200  # Up from 150
```

## Best Practices

1. **Start with Default Settings** - Run full regime once before tuning
2. **Monitor Exploration** - Check that `new_terrain_revealed` reward is positive
3. **Save Checkpoints Frequently** - Use `--save-interval 25` for experimentation
4. **Test Between Phases** - Run bot demo to verify agent is improving
5. **Compare Algorithms** - Train both DQN and PPO, compare results
6. **Use ELO Ratings** - Track relative skill levels over time

## Example Training Sessions

### Beginner: Quick Test

```bash
python -m tanks.scripts.train_regime --agent dqn \
  --episodes-per-stage 50 \
  --phase-b-episodes 100 \
  --phase-c-episodes 50 \
  --exploration-weight 10.0
```

**Duration**: ~2 hours  
**Goal**: Verify training pipeline works

### Intermediate: Balanced Training

```bash
python -m tanks.scripts.train_regime --agent dqn \
  --episodes-per-stage 150 \
  --phase-b-episodes 500 \
  --phase-c-episodes 200 \
  --exploration-weight 8.0
```

**Duration**: ~8 hours  
**Goal**: Competent agent, good vs bots

### Advanced: Full Professional Training

```bash
python -m tanks.scripts.train_regime --agent ppo \
  --episodes-per-stage 300 \
  --phase-b-episodes 1000 \
  --phase-c-episodes 400 \
  --exploration-weight 8.0 \
  --ppo-lr 3e-4
```

**Duration**: ~16 hours  
**Goal**: Expert-level agent, competes with trained humans

## Post-Training

### Deploy Agent

```bash
# Test against bots
python -m tanks  # Select "Player vs Bot", use trained agent

# Run benchmark
python -m tanks.scripts.benchmark --agent checkpoints/regime/best_model.pt
```

### Continue Training

```bash
# Resume for more Phase C episodes
python -m tanks.scripts.train_regime --agent dqn \
  --resume checkpoints/regime/phase_c/checkpoints/latest_model.pt \
  --skip-phase-a \
  --skip-phase-b \
  --phase-c-episodes 500
```

### Export for Deployment

```bash
# Save best model
cp checkpoints/regime/best_model.pt deployed_agent.pt

# Test in production
python -m tanks.scripts.eval --agent deployed_agent.pt --opponents 100
```

## FAQ

**Q: Which agent type is better, DQN or PPO?**

A: PPO generally trains faster and is more stable. DQN can reach higher skill ceiling with proper tuning. Try both!

**Q: How do I know if my agent is exploring properly?**

A: Check the logs for `new_terrain_revealed` rewards. Should see positive values (~5-10) frequently. If always 0, increase exploration weight.

**Q: Can I train on multiple GPUs?**

A: Currently single-GPU only. Multi-GPU support planned for future.

**Q: Should I use symmetry on training maps?**

A: Yes for fairness, no for diversity. Phase A uses symmetry (fair), Phase B random (diverse).

**Q: My agent keeps dying immediately in Phase C. Normal?**

A: Yes! 1v3 is extremely hard. Success = 20% win rate OR 45s+ survival. Focus on survival time first.

**Q: Can I change opponents mid-training?**

A: Yes, edit `map_specs.py` and change `recommended_opponent` field. Options: "simple", "smart", or implement custom bot.

---

**Training regime designed and documented - Ready to produce expert-level agents! 🚀**
