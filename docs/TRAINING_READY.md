# Phase 6.3 - Training Infrastructure Complete ✅

## What Was Built

### 1. **Metrics Tracking System**
- **TrainingMetrics** dataclass: Captures 20+ metrics per episode
  - Episode: reward, length, win/loss
  - Combat: kills, deaths, damage dealt/taken
  - Accuracy: shooting accuracy, K/D ratio
  - Learning: Q-values, loss, epsilon
  - Exploration: action distribution, terrain revealed
- **MetricsTracker**: Aggregates metrics over time
  - Rolling averages (configurable window, default 100 episodes)
  - Statistics (mean, std, totals)
  - CSV export for analysis
  - Console summaries

### 2. **TensorBoard Integration**
- **TensorBoardLogger**: Real-time visualization
  - 15+ metric types across 6 categories
  - Scalars: reward, loss, win rate, Q-values, epsilon
  - Histograms: action distribution
  - Grouped metrics: combat, accuracy, exploration
  - Automatic logging every episode
  - Manual flush/close for safety

### 3. **Checkpoint Management**
- **CheckpointManager**: Flexible save/load system
  - **Latest checkpoint**: Resume training anytime
  - **Best checkpoint**: Auto-saves when performance improves
  - **Periodic checkpoints**: Saves every N episodes (keeps last 10)
  - **Opponent pool**: Store frozen models for self-play (future)
  - Automatic cleanup (configurable max checkpoints)

### 4. **Training Script (CLI)**
- **train_dqn.py**: Full-featured training pipeline
  - 30+ command-line arguments
  - Training modes: new, resume, evaluate
  - Graceful interrupt (Ctrl+C saves state)
  - Progress logging (configurable interval)
  - Automatic evaluation
  - Device selection (CPU/CUDA/auto)
  - Network architecture (DQN/Dueling)

### 5. **Training Guide**
- **TRAINING_GUIDE.md**: Comprehensive documentation
  - Quick start examples
  - All CLI options explained
  - Checkpoint management guide
  - TensorBoard usage
  - Troubleshooting section
  - Performance expectations
  - Advanced topics (curriculum, hyperparameter search)

## How to Use

### Start Training
```bash
# Basic training (1000 episodes, ~30-60 minutes)
python -m tanks.scripts.train_dqn

# With TensorBoard visualization
python -m tanks.scripts.train_dqn --tensorboard

# Open TensorBoard (in another terminal)
tensorboard --logdir runs/
# Navigate to http://localhost:6006
```

### Monitor Progress
**Console Output:**
```
Episode 100/1000 | Reward: +12.34 ± 5.67 | Win Rate: 15.0% | Epsilon: 0.905 | Buffer: 3,000
Episode 200/1000 | Reward: +25.89 ± 8.23 | Win Rate: 28.0% | Epsilon: 0.819 | Buffer: 6,000
...
```

**TensorBoard Graphs:**
- `episode/reward` - Should increase over time
- `episode/win_rate` - Should improve from 0% toward 50%+
- `training/loss` - Should decrease and stabilize
- `training/epsilon` - Should decay from 1.0 to 0.05
- `training/q_value_mean` - Should increase (agent learning value)
- `actions/distribution` - Should show exploration (not stuck on one action)

### Stop Training
**Press Ctrl+C:**
- Saves latest checkpoint automatically
- Exports metrics to CSV
- Closes TensorBoard logger
- Prints training summary

**Output:**
```
Training interrupted by user

Saving final checkpoint...
Metrics saved to: checkpoints/dqn/training_metrics.csv
TensorBoard logs saved to: runs/dqn

============================================================
Training Summary (last 100 episodes)
============================================================
Total Episodes: 456
Total Steps: 1,234,567
Overall Win Rate: 34.5%

Recent Performance:
  Reward: +45.67 ± 12.34
  Length: 2,345 steps
  Win Rate: 42.0% (42/100)
  Kills/Deaths: 58/58
  K/D Ratio: 1.00
  Accuracy: 23.4%
  Avg Loss: 0.1234
  Avg Q-Value: 12.34
============================================================
```

### Resume Training
```bash
# Continue from where you left off
python -m tanks.scripts.train_dqn --resume

# Resume and train for more episodes
python -m tanks.scripts.train_dqn --resume --episodes 2000
```

### Evaluate Trained Agent
```bash
# Evaluate best model (10 episodes, deterministic)
python -m tanks.scripts.train_dqn --evaluate

# Evaluate specific checkpoint
python -m tanks.scripts.train_dqn --evaluate --checkpoint checkpoints/dqn/episode_500.pt

# More evaluation episodes (100)
python -m tanks.scripts.train_dqn --evaluate --eval-episodes 100
```

**Output:**
```
Running 10 evaluation episodes...
  Episode 1: Reward=+45.67, Length=1234, Result=WIN
  Episode 2: Reward=-12.34, Length=567, Result=LOSS
  ...

======================================================================
Evaluation Results
======================================================================
Episodes: 10
Mean Reward: +34.56 ± 23.45
Mean Length: 1,456 steps
Win Rate: 6/10 (60.0%)
======================================================================
```

## File Locations

### Checkpoints
```
checkpoints/dqn/
├── best_model.pt          # Best model (highest win rate)
├── latest_model.pt        # Most recent (resume here)
├── training_metrics.csv   # Full training history
├── checkpoints/
│   ├── episode_100.pt
│   ├── episode_200.pt
│   └── ...
└── opponents/
    └── (empty until self-play implemented)
```

### TensorBoard Logs
```
runs/dqn/
└── events.out.tfevents.* # TensorBoard event files
```

### Training Data
```
checkpoints/dqn/training_metrics.csv
```
Columns: episode, reward, length, loss, epsilon, won, win_rate, kills, deaths, damage_dealt, damage_taken, shots_fired, shots_hit, accuracy, kd_ratio, survival_time, q_value_mean, q_value_max, terrain_revealed

## Custom Training

### Adjust Hyperparameters
```bash
python -m tanks.scripts.train_dqn \
    --episodes 5000 \
    --learning-rate 5e-5 \
    --epsilon-decay 0.999 \
    --batch-size 128 \
    --buffer-size 200000 \
    --tensorboard
```

### Use Dueling DQN
```bash
python -m tanks.scripts.train_dqn \
    --network-type dueling \
    --episodes 1000 \
    --tensorboard
```

### Fast Training (Large Batches)
```bash
python -m tanks.scripts.train_dqn \
    --episodes 10000 \
    --batch-size 256 \
    --buffer-size 500000 \
    --save-interval 200
```

### Debug Training (Frequent Saves)
```bash
python -m tanks.scripts.train_dqn \
    --episodes 100 \
    --save-interval 10 \
    --log-interval 1 \
    --tensorboard
```

## Using Trained Agents

### In Python
```python
from tanks.rl.models import DQNAgent
from tanks.bots import RLBot

# Load trained agent
agent = DQNAgent.load("checkpoints/dqn/best_model.pt")

# Wrap as Bot
bot = RLBot(agent)

# Use in game (same interface as SimpleBot, SmartBot, etc.)
action = bot.update(bot_state)
```

### In Demo Mode
Edit `src/tanks/demo.py` to add:
```python
from tanks.rl.models import DQNAgent
from tanks.bots import RLBot

# Load trained agent
agent = DQNAgent.load("checkpoints/dqn/best_model.pt")
rl_bot = RLBot(agent)

# Add to game
tank_rl = Tank(x, y, angle=0, team=1)
tank_rl.controller = BotController(rl_bot, tank_rl)
```

## Next Steps

### When You're Ready to Train

1. **Start a Training Run:**
   ```bash
   python -m tanks.scripts.train_dqn --episodes 1000 --tensorboard
   ```

2. **Open TensorBoard:**
   ```bash
   tensorboard --logdir runs/
   ```
   Navigate to http://localhost:6006

3. **Let it Run:**
   - Training 1000 episodes takes ~30-60 minutes (depends on hardware)
   - Monitor TensorBoard graphs for learning progress
   - Check console for periodic updates

4. **Stop When Satisfied:**
   - Press Ctrl+C when win rate plateaus or improves sufficiently
   - Training automatically saves checkpoint

5. **Evaluate:**
   ```bash
   python -m tanks.scripts.train_dqn --evaluate
   ```

6. **Use in Game:**
   - Load agent with `DQNAgent.load()`
   - Wrap with `RLBot(agent)`
   - Add to demo mode or tournament

### What's Ready Now

- ✅ **All training infrastructure** (metrics, logging, checkpoints)
- ✅ **CLI script** (start, stop, resume, evaluate)
- ✅ **TensorBoard integration** (real-time visualization)
- ✅ **Documentation** (comprehensive guide)
- ✅ **Linting passed** (all code clean)

### What's Next (If You Want)

- **Phase 6.4**: PPO implementation (continuous actions, actor-critic)
- **Phase 6.5**: Advanced features (ELO ratings, co-evolution, self-play)
- **Actual Training**: Run the scripts and train an agent!

## Summary

You now have a **production-ready RL training system** with:

- 📊 **Comprehensive metrics** (20+ per episode)
- 📈 **TensorBoard visualization** (15+ metric types)
- 💾 **Smart checkpointing** (best/latest/periodic)
- 🖥️ **User-friendly CLI** (30+ options)
- 📖 **Complete documentation** (guide + troubleshooting)

**No training has been run yet** - you control when to start! The system is ready and waiting for your command.

See `docs/TRAINING_GUIDE.md` for full documentation.
