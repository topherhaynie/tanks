"""Curriculum learning trainer for RL agents.

Progressively trains agents against increasingly difficult opponents.
Automatically advances to next difficulty level when performance thresholds are met.
"""

import sys
from typing import Any

import numpy as np
from tqdm import tqdm

from tanks.bots import SimpleBot, SmartBot
from tanks.rl.checkpoint import CheckpointManager
from tanks.rl.models.agent import Agent, DQNAgent, PPOAgent
from tanks.rl.replay_buffer import ReplayBuffer
from tanks.training.env import TrainingEnvironment


class CurriculumStage:
    """Defines a curriculum learning stage.

    Args:
        name: Stage name (e.g., "easy", "medium", "hard").
        opponent_type: Opponent bot type ("simple", "smart", or "self_play").
        advancement_threshold: Win rate threshold to advance. Default: 0.7.
        min_episodes: Minimum episodes before advancement. Default: 100.

    """

    def __init__(
        self,
        name: str,
        opponent_type: str,
        advancement_threshold: float = 0.7,
        min_episodes: int = 100,
    ) -> None:
        """Initialize curriculum stage."""
        self.name = name
        self.opponent_type = opponent_type
        self.advancement_threshold = advancement_threshold
        self.min_episodes = min_episodes


class CurriculumTrainer:
    """Curriculum learning trainer for RL agents.

    Trains agents through progressive difficulty stages. Automatically
    advances when agent meets performance thresholds.

    Args:
        env: Training environment.
        agent: Agent to train (DQN or PPO).
        checkpoint_manager: Checkpoint manager for saving/loading.
        stages: List of curriculum stages. Uses default if None.
        buffer_size: Replay buffer capacity (DQN only). Default: 100,000.
        batch_size: Training batch size. Default: 64.
        evaluation_window: Episodes for advancement eval. Default: 20.
        log_interval: Episodes between logging. Default: 10.

    """

    def __init__(
        self,
        env: TrainingEnvironment,
        agent: Agent,
        checkpoint_manager: CheckpointManager,
        stages: list[CurriculumStage] | None = None,
        buffer_size: int = 100_000,
        batch_size: int = 64,
        evaluation_window: int = 20,
        log_interval: int = 10,
    ) -> None:
        """Initialize curriculum trainer."""
        self.env = env
        self.agent = agent
        self.checkpoint_manager = checkpoint_manager
        self.batch_size = batch_size
        self.evaluation_window = evaluation_window
        self.log_interval = log_interval

        # Default curriculum stages
        if stages is None:
            self.stages = [
                CurriculumStage(
                    name="Stage 1: SimpleBot",
                    opponent_type="simple",
                    advancement_threshold=0.75,
                    min_episodes=100,
                ),
                CurriculumStage(
                    name="Stage 2: SmartBot",
                    opponent_type="smart",
                    advancement_threshold=0.65,
                    min_episodes=150,
                ),
                CurriculumStage(
                    name="Stage 3: Mastery",
                    opponent_type="smart",
                    advancement_threshold=0.80,
                    min_episodes=200,
                ),
            ]
        else:
            self.stages = stages

        # Current stage
        self.current_stage_idx = 0
        self.episodes_in_stage = 0

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
        self.stage_history: list[int] = []  # Track which stage each episode was in
        self._prev_log_metrics: dict[str, float] | None = None
        self._regression_streak = 0

    def train(
        self,
        max_episodes: int = 1000,
        max_steps_per_episode: int = 3000,
        warmup_steps: int = 1000,
        save_interval: int = 100,
        use_progress_bar: bool = True,
    ) -> dict[str, list[Any]]:
        """Train agent through curriculum stages.

        Args:
            max_episodes: Maximum total episodes. Default: 1000.
            max_steps_per_episode: Maximum steps per episode. Default: 3000.
            warmup_steps: Steps of random exploration (DQN). Default: 1000.
            save_interval: Episodes between checkpoint saves. Default: 100.
            use_progress_bar: Show tqdm progress bar. Default: True.

        Returns:
            Dictionary of training metrics.

        """
        print(f"Starting curriculum training for up to {max_episodes} episodes...")
        print(f"Device: {self.agent.device}")
        print(f"Curriculum stages: {len(self.stages)}")
        for i, stage in enumerate(self.stages):
            print(f"  Stage {i + 1}: {stage.name} (threshold: {stage.advancement_threshold:.0%})")
        print()

        # Progress bar
        pbar = None
        if use_progress_bar:
            pbar = tqdm(
                total=max_episodes,
                desc=self.stages[0].name,
                unit="ep",
                ncols=100,
                dynamic_ncols=True,
                file=sys.stdout,
                disable=not sys.stdout.isatty(),
            )

        episode = 0
        while episode < max_episodes and self.current_stage_idx < len(self.stages):
            # Get current stage
            current_stage = self.stages[self.current_stage_idx]

            # Update opponent for this stage
            if current_stage.opponent_type == "simple":
                self.env.opponent_bot = SimpleBot()
            elif current_stage.opponent_type == "smart" or current_stage.opponent_type in {"self_play", "self-play"}:
                self.env.opponent_bot = SmartBot()

            # Run episode
            episode_reward, episode_length, won = self._run_episode(
                episode,
                max_steps_per_episode,
                warmup_steps,
            )

            # Store metrics
            self.episode_rewards.append(episode_reward)
            self.episode_lengths.append(episode_length)
            self.episode_wins.append(won)
            self.stage_history.append(self.current_stage_idx)
            self.episodes_in_stage += 1

            # Update progress bar
            if pbar is not None:
                recent_reward = np.mean(self.episode_rewards[-10:])
                recent_win_rate = np.mean(self.episode_wins[-10:])
                pbar.update(1)
                pbar.set_postfix(
                    {
                        "stage": f"{self.current_stage_idx + 1}/{len(self.stages)}",
                        "reward": f"{recent_reward:+.1f}",
                        "win_rate": f"{recent_win_rate:.0%}",
                    },
                )

            # Log periodically
            if (episode + 1) % self.log_interval == 0:
                self._log_progress(episode + 1, pbar)

            # Check for stage advancement
            if self.episodes_in_stage >= current_stage.min_episodes:
                if self._check_advancement(current_stage):
                    self.current_stage_idx += 1
                    self.episodes_in_stage = 0

                    if self.current_stage_idx < len(self.stages):
                        next_stage = self.stages[self.current_stage_idx]
                        print(f"\n{'=' * 80}")
                        print(f"ADVANCED TO {next_stage.name}!")
                        print(f"{'=' * 80}\n")

                        if pbar is not None:
                            pbar.set_description(next_stage.name)

            # Save checkpoint
            if (episode + 1) % save_interval == 0:
                self._save_checkpoint(episode + 1)

            episode += 1

        if pbar is not None:
            pbar.close()

        print("\nCurriculum training complete!")
        self._print_final_stats()

        return {
            "episode_rewards": self.episode_rewards,
            "episode_lengths": self.episode_lengths,
            "episode_wins": self.episode_wins,
            "losses": self.losses,
            "stage_history": self.stage_history,
        }

    def _run_episode(
        self,
        episode_num: int,
        max_steps: int,
        warmup_steps: int,
    ) -> tuple[float, int, bool]:
        """Run one training episode.

        Args:
            episode_num: Current episode number.
            max_steps: Maximum steps per episode.
            warmup_steps: Warmup steps before training.

        Returns:
            Tuple of (total_reward, episode_length, won).

        """
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

    def _check_advancement(self, stage: CurriculumStage) -> bool:
        """Check if agent should advance to next stage.

        Args:
            stage: Current curriculum stage.

        Returns:
            True if agent meets advancement criteria.

        """
        # Need minimum episodes
        if self.episodes_in_stage < stage.min_episodes:
            return False

        # Check win rate over evaluation window
        recent_wins = self.episode_wins[-self.evaluation_window :]
        if len(recent_wins) < self.evaluation_window:
            return False

        win_rate = np.mean(recent_wins)

        return win_rate >= stage.advancement_threshold

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

        # Save periodic (with stage info)
        metadata = {
            "stage": self.current_stage_idx,
            "episodes_in_stage": self.episodes_in_stage,
        }
        self.checkpoint_manager.save_checkpoint(self.agent, episode, metadata)

    def _log_progress(self, episode: int, pbar: Any = None) -> None:
        """Log training progress.

        Args:
            episode: Current episode number.
            pbar: Optional progress bar for writing.

        """
        # Calculate metrics
        window = min(self.log_interval, len(self.episode_rewards))
        recent_rewards = self.episode_rewards[-window:]
        recent_lengths = self.episode_lengths[-window:]
        recent_wins = self.episode_wins[-window:]
        recent_losses = self.losses[-100:] if self.losses else []

        avg_reward = np.mean(recent_rewards)
        avg_length = np.mean(recent_lengths)
        win_rate = np.mean(recent_wins)
        avg_loss = np.mean(recent_losses) if recent_losses else 0.0

        # Current stage info
        current_stage = self.stages[self.current_stage_idx]
        advancement_progress = self.episodes_in_stage / current_stage.min_episodes
        warning = self._update_collapse_watch(avg_reward, win_rate, avg_length)
        warning_line = f"{warning}\n" if warning else ""

        # Format message
        msg = (
            f"\n{'=' * 80}\n"
            f"Episode: {episode} | Steps: {self.total_steps}\n"
            f"Stage: {current_stage.name} ({self.episodes_in_stage} episodes, "
            f"{advancement_progress:.0%} to min)\n"
            f"Avg Reward: {avg_reward:+.2f} | Win Rate: {win_rate:.1%} "
            f"(need {current_stage.advancement_threshold:.0%})\n"
            f"Avg Length: {avg_length:.0f} | Avg Loss: {avg_loss:.4f}\n"
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

        # Completed curriculum?
        if self.current_stage_idx >= len(self.stages):
            print(f"\n✅ CURRICULUM COMPLETE! Agent mastered all {len(self.stages)} stages!")
        else:
            print(f"\nReached stage {self.current_stage_idx + 1} of {len(self.stages)}")

        # Per-stage stats
        print("\nPer-Stage Performance:")
        for stage_idx in range(max(self.stage_history) + 1 if self.stage_history else 0):
            stage_episodes = [i for i, s in enumerate(self.stage_history) if s == stage_idx]
            if stage_episodes:
                stage_wins = [self.episode_wins[i] for i in stage_episodes]
                stage_win_rate = np.mean(stage_wins)
                stage_name = self.stages[stage_idx].name
                print(f"  {stage_name}: {len(stage_episodes)} episodes, {stage_win_rate:.1%} win rate")
