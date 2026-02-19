"""Self-play training for RL agents.

Trains agents by making them compete against previous versions of themselves.
Maintains an opponent pool and periodically adds snapshots for diversity.
"""

import random
import sys
from typing import Any

import numpy as np
from tqdm import tqdm

from tanks.bots import SimpleBot, SmartBot
from tanks.rl.checkpoint import CheckpointManager
from tanks.rl.models.agent import Agent, DQNAgent, PPOAgent
from tanks.rl.replay_buffer import ReplayBuffer
from tanks.training.env import TrainingEnvironment
from tanks.training.episode import EpisodeManager


class SelfPlayTrainer:
    """Self-play trainer for RL agents.

    Trains agents by playing against their own past versions. Periodically
    snapshots the current agent and adds it to an opponent pool. Opponents
    are randomly selected for variety and to prevent overfitting.

    Args:
        env: Training environment.
        agent: Agent to train (DQN or PPO).
        checkpoint_manager: Checkpoint manager for saving/loading.
        buffer_size: Replay buffer capacity (DQN only). Default: 100,000.
        batch_size: Training batch size. Default: 64.
        snapshot_interval: Episodes between adding opponent snapshots. Default: 50.
        opponent_prob: Probability of using opponent vs random bot. Default: 0.8.
        log_interval: Episodes between logging. Default: 10.

    """

    def __init__(
        self,
        env: TrainingEnvironment,
        agent: Agent,
        checkpoint_manager: CheckpointManager,
        buffer_size: int = 100_000,
        batch_size: int = 64,
        snapshot_interval: int = 50,
        opponent_prob: float = 0.8,
        log_interval: int = 10,
    ) -> None:
        """Initialize self-play trainer."""
        self.env = env
        self.agent = agent
        self.checkpoint_manager = checkpoint_manager
        self.batch_size = batch_size
        self.snapshot_interval = snapshot_interval
        self.opponent_prob = opponent_prob
        self.log_interval = log_interval

        # Create replay buffer for DQN
        self.replay_buffer = None
        if isinstance(agent, DQNAgent):
            self.replay_buffer = ReplayBuffer(
                capacity=buffer_size,
                state_dim=agent.state_dim,
            )

        # Training stats
        self.total_steps = 0
        self.episode_rewards: list[float] = []
        self.episode_lengths: list[int] = []
        self.episode_wins: list[bool] = []
        self.losses: list[float] = []
        self.opponent_versions: list[int] = []
        self.current_opponent_version = 0
        self._prev_log_metrics: dict[str, float] | None = None
        self._regression_streak = 0

        # Episode manager
        self.episode_manager = EpisodeManager()

    def train(
        self,
        num_episodes: int,
        max_steps_per_episode: int = 3000,
        warmup_steps: int = 1000,
        save_interval: int = 100,
        use_progress_bar: bool = True,
    ) -> dict[str, list[Any]]:
        """Train agent with self-play.

        Args:
            num_episodes: Number of episodes to train.
            max_steps_per_episode: Maximum steps per episode. Default: 3000.
            warmup_steps: Steps of random exploration before training (DQN). Default: 1000.
            save_interval: Episodes between checkpoint saves. Default: 100.
            use_progress_bar: Show tqdm progress bar. Default: True.

        Returns:
            Dictionary of training metrics.

        """
        print(f"Starting self-play training for {num_episodes} episodes...")
        print(f"Device: {self.agent.device}")
        print(f"Snapshot interval: {self.snapshot_interval} episodes")
        print(f"Opponent pool size: {self.checkpoint_manager.get_opponent_count()}")
        print()

        # Progress bar
        pbar = None
        if use_progress_bar:
            pbar = tqdm(
                range(num_episodes),
                desc="Self-play",
                unit="ep",
                ncols=100,
                dynamic_ncols=True,
                file=sys.stdout,
                disable=not sys.stdout.isatty(),
            )

        for episode in range(num_episodes):
            # Select opponent for this episode
            opponent_type = self._select_opponent()

            # Run episode
            episode_reward, episode_length, won = self._run_episode(
                episode,
                max_steps_per_episode,
                warmup_steps,
                opponent_type,
            )

            # Store metrics
            self.episode_rewards.append(episode_reward)
            self.episode_lengths.append(episode_length)
            self.episode_wins.append(won)

            # Update progress bar
            if pbar is not None:
                recent_reward = np.mean(self.episode_rewards[-10:])
                recent_win_rate = np.mean(self.episode_wins[-10:])
                pbar.update(1)
                pbar.set_postfix(
                    {
                        "reward": f"{recent_reward:+.1f}",
                        "win_rate": f"{recent_win_rate:.0%}",
                        "opp_pool": self.checkpoint_manager.get_opponent_count(),
                    },
                )

            # Log periodically
            if (episode + 1) % self.log_interval == 0:
                self._log_progress(episode + 1, pbar)

            # Add snapshot to opponent pool
            if (episode + 1) % self.snapshot_interval == 0:
                self._add_opponent_snapshot(episode + 1)

            # Save checkpoint
            if (episode + 1) % save_interval == 0:
                self._save_checkpoint(episode + 1)

        if pbar is not None:
            pbar.close()

        print("\nSelf-play training complete!")
        self._print_final_stats()

        return {
            "episode_rewards": self.episode_rewards,
            "episode_lengths": self.episode_lengths,
            "episode_wins": self.episode_wins,
            "losses": self.losses,
            "opponent_versions": self.opponent_versions,
        }

    def _select_opponent(self) -> str:
        """Select opponent type for next episode.

        Returns:
            Opponent type: "self_play", "simple", or "smart".

        """
        # Warm-up phase: train against bots until we have some opponents
        if self.checkpoint_manager.get_opponent_count() == 0:
            return random.choice(["simple", "smart"])

        # Use self-play opponent most of the time
        if random.random() < self.opponent_prob:
            return "self_play"

        # Occasionally use bots for variety
        return random.choice(["simple", "smart"])

    def _run_episode(
        self,
        episode_num: int,
        max_steps: int,
        warmup_steps: int,
        opponent_type: str,
    ) -> tuple[float, int, bool]:
        """Run one training episode.

        Args:
            episode_num: Current episode number.
            max_steps: Maximum steps per episode.
            warmup_steps: Warmup steps before training.
            opponent_type: Type of opponent ("self_play", "simple", "smart").

        Returns:
            Tuple of (total_reward, episode_length, won).

        """
        # Update opponent bot type for this episode
        if opponent_type == "simple":
            self.env.opponent_bot = SimpleBot()
        elif opponent_type == "smart":
            self.env.opponent_bot = SmartBot()
        else:  # self_play
            # For self-play, we'll use SmartBot as fallback for now
            # TODO: Implement proper self-play opponent loading
            self.env.opponent_bot = SmartBot()

        # Reset environment
        state = self.env.reset()

        # Run episode
        total_reward = 0.0
        episode_length = 0
        done = False

        ppo_states: list[np.ndarray] = []
        ppo_actions: list[np.ndarray] = []
        ppo_log_probs: list[float] = []
        ppo_values: list[float] = []
        ppo_rewards: list[float] = []
        ppo_dones: list[bool] = []

        while not done and episode_length < max_steps:
            # Select action
            if isinstance(self.agent, DQNAgent):
                action = self.agent.select_action(state)
            else:  # PPO
                assert isinstance(self.agent, PPOAgent)
                action, log_prob, value = self.agent.get_action(state, deterministic=False)

            # Step environment
            next_state, reward, done, info = self.env.step(action)

            # Store transition
            if isinstance(self.agent, DQNAgent) and self.replay_buffer:
                self.replay_buffer.add(state, action, reward, next_state, done)
            elif isinstance(self.agent, PPOAgent):
                ppo_states.append(state)
                ppo_actions.append(action)
                ppo_log_probs.append(log_prob)
                ppo_values.append(value)
                ppo_rewards.append(reward)
                ppo_dones.append(done)

            # Train agent
            if self.total_steps >= warmup_steps:
                if isinstance(self.agent, DQNAgent) and self.replay_buffer:
                    if len(self.replay_buffer) >= self.batch_size:
                        batch = self.replay_buffer.sample(self.batch_size)
                        loss = self.agent.train_step(*batch)
                        if loss is not None:
                            self.losses.append(loss)

                        # Update target network
                        if self.total_steps % 1000 == 0:
                            self.agent.update_target_network()

            # Update state
            state = next_state
            total_reward += reward
            episode_length += 1
            self.total_steps += 1

        # Check if won
        won = info.get("agent_won", info.get("won", False))

        if isinstance(self.agent, PPOAgent) and ppo_states:
            states = np.asarray(ppo_states, dtype=np.float32)
            actions = np.asarray(ppo_actions, dtype=np.float32)
            log_probs = np.asarray(ppo_log_probs, dtype=np.float32)
            rewards = np.asarray(ppo_rewards, dtype=np.float32)
            values = np.asarray(ppo_values, dtype=np.float32)
            dones = np.asarray(ppo_dones, dtype=bool)

            next_value = 0.0
            if not done:
                _, _, next_value = self.agent.get_action(state, deterministic=False)

            advantages, returns = self.agent.compute_gae(rewards, values, dones, next_value)
            losses = self.agent.train_step(states, actions, log_probs, advantages, returns)
            self.losses.append(losses["total_loss"])
        elif isinstance(self.agent, DQNAgent):
            self.agent.decay_epsilon()

        return total_reward, episode_length, won

    def _add_opponent_snapshot(self, episode: int) -> None:
        """Add current agent to opponent pool.

        Args:
            episode: Current episode number.

        """
        # Calculate recent win rate
        recent_wins = self.episode_wins[-self.snapshot_interval :]
        win_rate = np.mean(recent_wins) if recent_wins else 0.0

        # Add to pool
        self.current_opponent_version += 1
        self.checkpoint_manager.add_opponent(
            self.agent,
            self.current_opponent_version,
            win_rate,
        )

        print(
            f"\n[Episode {episode}] Added opponent v{self.current_opponent_version} to pool (win_rate: {win_rate:.1%})",
        )

    def _save_checkpoint(self, episode: int) -> None:
        """Save training checkpoint.

        Args:
            episode: Current episode number.

        """
        # Calculate recent metrics
        recent_rewards = self.episode_rewards[-100:]
        recent_wins = self.episode_wins[-100:]

        avg_reward = np.mean(recent_rewards) if recent_rewards else 0.0
        win_rate = np.mean(recent_wins) if recent_wins else 0.0

        # Save latest
        self.checkpoint_manager.save_latest(self.agent, episode)

        # Save best
        self.checkpoint_manager.save_best(
            self.agent,
            episode,
            avg_reward,
            win_rate,
        )

        # Save periodic
        self.checkpoint_manager.save_checkpoint(self.agent, episode)

    def _log_progress(self, episode: int, pbar: Any = None) -> None:
        """Log training progress.

        Args:
            episode: Current episode number.
            pbar: Optional progress bar for writing.

        """
        # Calculate metrics over last N episodes
        window = min(self.log_interval, len(self.episode_rewards))
        recent_rewards = self.episode_rewards[-window:]
        recent_lengths = self.episode_lengths[-window:]
        recent_wins = self.episode_wins[-window:]
        recent_losses = self.losses[-100:] if self.losses else []

        avg_reward = np.mean(recent_rewards)
        avg_length = np.mean(recent_lengths)
        win_rate = np.mean(recent_wins)
        avg_loss = np.mean(recent_losses) if recent_losses else 0.0
        warning = self._update_collapse_watch(avg_reward, win_rate, avg_length)
        warning_line = f"{warning}\n" if warning else ""

        # Format message
        msg = (
            f"\n{'=' * 80}\n"
            f"Episode: {episode} | Steps: {self.total_steps}\n"
            f"Avg Reward: {avg_reward:+.2f} | Win Rate: {win_rate:.1%}\n"
            f"Avg Length: {avg_length:.0f} | Avg Loss: {avg_loss:.4f}\n"
            f"Opponent Pool: {self.checkpoint_manager.get_opponent_count()}\n"
            f"{warning_line}"
            f"{'=' * 80}\n"
        )

        if pbar is not None:
            pbar.write(msg)
        else:
            print(msg)

    def _update_collapse_watch(
        self,
        avg_reward: float,
        win_rate: float,
        avg_length: float,
    ) -> str | None:
        """Track consecutive regressions and return warning text when detected.

        Args:
            avg_reward: Current logging-window average reward.
            win_rate: Current logging-window win rate.
            avg_length: Current logging-window average episode length.

        Returns:
            Warning string when collapse pattern is detected, otherwise None.

        """
        if self._prev_log_metrics is None:
            self._prev_log_metrics = {
                "avg_reward": avg_reward,
                "win_rate": win_rate,
                "avg_length": avg_length,
            }
            return None

        reward_drop = avg_reward <= self._prev_log_metrics["avg_reward"] - 10.0
        win_drop = win_rate <= self._prev_log_metrics["win_rate"] - 0.10
        length_rise = avg_length >= self._prev_log_metrics["avg_length"] + 120.0

        if win_drop and (reward_drop or length_rise):
            self._regression_streak += 1
        else:
            self._regression_streak = 0

        self._prev_log_metrics = {
            "avg_reward": avg_reward,
            "win_rate": win_rate,
            "avg_length": avg_length,
        }

        if self._regression_streak >= 2:
            return (
                "⚠️  Collapse watch: 2+ consecutive regressions detected "
                "(win/reward down, length up). Consider lowering PPO lr/clip or restarting stage."
            )

        return None

    def _print_final_stats(self) -> None:
        """Print final training statistics."""
        total_episodes = len(self.episode_rewards)
        total_reward = sum(self.episode_rewards)
        avg_reward = total_reward / total_episodes if total_episodes > 0 else 0.0

        total_wins = sum(self.episode_wins)
        overall_win_rate = total_wins / total_episodes if total_episodes > 0 else 0.0

        print(f"Total Episodes: {total_episodes}")
        print(f"Total Steps: {self.total_steps}")
        print(f"Average Reward: {avg_reward:+.2f}")
        print(f"Overall Win Rate: {overall_win_rate:.1%}")
        print(f"Final Opponent Pool Size: {self.checkpoint_manager.get_opponent_count()}")

        # Recent performance (last 100 episodes)
        recent_window = min(100, total_episodes)
        recent_rewards = self.episode_rewards[-recent_window:]
        recent_wins = self.episode_wins[-recent_window:]

        recent_avg_reward = np.mean(recent_rewards)
        recent_win_rate = np.mean(recent_wins)

        print(f"\nRecent Performance (last {recent_window} episodes):")
        print(f"  Average Reward: {recent_avg_reward:+.2f}")
        print(f"  Win Rate: {recent_win_rate:.1%}")
