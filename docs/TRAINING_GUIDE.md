# DQN Training Guide

This guide explains how to train, evaluate, and manage DQN agents for the Tanks game.

## Quick Start

### Start Training
```bash
# Basic training (1000 episodes)
python -m tanks.scripts.train_dqn

# Training with TensorBoard visualization
python -m tanks.scripts.train_dqn --tensorboard

# View TensorBoard (in another terminal)
tensorboard --logdir runs/
```

### Resume Training
```bash
# Resume from latest checkpoint
python -m tanks.scripts.train_dqn --resume

# Continue for more episodes
python -m tanks.scripts.train_dqn --resume --episodes 2000
```

### Evaluate Agent
```bash
# Evaluate best model
python -m tanks.scripts.train_dqn --evaluate

# Evaluate specific checkpoint
python -m tanks.scripts.train_dqn --evaluate --checkpoint checkpoints/dqn/episode_1000.pt
```

## Training Modes

### Standard Training
Train a DQN agent against a static opponent or random policy:
```bash
python -m tanks.scripts.train_dqn \
    --episodes 1000 \
    --learning-rate 1e-4 \
    --batch-size 64 \
    --tensorboard
```

### Self-Play Training
Train with gradually improving opponents (future feature):
```bash
python -m tanks.scripts.train_dqn \
    --episodes 5000 \
    --self-play \
    --opponent-prob 0.8 \
    --max-opponents 10
```

### Fast Training
High-throughput training without rendering:
```bash
python -m tanks.scripts.train_dqn \
    --episodes 10000 \
    --batch-size 128 \
    --buffer-size 200000
```

### Debug Training
Small-scale training with frequent checkpoints:
```bash
python -m tanks.scripts.train_dqn \
    --episodes 100 \
    --save-interval 10 \
    --log-interval 1
```

## Command-Line Options

### Training Parameters
| Option | Default | Description |
|--------|---------|-------------|
| `--episodes` | 1000 | Number of training episodes |
| `--max-steps` | 3000 | Maximum steps per episode (~100s) |
| `--batch-size` | 64 | Training batch size |
| `--buffer-size` | 100,000 | Replay buffer capacity |
| `--learning-rate` | 1e-4 | Adam learning rate |
| `--gamma` | 0.99 | Discount factor for rewards |
| `--warmup-steps` | 1000 | Random exploration before training |

### Exploration
| Option | Default | Description |
|--------|---------|-------------|
| `--epsilon-start` | 1.0 | Initial exploration rate |
| `--epsilon-end` | 0.05 | Minimum exploration rate |
| `--epsilon-decay` | 0.995 | Decay per episode |

Epsilon Schedule:
- Episode 0: ε = 1.0 (full exploration)
- Episode 138: ε = 0.5 (50% exploration)
- Episode 598: ε = 0.05 (5% exploration, then stays)

### Network Architecture
| Option | Default | Description |
|--------|---------|-------------|
| `--network-type` | dqn | Architecture: `dqn` or `dueling` |
| `--device` | auto | Device: `cpu`, `cuda`, or `auto` |
| `--target-update-freq` | 1000 | Steps between target network updates |

### Checkpointing
| Option | Default | Description |
|--------|---------|-------------|
| `--checkpoint-dir` | checkpoints/dqn | Checkpoint directory |
| `--save-interval` | 100 | Episodes between saves |
| `--max-checkpoints` | 10 | Maximum periodic checkpoints to keep |
| `--resume` | - | Resume from latest checkpoint |
| `--checkpoint` | - | Load specific checkpoint |

### Logging
| Option | Default | Description |
|--------|---------|-------------|
| `--tensorboard` | off | Enable TensorBoard logging |
| `--log-dir` | runs/dqn | TensorBoard log directory |
| `--log-interval` | 10 | Episodes between progress logs |
| `--eval-interval` | 100 | Episodes between evaluations |
| `--eval-episodes` | 10 | Number of evaluation episodes |

## Checkpoint Management

### Directory Structure
```
checkpoints/dqn/
├── best_model.pt        # Best performing model (highest win rate)
├── latest_model.pt      # Most recent model (for resuming)
├── training_metrics.csv # Full training history
├── checkpoints/         # Periodic snapshots
│   ├── episode_100.pt
│   ├── episode_200.pt
│   └── ...
└── opponents/           # Self-play opponent pool (future)
    ├── opponent_v1.pt
    └── ...
```

### Checkpoint Contents
Each checkpoint contains:
- Model weights (policy network + target network)
- Optimizer state (Adam momentum)
- Training progress (episode number, steps)
- Hyperparameters (epsilon, learning rate, etc.)
- Performance metrics (best reward, win rate)

### Loading Checkpoints
```python
# In Python
from tanks.rl.models import DQNAgent

# Load best model
agent = DQNAgent.load("checkpoints/dqn/best_model.pt")

# Load specific checkpoint
agent = DQNAgent.load("checkpoints/dqn/episode_500.pt")

# Use in game
from tanks.bots import RLBot

bot = RLBot(agent)
```

## TensorBoard Visualization

### Starting TensorBoard
```bash
# Start TensorBoard server
tensorboard --logdir runs/

# Open browser to http://localhost:6006
```

### Available Metrics

#### Episode Metrics
- `episode/reward` - Total episode reward (primary metric)
- `episode/length` - Steps per episode
- `episode/win_rate` - Win/loss outcome (1.0 = win, 0.0 = loss)

#### Training Metrics
- `training/loss` - TD error (should decrease over time)
- `training/epsilon` - Exploration rate (decays to 0.05)
- `training/q_value_mean` - Average Q-value (should increase)
- `training/q_value_max` - Maximum Q-value

#### Combat Metrics
- `combat/kills` - Enemy tanks destroyed
- `combat/deaths` - Times agent was destroyed
- `combat/damage_dealt` - Total damage inflicted
- `combat/damage_taken` - Total damage received

#### Accuracy Metrics
- `accuracy/shooting` - Hit rate (shots_hit / shots_fired)
- `accuracy/kd_ratio` - Kill/Death ratio

#### Exploration Metrics
- `actions/distribution` - Histogram of actions taken
- `exploration/terrain_revealed` - Fog tiles explored

### Interpreting Graphs

**Good Training**:
- Reward increases over episodes
- Win rate improves from 0% to >50%
- Loss decreases and stabilizes
- Q-values increase steadily
- Action distribution balances (not all one action)

**Bad Training**:
- Reward flatlines or decreases
- Win rate stays near 0%
- Loss explodes (NaN values)
- Q-values don't increase
- Agent stuck on one action (explore/exploit imbalance)

## Training Workflow

### 1. Start Training
```bash
python -m tanks.scripts.train_dqn \
    --episodes 1000 \
    --tensorboard \
    --save-interval 100
```

### 2. Monitor Progress
- Watch console output for reward trends
- Open TensorBoard to see live graphs
- Check checkpoints directory for saved models

### 3. Stop Training (Ctrl+C)
Training gracefully saves:
- Latest checkpoint (for resuming)
- Metrics CSV (for analysis)
- TensorBoard logs (for visualization)

### 4. Resume Training
```bash
python -m tanks.scripts.train_dqn --resume --episodes 2000
```

### 5. Evaluate Best Model
```bash
python -m tanks.scripts.train_dqn --evaluate
```

### 6. Use in Game
```python
from tanks.bots import RLBot
from tanks.rl.models import DQNAgent

# Load trained agent
agent = DQNAgent.load("checkpoints/dqn/best_model.pt")

# Create bot
bot = RLBot(agent)

# Use in demo mode (see demo.py)
```

## Troubleshooting

### Training is Slow
- Reduce `--max-steps` (e.g., 1500 instead of 3000)
- Increase `--batch-size` (64 → 128)
- Use `--device cuda` if GPU available
- Reduce `--buffer-size` (100k → 50k)

### Agent Not Learning
- Check TensorBoard: Is loss decreasing?
- Check Q-values: Are they increasing?
- Increase `--warmup-steps` (1000 → 5000)
- Adjust `--learning-rate` (try 5e-5 or 5e-4)
- Check action distribution: Is agent exploring?

### Loss Explodes (NaN)
- Reduce `--learning-rate` (1e-4 → 1e-5)
- Use `--network-type dueling` (more stable)
- Check reward scale (should be -10 to +100 range)
- Gradient clipping is enabled (should prevent this)

### Win Rate Stuck at 0%
- Train longer (1000 → 5000 episodes)
- Check opponent difficulty (is it too hard?)
- Verify reward signal (positive for good actions?)
- Try different hyperparameters

### Out of Memory
- Reduce `--buffer-size` (100k → 50k)
- Reduce `--batch-size` (64 → 32)
- Use `--device cpu` (slower but less memory)

## Performance Expectations

### Episode 0-200 (Warmup & Random)
- Win Rate: ~0-10%
- Reward: Highly variable
- Agent explores randomly, no clear strategy

### Episode 200-500 (Learning Basics)
- Win Rate: ~10-30%
- Reward: Starting to increase
- Agent learns to shoot, avoid bullets

### Episode 500-1000 (Strategy Development)
- Win Rate: ~30-60%
- Reward: Steadily increasing
- Agent learns positioning, timing

### Episode 1000+ (Refinement)
- Win Rate: ~60-80%
- Reward: High and stable
- Agent has coherent strategy

## Next Steps

After training a DQN agent:

1. **Evaluate Performance**: Test against different opponents
2. **Analyze Metrics**: Review TensorBoard graphs and CSV data
3. **Tournament Mode**: Compete against other bots
4. **Try Different Architectures**: Dueling DQN, PPO
5. **Self-Play**: Train against own checkpoints (Phase 6.3 feature)
6. **Hyperparameter Tuning**: Experiment with learning rates, epsilons

## Advanced Topics

### Curriculum Learning
Start with easier opponents, gradually increase difficulty:
```bash
# Phase 1: Train vs random (episodes 0-500)
python -m tanks.scripts.train_dqn --episodes 500

# Phase 2: Train vs SimpleBot (episodes 500-1500)
python -m tanks.scripts.train_dqn --resume --episodes 1000 # (configure opponent)

# Phase 3: Train vs SmartBot (episodes 1500-3000)
python -m tanks.scripts.train_dqn --resume --episodes 1500 # (configure opponent)
```

### Hyperparameter Search
Grid search key hyperparameters:
- Learning rate: [1e-5, 5e-5, 1e-4, 5e-4]
- Target update frequency: [500, 1000, 2000]
- Batch size: [32, 64, 128]
- Epsilon decay: [0.99, 0.995, 0.999]

### Multi-Agent Training (Future)
Train multiple agents simultaneously:
```bash
# Agent 1: Aggressive (high reward for kills)
# Agent 2: Defensive (high reward for survival)
# Agent 3: Balanced (standard rewards)
```

## References

- DQN Paper: https://arxiv.org/abs/1312.5602
- Dueling DQN: https://arxiv.org/abs/1511.06581
- PyTorch Documentation: https://pytorch.org/docs/
- TensorBoard Guide: https://www.tensorflow.org/tensorboard
