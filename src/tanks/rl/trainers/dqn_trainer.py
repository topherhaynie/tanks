"""DQN training loop with epsilon-greedy exploration.

This module implements the training pipeline for DQN agents, including
episode iteration, experience collection, batch training, and logging.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from tanks.rl.models.agent import DQNAgent
from tanks.rl.replay_buffer import ReplayBuffer
from tanks.training.env import TrainingEnvironment
from tanks.training.episode import Episode, EpisodeManager

if TYPE_CHECKING:
    pass


class DQNTrainer:
    """DQN training coordinator.
    
    Manages the training loop for DQN agents, including:
    - Experience collection from environment
    - Replay buffer management
    - Training step execution
    - Target network updates
    - Epsilon decay
    - Checkpoint saving
    - Metrics logging
    
    Args:
        env: Training environment.
        agent: DQN agent to train.
        buffer_size: Replay buffer capacity. Default: 100,000.
        batch_size: Training batch size. Default: 64.
        target_update_freq: Steps between target network updates. Default: 1000.
        checkpoint_dir: Directory to save checkpoints. Default: "checkpoints".
        log_interval: Episodes between logging. Default: 10.
    """
    
    def __init__(
        self,
        env: TrainingEnvironment,
        agent: DQNAgent,
        buffer_size: int = 100_000,
        batch_size: int = 64,
        target_update_freq: int = 1000,
        checkpoint_dir: str = "checkpoints",
        log_interval: int = 10,
    ) -> None:
        """Initialize DQN trainer."""
        self.env = env
        self.agent = agent
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.checkpoint_dir = Path(checkpoint_dir)
        self.log_interval = log_interval
        
        # Create replay buffer
        self.replay_buffer = ReplayBuffer(
            capacity=buffer_size,
            state_dim=agent.state_dim,
        )
        
        # Training stats
        self.total_steps = 0
        self.episode_rewards: list[float] = []
        self.episode_lengths: list[int] = []
        self.losses: list[float] = []
        
        # Create checkpoint directory
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def train(
        self,
        num_episodes: int,
        max_steps_per_episode: int = 3000,
        warmup_steps: int = 1000,
        save_interval: int = 100,
    ) -> dict[str, list[float]]:
        """Train agent for specified number of episodes.
        
        Args:
            num_episodes: Number of episodes to train.
            max_steps_per_episode: Maximum steps per episode. Default: 3000.
            warmup_steps: Steps of random exploration before training. Default: 1000.
            save_interval: Episodes between checkpoint saves. Default: 100.
        
        Returns:
            Dictionary of training metrics (episode_rewards, episode_lengths, losses, epsilons).
        """
        print(f"Starting DQN training for {num_episodes} episodes...")
        print(f"Device: {self.agent.device}")
        print(f"Warmup steps: {warmup_steps}")
        print(f"Replay buffer size: {len(self.replay_buffer)} / {self.replay_buffer.capacity}")
        print()
        
        epsilons = []
        
        for episode in range(num_episodes):
            episode_data = self._run_episode(
                max_steps=max_steps_per_episode,
                warmup=(self.total_steps < warmup_steps),
            )
            
            # Decay epsilon after episode
            self.agent.decay_epsilon()
            
            # Store metrics
            self.episode_rewards.append(episode_data.total_reward)
            self.episode_lengths.append(episode_data.steps)
            epsilons.append(self.agent.epsilon)
            
            # Log progress
            if (episode + 1) % self.log_interval == 0:
                self._log_progress(episode + 1, num_episodes)
            
            # Save checkpoint
            if (episode + 1) % save_interval == 0:
                checkpoint_path = self.checkpoint_dir / f"dqn_episode_{episode + 1}.pt"
                self.agent.save(str(checkpoint_path))
                print(f"Checkpoint saved: {checkpoint_path}")
        
        # Final checkpoint
        final_path = self.checkpoint_dir / "dqn_final.pt"
        self.agent.save(str(final_path))
        print(f"\nTraining complete! Final checkpoint: {final_path}")
        
        return {
            "episode_rewards": self.episode_rewards,
            "episode_lengths": self.episode_lengths,
            "losses": self.losses,
            "epsilons": epsilons,
        }
    
    def _run_episode(
        self,
        max_steps: int,
        warmup: bool = False,
    ) -> Episode:
        """Run one training episode.
        
        Args:
            max_steps: Maximum steps in episode.
            warmup: If True, use random actions (no training).
        
        Returns:
            Episode data.
        """
        state = self.env.reset()
        episode_reward = 0.0
        episode_loss = 0.0
        loss_count = 0
        
        for step in range(max_steps):
            # Select action (random during warmup)
            if warmup:
                action = int(np.random.randint(0, self.agent.action_dim))
            else:
                action = self.agent.select_action(state)
            
            # Execute action
            next_state, reward, done, info = self.env.step(action)
            episode_reward += reward
            
            # Store experience
            self.replay_buffer.add(state, action, reward, next_state, done)
            
            # Train if enough experiences collected
            if not warmup and len(self.replay_buffer) >= self.batch_size:
                loss = self._train_step()
                episode_loss += loss
                loss_count += 1
            
            # Update target network periodically
            if self.total_steps % self.target_update_freq == 0:
                self.agent.update_target_network()
            
            state = next_state
            self.total_steps += 1
            
            if done:
                break
        
        # Store average loss
        if loss_count > 0:
            self.losses.append(episode_loss / loss_count)
        
        return Episode(
            episode_id=len(self.episode_rewards),
            steps=step + 1,
            total_reward=episode_reward,
            final_result="victory" if info.get("won", False) else "defeat",
            metadata=info,
        )
    
    def _train_step(self) -> float:
        """Perform one training step.
        
        Returns:
            Training loss.
        """
        # Sample batch from replay buffer
        states, actions, rewards, next_states, dones = self.replay_buffer.sample(
            self.batch_size
        )
        
        # Train agent
        loss = self.agent.train_step(states, actions, rewards, next_states, dones)
        
        return loss
    
    def _log_progress(self, episode: int, total_episodes: int) -> None:
        """Log training progress.
        
        Args:
            episode: Current episode number.
            total_episodes: Total number of episodes.
        """
        recent_rewards = self.episode_rewards[-self.log_interval:]
        recent_lengths = self.episode_lengths[-self.log_interval:]
        recent_losses = self.losses[-self.log_interval:] if self.losses else [0.0]
        
        avg_reward = np.mean(recent_rewards)
        avg_length = np.mean(recent_lengths)
        avg_loss = np.mean(recent_losses)
        
        print(
            f"Episode {episode}/{total_episodes} | "
            f"Avg Reward: {avg_reward:+.2f} | "
            f"Avg Length: {avg_length:.0f} | "
            f"Avg Loss: {avg_loss:.4f} | "
            f"Epsilon: {self.agent.epsilon:.3f} | "
            f"Buffer: {len(self.replay_buffer)}"
        )
    
    def evaluate(
        self,
        num_episodes: int = 10,
        max_steps: int = 3000,
        deterministic: bool = True,
    ) -> dict[str, Any]:
        """Evaluate agent performance.
        
        Args:
            num_episodes: Number of evaluation episodes.
            max_steps: Maximum steps per episode.
            deterministic: If True, use greedy policy (no exploration).
        
        Returns:
            Dictionary of evaluation metrics.
        """
        print(f"Evaluating agent for {num_episodes} episodes...")
        
        episode_manager = EpisodeManager()
        
        def episode_callback(episode: Episode) -> None:
            """Callback for episode completion."""
            print(
                f"  Episode {episode.episode_id + 1}: "
                f"Reward={episode.total_reward:+.2f}, "
                f"Steps={episode.steps}, "
                f"Result={episode.final_result}"
            )
        
        episodes = episode_manager.collect_episodes(
            env=self.env,
            agent=self.agent,
            num_episodes=num_episodes,
            max_steps=max_steps,
            deterministic=deterministic,
            on_episode_end=episode_callback,
        )
        
        # Calculate metrics
        rewards = [ep.total_reward for ep in episodes]
        lengths = [ep.steps for ep in episodes]
        wins = sum(1 for ep in episodes if ep.final_result == "victory")
        
        metrics = {
            "mean_reward": float(np.mean(rewards)),
            "std_reward": float(np.std(rewards)),
            "mean_length": float(np.mean(lengths)),
            "win_rate": wins / num_episodes,
            "episodes": episodes,
        }
        
        print("\nEvaluation Results:")
        print(f"  Mean Reward: {metrics['mean_reward']:+.2f} ± {metrics['std_reward']:.2f}")
        print(f"  Mean Length: {metrics['mean_length']:.0f}")
        print(f"  Win Rate: {metrics['win_rate']:.1%}")
        
        return metrics
