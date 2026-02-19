"""PPO training loop with rollout collection and GAE.

This module implements the training pipeline for PPO agents, including
trajectory collection, advantage estimation, and multi-epoch training.
"""

from typing import TYPE_CHECKING

import numpy as np

from tanks.rl.checkpoint import CheckpointManager
from tanks.rl.metrics import MetricsTracker, TensorBoardLogger, TrainingMetrics
from tanks.rl.models.agent import PPOAgent
from tanks.training.env import TrainingEnvironment

if TYPE_CHECKING:
    pass


class RolloutBuffer:
    """Buffer for storing trajectory data for PPO.
    
    Stores states, actions, rewards, values, log_probs for a full rollout,
    then computes advantages using GAE.
    
    Args:
        state_dim: Dimension of state vectors.
        action_dim: Number of continuous actions.
        max_size: Maximum rollout length.
    """
    
    def __init__(self, state_dim: int, action_dim: int, max_size: int = 2048) -> None:
        """Initialize rollout buffer."""
        self.max_size = max_size
        self.state_dim = state_dim
        self.action_dim = action_dim
        
        # Storage
        self.states = np.zeros((max_size, state_dim), dtype=np.float32)
        self.actions = np.zeros((max_size, action_dim), dtype=np.float32)
        self.rewards = np.zeros(max_size, dtype=np.float32)
        self.values = np.zeros(max_size, dtype=np.float32)
        self.log_probs = np.zeros(max_size, dtype=np.float32)
        self.dones = np.zeros(max_size, dtype=bool)
        
        self.ptr = 0
        self.size = 0
    
    def add(
        self,
        state: np.ndarray,
        action: np.ndarray,
        reward: float,
        value: float,
        log_prob: float,
        done: bool,
    ) -> None:
        """Add experience to buffer.
        
        Args:
            state: State vector.
            action: Action taken.
            reward: Reward received.
            value: Value estimate.
            log_prob: Log probability of action.
            done: Whether episode ended.
        """
        self.states[self.ptr] = state
        self.actions[self.ptr] = action
        self.rewards[self.ptr] = reward
        self.values[self.ptr] = value
        self.log_probs[self.ptr] = log_prob
        self.dones[self.ptr] = done
        
        self.ptr += 1
        self.size = min(self.size + 1, self.max_size)
    
    def get(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Get all data from buffer.
        
        Returns:
            Tuple of (states, actions, rewards, values, log_probs, dones).
        """
        return (
            self.states[: self.size],
            self.actions[: self.size],
            self.rewards[: self.size],
            self.values[: self.size],
            self.log_probs[: self.size],
            self.dones[: self.size],
        )
    
    def clear(self) -> None:
        """Clear buffer for next rollout."""
        self.ptr = 0
        self.size = 0


class PPOTrainer:
    """PPO training coordinator.
    
    Manages rollout collection, advantage computation, and multi-epoch training.
    
    Args:
        env: Training environment.
        agent: PPO agent to train.
        n_steps: Steps per rollout. Default: 2048.
        batch_size: Mini-batch size for training. Default: 64.
        n_epochs: Epochs per rollout. Default: 10.
        checkpoint_dir: Directory to save checkpoints. Default: "checkpoints/ppo".
        log_interval: Episodes between logging. Default: 10.
    """
    
    def __init__(
        self,
        env: TrainingEnvironment,
        agent: PPOAgent,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        checkpoint_dir: str = "checkpoints/ppo",
        log_interval: int = 10,
    ) -> None:
        """Initialize PPO trainer."""
        self.env = env
        self.agent = agent
        self.n_steps = n_steps
        self.batch_size = batch_size
        self.n_epochs = n_epochs
        self.log_interval = log_interval
        
        # Create rollout buffer
        self.rollout_buffer = RolloutBuffer(
            state_dim=agent.state_dim,
            action_dim=agent.action_dim,
            max_size=n_steps,
        )
        
        # Checkpoint and metrics
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        self.metrics_tracker = MetricsTracker(save_dir=checkpoint_dir)
        
        # Training stats
        self.total_steps = 0
        self.total_episodes = 0
    
    def collect_rollout(self) -> dict:
        """Collect one rollout of experiences.
        
        Returns:
            Dictionary with rollout statistics.
        """
        self.rollout_buffer.clear()
        
        state = self.env.reset()
        episode_rewards = []
        episode_lengths = []
        current_episode_reward = 0.0
        current_episode_length = 0
        
        for step in range(self.n_steps):
            # Get action from policy
            action, log_prob, value = self.agent.get_action(state, deterministic=False)
            
            # Execute action
            next_state, reward, done, info = self.env.step(action)
            
            # Store transition
            self.rollout_buffer.add(state, action, reward, value, log_prob, done)
            
            current_episode_reward += reward
            current_episode_length += 1
            self.total_steps += 1
            
            if done:
                episode_rewards.append(current_episode_reward)
                episode_lengths.append(current_episode_length)
                current_episode_reward = 0.0
                current_episode_length = 0
                self.total_episodes += 1
                state = self.env.reset()
            else:
                state = next_state
        
        # Get value of final state for GAE computation
        _, _, next_value = self.agent.get_action(state, deterministic=False)
        
        return {
            "episode_rewards": episode_rewards,
            "episode_lengths": episode_lengths,
            "next_value": next_value,
            "total_steps": self.total_steps,
        }
    
    def train(
        self,
        num_rollouts: int,
        tb_logger: TensorBoardLogger | None = None,
        save_interval: int = 100,
    ) -> None:
        """Train agent for specified number of rollouts.
        
        Args:
            num_rollouts: Number of rollouts to collect and train on.
            tb_logger: Optional TensorBoard logger.
            save_interval: Rollouts between checkpoint saves.
        """
        print(f"Starting PPO training for {num_rollouts} rollouts...")
        print(f"Device: {self.agent.device}")
        print(f"Steps per rollout: {self.n_steps}")
        print(f"Batch size: {self.batch_size}")
        print(f"Epochs per rollout: {self.n_epochs}")
        print()
        
        for rollout in range(num_rollouts):
            # Collect rollout
            rollout_stats = self.collect_rollout()
            
            # Get rollout data
            states, actions, rewards, values, log_probs, dones = self.rollout_buffer.get()
            
            # Compute advantages using GAE
            advantages, returns = self.agent.compute_gae(
                rewards, values, dones, rollout_stats["next_value"]
            )
            
            # Train for multiple epochs
            total_losses = {
                "total_loss": 0.0,
                "policy_loss": 0.0,
                "value_loss": 0.0,
                "entropy_loss": 0.0,
            }
            n_updates = 0
            
            for epoch in range(self.n_epochs):
                # Generate random mini-batches
                indices = np.arange(len(states))
                np.random.shuffle(indices)
                
                for start in range(0, len(states), self.batch_size):
                    end = start + self.batch_size
                    batch_indices = indices[start:end]
                    
                    # Train on mini-batch
                    losses = self.agent.train_step(
                        states[batch_indices],
                        actions[batch_indices],
                        log_probs[batch_indices],
                        advantages[batch_indices],
                        returns[batch_indices],
                    )
                    
                    # Accumulate losses
                    for key, value in losses.items():
                        total_losses[key] += value
                    n_updates += 1
            
            # Average losses
            avg_losses = {k: v / n_updates for k, v in total_losses.items()}
            
            # Log episode metrics
            for ep_reward, ep_length in zip(rollout_stats["episode_rewards"],
                                           rollout_stats["episode_lengths"],
                                           strict=False):
                metrics = TrainingMetrics(
                    episode=self.total_episodes,
                    reward=ep_reward,
                    length=ep_length,
                    loss=avg_losses["total_loss"],
                )
                self.metrics_tracker.add(metrics)
                
                if tb_logger:
                    tb_logger.log_episode(metrics, self.total_episodes)
            
            # Log progress
            if (rollout + 1) % self.log_interval == 0 or len(rollout_stats["episode_rewards"]) > 0:
                stats = self.metrics_tracker.get_stats()
                print(
                    f"Rollout {rollout + 1}/{num_rollouts} | "
                    f"Steps: {self.total_steps:,} | "
                    f"Episodes: {self.total_episodes} | "
                    f"Reward: {stats.get('mean_reward', 0.0):+.2f} | "
                    f"Loss: {avg_losses['total_loss']:.4f}"
                )
            
            # Save checkpoints
            if (rollout + 1) % save_interval == 0:
                self.checkpoint_manager.save_checkpoint(self.agent, rollout + 1)
                self.checkpoint_manager.save_latest(self.agent, rollout + 1)
                
                # Check for best model
                win_rate = self.metrics_tracker.get_rolling_avg("win_rate", window=100)
                mean_reward = self.metrics_tracker.get_rolling_avg("reward", window=100)
                self.checkpoint_manager.save_best(self.agent, rollout + 1, mean_reward, win_rate)
            
            # Flush TensorBoard
            if tb_logger and (rollout + 1) % 10 == 0:
                tb_logger.flush()
        
        # Final save
        self.checkpoint_manager.save_latest(self.agent, num_rollouts)
        self.metrics_tracker.save_csv()
        
        print("\nTraining complete!")
        self.metrics_tracker.print_summary()
    
    def evaluate(self, num_episodes: int = 10, max_steps: int = 3000) -> dict:
        """Evaluate agent performance.
        
        Args:
            num_episodes: Number of evaluation episodes.
            max_steps: Maximum steps per episode.
        
        Returns:
            Dictionary of evaluation metrics.
        """
        print(f"Evaluating agent for {num_episodes} episodes...")
        
        rewards = []
        lengths = []
        wins = 0
        
        for episode in range(num_episodes):
            state = self.env.reset()
            episode_reward = 0.0
            
            for step in range(max_steps):
                action, _, _ = self.agent.get_action(state, deterministic=True)
                next_state, reward, done, info = self.env.step(action)
                episode_reward += reward
                state = next_state
                
                if done:
                    break
            
            rewards.append(episode_reward)
            lengths.append(step + 1)
            if info.get("won", False):
                wins += 1
            
            print(
                f"  Episode {episode + 1}: "
                f"Reward={episode_reward:+.2f}, "
                f"Length={step + 1}, "
                f"Result={'WIN' if info.get('won', False) else 'LOSS'}"
            )
        
        # Summary
        print("\n" + "=" * 70)
        print("Evaluation Results")
        print("=" * 70)
        print(f"Episodes: {num_episodes}")
        print(f"Mean Reward: {np.mean(rewards):+.2f} ± {np.std(rewards):.2f}")
        print(f"Mean Length: {np.mean(lengths):.0f} steps")
        print(f"Win Rate: {wins}/{num_episodes} ({wins / num_episodes:.1%})")
        print("=" * 70)
        
        return {
            "mean_reward": float(np.mean(rewards)),
            "std_reward": float(np.std(rewards)),
            "mean_length": float(np.mean(lengths)),
            "win_rate": wins / num_episodes,
        }
