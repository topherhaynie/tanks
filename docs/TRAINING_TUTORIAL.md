# Training Your First RL Tank Agents

**Welcome!** This tutorial will teach you how to train intelligent tank agents using two different reinforcement learning algorithms: **DQN** and **PPO**.

By the end of this tutorial, you'll understand:
- How DQN and PPO work (in simple terms)
- How to train both algorithms from scratch
- How to monitor training progress with TensorBoard
- How to evaluate and deploy your trained agents
- When to use DQN vs PPO

**Time investment**: 2-3 hours for complete walkthrough  
**Prerequisites**: Python 3.12+, PyTorch 2.10+, 5-10 GB free disk space

---

## Part 1: Understanding the Algorithms

### What is Reinforcement Learning?

Imagine teaching a dog a trick:
1. **Dog tries something** (action)
2. **You give a treat or nothing** (reward)
3. **Dog learns what works** (policy)

RL agents work the same way:
1. **Agent observes the game** (state)
2. **Agent chooses an action** (move, shoot, turn)
3. **Agent gets a reward** (hit enemy: +10, got hit: -5)
4. **Agent learns to maximize rewards** (get better at combat)

### DQN (Deep Q-Network)

**What it does**: Learns to predict "how good is each action right now?"

**How it works**:
```
State → Neural Network → Q-values for each action → Pick best action
Example: [shoot: 8.5, move_forward: 3.2, turn_left: -1.0] → SHOOT!
```

**Key features**:
- **Discrete actions**: Choose from 12 specific commands
- **Experience replay**: Remembers past experiences and learns from them
- **Target network**: Uses a stable copy for learning stability
- **Epsilon-greedy**: Sometimes explores random actions

**Best for**:
- Beginners (simpler to understand)
- When you need specific commands (e.g., "place mine HERE")
- When training data is limited

### PPO (Proximal Policy Optimization)

**What it does**: Learns a policy that smoothly controls all actions simultaneously

**How it works**:
```
State → Neural Network → Action probabilities → Sample smooth actions
Example: [move: 0.8, turn: -0.3, turret: 0.5, shoot: 0.9] → Smooth movement!
```

**Key features**:
- **Continuous actions**: Fine-grained control (like joystick)
- **On-policy**: Learns from current behavior only
- **GAE**: Smart advantage calculation for better credit assignment
- **Clipped updates**: Prevents destructive policy changes

**Best for**:
- Advanced users
- When you want smooth, natural movement
- When you have lots of training time
- Often achieves better final performance

---

## Part 2: Your First DQN Training Session

### Step 1: Start Training

Open a terminal in the tanks directory and run:

```bash
python -m tanks.scripts.train_dqn --episodes 1000 --tensorboard
```

**What happens:**
- Agent starts with **random actions** (epsilon=1.0)
- Every episode, agent fights an opponent
- Agent gradually learns which actions lead to rewards
- Exploration decreases over time (epsilon → 0.05)

**Initial output:**
```
============================================================
🎮 Training DQN Agent
============================================================
State dim: 78
Action space: Discrete (12 actions)
Map: small_arena
Max episode steps: 3000
============================================================

🚀 Starting training for 1000 episodes
   Batch size: 64
   Buffer size: 100000
   Press Ctrl+C to stop and save

Episode 10/1000
============================================================
📈 Episode Return: -52.30
⏱️  Episode Length: 145.0
💥 Damage Dealt: 0.0
🎯 Hit Rate: 0.0%
🔍 Epsilon: 0.99
📊 Loss: 0.0000
============================================================
```

**What you'll see:**
- **First 100 episodes**: Negative returns, 0% hit rate (random exploration)
- **Episodes 100-300**: Starting to hit enemies, returns improving
- **Episodes 300-500**: Consistent positive returns, learning combat
- **Episodes 500+**: Tactical behavior emerging

### Step 2: Monitor with TensorBoard

In a **new terminal**, start TensorBoard:

```bash
tensorboard --logdir runs/dqn
```

Open your browser to: `http://localhost:6006`

**Key metrics to watch:**

1. **Episode Return** (Scalars → Episode/return)
   - Starts negative (-50 to -100)
   - Goal: Positive and increasing (50+)
   - Good agent: 100+ consistently

2. **Hit Rate** (Scalars → Combat/hit_rate)
   - Starts at 0%
   - Goal: 20-30% for competent agent
   - Expert: 40%+

3. **Loss** (Scalars → Training/loss)
   - High at start (lots to learn)
   - Should stabilize below 1.0
   - Spiky = still learning

4. **Epsilon** (Scalars → Exploration/epsilon)
   - Starts at 1.0 (100% random)
   - Decays to 0.05 (5% random)
   - Watch behavior change as it decays!

### Step 3: Watch Your Agent Improve

DQN trains **headless** (no graphics) for speed. To see it in action:

**Option A: Manually enable rendering**

Stop training (Ctrl+C), then edit the training call:
```bash
python -m tanks.scripts.train_dqn --episodes 100 --tensorboard --render
```

**Option B: Evaluate checkpoint**

```bash
# This will render the agent playing
python -m tanks.scripts.train_dqn --evaluate --eval-episodes 5
```

**What to look for:**
- **Early training**: Agent moves erratically, shoots randomly, hits walls
- **Mid training**: Agent avoids walls, occasionally hits enemy
- **Late training**: Agent uses cover, predicts enemy movement, aims carefully

### Step 4: Understanding Training Progress

**Episode 0-50: Random Chaos**
```
Return: -80   Hit Rate: 0%   Deaths: 1.0
```
Agent doesn't know anything. Moves randomly, dies quickly.

**Episode 50-200: Basic Survival**
```
Return: -20   Hit Rate: 5%   Deaths: 0.8
```
Agent learns to avoid walls, shoots in enemy direction sometimes.

**Episode 200-500: Combat Competence**
```
Return: 40    Hit Rate: 20%   Deaths: 0.5
```
Agent consistently hits enemies, uses basic tactics, survives longer.

**Episode 500+: Tactical Mastery**
```
Return: 120   Hit Rate: 35%   Deaths: 0.3
```
Agent uses cover, predicts movement, controls engagement range.

### Step 5: Resume Training

Training was interrupted? No problem:

```bash
python -m tanks.scripts.train_dqn --resume --episodes 500
```

This loads the latest checkpoint and continues training!

### Step 6: Hyperparameter Tuning (Advanced)

Want to experiment? Try these variations:

**Faster exploration decay:**
```bash
python -m tanks.scripts.train_dqn \
  --episodes 1000 \
  --epsilon-decay 0.998 \
  --tensorboard
```

**Larger batch for stability:**
```bash
python -m tanks.scripts.train_dqn \
  --episodes 1000 \
  --batch-size 128 \
  --tensorboard
```

**More frequent updates:**
```bash
python -m tanks.scripts.train_dqn \
  --episodes 1000 \
  --batch-size 64 \
  --train-frequency 2 \
  --tensorboard
```

---

## Part 3: Your First PPO Training Session

### Step 1: Start Training

PPO uses **rollouts** instead of episodes. Each rollout collects 2048 steps across multiple episodes:

```bash
python -m tanks.scripts.train_ppo --rollouts 100 --tensorboard
```

**Initial output:**
```
============================================================
🎮 Training PPO Agent
============================================================
State dim: 78
Action space: Continuous (4D)
Map: small_arena
Max episode steps: 3000
============================================================

🚀 Starting training for 100 rollouts
   Each rollout collects 2048 steps
   Training for 10 epochs per rollout
   Mini-batch size: 64
   Press Ctrl+C to stop and save

Rollout 5/100
============================================================
📈 Episode Return: -45.20
⏱️  Episode Length: 230.5
💥 Damage Dealt: 12.5
🎯 Hit Rate: 8.5%
🔄 Policy Loss: 0.2145
💎 Value Loss: 0.8932
🎲 Entropy: 5.2341
============================================================
```

### Step 2: Understanding PPO Output

PPO has different metrics than DQN:

**Policy Loss**: How much policy is changing
- High early (0.5+) = lots of learning
- Stabilizes (0.1-0.3) = good convergence
- Near zero = policy might be stuck

**Value Loss**: How accurate is the critic
- Decreases as critic learns to predict returns
- Target: Below 1.0

**Entropy**: How much exploration
- High (5+) = diverse actions
- Decreases over time as policy becomes confident
- Too low (<2) = might be stuck in local optimum

**Clip Fraction**: How often PPO clips updates
- 0.0 = no clipping (policy stable)
- 0.2+ = lots of clipping (large updates)
- Goal: Decreases over time

### Step 3: Monitor with TensorBoard

```bash
tensorboard --logdir runs/ppo
```

**PPO-specific metrics:**

1. **Entropy** (Scalars → Training/entropy)
   - Starts high (5-7)
   - Gradually decreases (2-4)
   - Monitor: Too low = overfitted

2. **Clip Fraction** (Scalars → Training/clip_fraction)
   - High early (0.2-0.4)
   - Decreases as policy stabilizes
   - Spikes = policy making big changes

3. **Value Loss** (Scalars → Training/value_loss)
   - Shows critic learning
   - Should decrease steadily
   - Target: <1.0

### Step 4: PPO Training Timeline

**Rollout 0-10: Exploration Phase**
```
Return: -60   Hit Rate: 3%   Entropy: 6.5
```
Agent explores diverse actions, mostly bad outcomes.

**Rollout 10-30: Initial Learning**
```
Return: -10   Hit Rate: 10%   Entropy: 5.5
```
Agent learns basic movement, occasional hits.

**Rollout 30-60: Competence Building**
```
Return: 50    Hit Rate: 22%   Entropy: 4.0
```
Smooth movement, consistent combat, tactical awareness.

**Rollout 60+: Refinement**
```
Return: 140   Hit Rate: 38%   Entropy: 3.0
```
Advanced tactics, precise aiming, strategic positioning.

### Step 5: Comparing PPO to DQN

After training both, compare performance:

**Evaluate DQN:**
```bash
python -m tanks.scripts.train_dqn --evaluate --eval-episodes 10
```

**Evaluate PPO:**
```bash
python -m tanks.scripts.train_ppo --evaluate --eval-episodes 10
```

**What you'll notice:**

| Aspect | DQN | PPO |
|--------|-----|-----|
| Movement | Discrete, choppy | Smooth, continuous |
| Aiming | Snaps to angles | Fluid tracking |
| Training time | Faster (1-2 hrs) | Slower (3-5 hrs) |
| Final performance | Good | Often better |
| Sample efficiency | Higher | Lower |

---

## Part 4: Advanced Training Techniques

### Self-Play Training

Instead of fighting SmartBot, fight past versions of yourself:

**DQN self-play:**
```bash
python -m tanks.scripts.train_dqn \
  --episodes 2000 \
  --opponent-pool-size 10 \
  --save-interval 50 \
  --tensorboard
```

**What happens:**
- Every 50 episodes, saves checkpoint to opponent pool
- Randomly selects opponents from pool
- Forces continued improvement (arms race!)

### Curriculum Learning

Start easy, get progressively harder:

**Stage 1: Beat RandomBot (easy)**
```bash
python -m tanks.scripts.train_dqn --episodes 300 --opponent random
```

**Stage 2: Beat SimpleBot (medium)**
```bash
python -m tanks.scripts.train_dqn --resume --episodes 500 --opponent simple
```

**Stage 3: Beat SmartBot (hard)**
```bash
python -m tanks.scripts.train_dqn --resume --episodes 500 --opponent smart
```

### Hyperparameter Search

Try different configurations:

**DQN variations:**
```bash
# Conservative (stable but slow)
python -m tanks.scripts.train_dqn --lr 1e-4 --gamma 0.995 --episodes 1000

# Aggressive (fast but risky)
python -m tanks.scripts.train_dqn --lr 5e-4 --gamma 0.98 --episodes 1000

# Dueling network
python -m tanks.scripts.train_dqn --network-type dueling --episodes 1000
```

**PPO variations:**
```bash
# More exploration
python -m tanks.scripts.train_ppo --entropy-coef 0.02 --rollouts 100

# Larger rollouts
python -m tanks.scripts.train_ppo --n-steps 4096 --rollouts 100

# More training per rollout
python -m tanks.scripts.train_ppo --n-epochs 15 --rollouts 100
```

---

## Part 5: Troubleshooting

### Problem: Agent Isn't Learning

**Symptoms:**
- Return stays negative after 200+ episodes/rollouts
- Hit rate stays at 0%
- Loss is NaN or exploding

**Solutions:**

1. **Check learning rate** (might be too high):
   ```bash
   python -m tanks.scripts.train_dqn --lr 1e-4 --episodes 500
   ```

2. **Verify GPU isn't causing issues**:
   ```bash
   python -m tanks.scripts.train_dqn --device cpu --episodes 100
   ```

3. **Increase exploration** (DQN):
   ```bash
   python -m tanks.scripts.train_dqn --epsilon-decay 0.999 --episodes 1000
   ```

4. **Increase exploration** (PPO):
   ```bash
   python -m tanks.scripts.train_ppo --entropy-coef 0.03 --rollouts 100
   ```

### Problem: Training is Unstable

**Symptoms:**
- Return oscillates wildly
- Performance gets worse after improving
- Metrics spike unexpectedly

**Solutions (DQN):**
```bash
# Larger batch, slower learning
python -m tanks.scripts.train_dqn \
  --batch-size 128 \
  --lr 1e-4 \
  --target-update-freq 1000 \
  --episodes 1000
```

**Solutions (PPO):**
```bash
# Smaller policy updates
python -m tanks.scripts.train_ppo \
  --clip-epsilon 0.1 \
  --lr 1e-4 \
  --max-grad-norm 0.5 \
  --rollouts 100
```

### Problem: Agent Gets Stuck in Local Optimum

**Symptoms:**
- Return plateaus early (e.g., 30-40)
- Agent repeats same strategy
- Entropy too low (<2.0 for PPO)

**Solutions:**

1. **Restart with more exploration**:
   ```bash
   # DQN: Higher epsilon
   python -m tanks.scripts.train_dqn --epsilon-min 0.1 --episodes 1000
   
   # PPO: Higher entropy
   python -m tanks.scripts.train_ppo --entropy-coef 0.05 --rollouts 100
   ```

2. **Use opponent pool for diversity**:
   ```bash
   python -m tanks.scripts.train_dqn \
     --opponent-pool-size 10 \
     --save-interval 50 \
     --episodes 2000
   ```

3. **Curriculum learning** (explicit):
   - Train against RandomBot for 200 episodes
   - Resume against SimpleBot for 300 episodes
   - Resume against SmartBot for 500 episodes

### Problem: Training is Too Slow

**Symptoms:**
- Taking hours per 100 episodes/rollouts
- GPU not being utilized

**Solutions:**

1. **Verify GPU usage**:
   ```bash
   # Check if CUDA is available
   python -c "import torch; print(torch.cuda.is_available())"
   ```

2. **Reduce rendering overhead**:
   ```bash
   # Never render during training
   python -m tanks.scripts.train_dqn --episodes 1000 --render-interval 9999
   ```

3. **Larger batches** (better GPU utilization):
   ```bash
   python -m tanks.scripts.train_dqn --batch-size 256 --episodes 1000
   ```

4. **For PPO, increase rollout size**:
   ```bash
   python -m tanks.scripts.train_ppo --n-steps 4096 --rollouts 100
   ```

---

## Part 6: Deploying Your Trained Agent

### Test Against Built-in Bots

Once trained, test your agent in bot demo mode:

**Edit `demo.py` to add your trained agent:**

```python
# At the top, import RLBot
from tanks.bots.rl_bot import RLBot
from tanks.rl.models import DQNAgent

# In the demo mode setup, load your agent
trained_agent = DQNAgent.load("checkpoints/best_model.pt")
rl_bot = RLBot(agent=trained_agent, name="MyTrainedAgent")

# Add to bot list
bots = [rl_bot, smart_bot]
```

Then run:
```bash
python -m tanks.demo
```

### Tournament Integration

Your trained agents automatically work with the tournament system:

```python
from tanks.modes.tournament import Tournament
from tanks.bots.rl_bot import RLBot
from tanks.rl.models import DQNAgent, PPOAgent

# Load trained agents
dqn_agent = DQNAgent.load("checkpoints/dqn/best_model.pt")
ppo_agent = PPOAgent.load("checkpoints/ppo/best_model.pt")

# Create RL bots
dqn_bot = RLBot(agent=dqn_agent, name="DQN_Champion")
ppo_bot = RLBot(agent=ppo_agent, name="PPO_Master")

# Run tournament
tournament = Tournament(bots=[dqn_bot, ppo_bot, smart_bot, simple_bot])
tournament.run()
```

### Sharing Checkpoints

Trained agents are just checkpoint files! Share them:

```bash
# Your checkpoint is here:
checkpoints/best_model.pt

# Share with friends:
# They just need to load it:
agent = DQNAgent.load("path/to/your/checkpoint.pt")
```

---

## Part 7: Next Steps & Advanced Topics

### What You've Learned

✅ How to train DQN agents (discrete actions)  
✅ How to train PPO agents (continuous actions)  
✅ How to monitor training with TensorBoard  
✅ How to evaluate and deploy trained agents  
✅ How to troubleshoot common issues  

### Advanced Topics (Phase 6.5 - Coming Soon)

**ELO Rating System**
- Track agent skill levels
- Matchmake opponents by strength
- Build competitive ladders

**Self-Play Framework**
- Automatic opponent pool management
- Version freezing and thawing
- Diversity metrics

**Co-Evolution**
- Multiple agents training simultaneously
- Competitive dynamics
- Strategic diversity emergence

**Advanced Architectures**
- LSTM for memory (remember enemy patterns)
- Attention mechanisms (focus on threats)
- Transformer-based agents

### Experiment Ideas

1. **Train on different maps** - Does agent generalize?
2. **Try longer episodes** - `--max-steps 5000`
3. **Multi-agent self-play** - Train population of agents
4. **Reward shaping** - Modify reward function in `src/tanks/rl/rewards.py`
5. **Ensemble agents** - Use 3 networks, vote on actions

### Community & Support

**Questions?**
- Check `docs/TRAINING_GUIDE.md` for detailed reference
- Review `docs/Project Plans/07_Phase6_Reinforcement_Learning.md` for architecture details
- Inspect agent code in `src/tanks/rl/`

**Want to contribute?**
- Share your trained checkpoints
- Submit new reward functions
- Propose architecture improvements
- Add new opponent bots

---

## Summary

**DQN** is your go-to for:
- First RL project
- Discrete control
- Sample efficiency
- Quick experiments

**PPO** is your choice for:
- Smooth, natural control
- Final performance
- Continuous domains
- Production deployments

**Both** are production-ready and await your training!

Now go train some intelligent tanks! 🎮🤖

---

**Quick Reference:**

```bash
# DQN: Basic training
python -m tanks.scripts.train_dqn --episodes 1000 --tensorboard

# PPO: Basic training
python -m tanks.scripts.train_ppo --rollouts 100 --tensorboard

# TensorBoard
tensorboard --logdir runs/

# Evaluate
python -m tanks.scripts.train_dqn --evaluate
python -m tanks.scripts.train_ppo --evaluate

# Resume
python -m tanks.scripts.train_dqn --resume --episodes 500
python -m tanks.scripts.train_ppo --resume --rollouts 50
```

Happy training! 🚀
