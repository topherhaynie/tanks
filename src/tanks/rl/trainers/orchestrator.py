"""Training regime orchestrator for comprehensive RL training.

Coordinates the full training pipeline:
1. Phase A: Map-specific curriculum (6 stages)
2. Phase B: Random map generalization (self-play)
3. Phase C: Survival training (1v2, 1v3)
4. Phase D: Co-evolution and refinement
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from tanks.bots import SmartBot
from tanks.maps.generator import MapGenerator
from tanks.rl.actions import ActionSpace, create_continuous_action_space, create_discrete_action_space
from tanks.rl.checkpoint import CheckpointManager
from tanks.rl.metrics.elo import ELORatingSystem
from tanks.rl.models.agent import Agent, DQNAgent, PPOAgent
from tanks.rl.replay_buffer import ReplayBuffer
from tanks.rl.trainers.curriculum import CurriculumStage, CurriculumTrainer
from tanks.rl.trainers.self_play import SelfPlayTrainer
from tanks.training.env import TrainingEnvironment
from tanks.training.map_specs import (
    STANDARD_CURRICULUM,
    SURVIVAL_EXTREME_SPEC,
    SURVIVAL_MEDIUM_SPEC,
    SURVIVAL_SMALL_SPEC,
    create_random_map_config,
)
from tanks.training.multi_agent_env import MultiAgentEnvironment
from tanks.training.rewards import RewardCalculator, RewardWeights


class TrainingOrchestrator:
    """Orchestrates the complete training regime.

    Manages progression through all training phases, tracking metrics,
    saving checkpoints, and providing comprehensive progress reports.

    Args:
        agent: Agent to train (DQN or PPO).
        base_checkpoint_dir: Base directory for all checkpoints.
        regime_config: Configuration dict for training regime.
        verbose: Whether to print detailed progress.

    """

    def __init__(
        self,
        agent: Agent,
        base_checkpoint_dir: str = "checkpoints/regime",
        regime_config: dict[str, Any] | None = None,
        verbose: bool = True,
    ) -> None:
        """Initialize training orchestrator."""
        self.agent = agent
        self.base_checkpoint_dir = Path(base_checkpoint_dir)
        self.base_checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = verbose

        # Default regime configuration
        self.config = regime_config or {
            "phase_a_enabled": True,  # Map-specific curriculum
            "phase_b_enabled": True,  # Random map self-play
            "phase_c_enabled": True,  # Survival training
            "phase_a_episodes_per_stage": 150,
            "phase_b_episodes": 500,
            "phase_c_episodes_per_stage": 200,
            "exploration_weight": 8.0,  # Boost exploration rewards
            "save_interval": 50,
            "log_interval": 10,
        }
        self.config.update(regime_config or {})

        # Progress tracking
        self.regime_start_time = datetime.now(tz=timezone.utc)
        self.phase_metrics: dict[str, dict[str, Any]] = {}
        self.current_phase = ""
        self.total_episodes = 0

        # ELO rating system for benchmarking
        elo_dir = self.base_checkpoint_dir / "elo"
        self.elo_system = ELORatingSystem(
            k_factor=32,
            starting_rating=1500,
            storage_path=str(elo_dir / "ratings.json"),
        )

    def run_full_regime(self) -> dict[str, Any]:
        """Execute the complete training regime.

        Returns:
            Dictionary with metrics from all phases.

        """
        self._log_header("STARTING COMPLETE TRAINING REGIME")

        results = {}

        # Phase A: Map-Specific Curriculum
        if self.config["phase_a_enabled"]:
            results["phase_a"] = self._run_phase_a()

        # Phase B: Random Map Generalization
        if self.config["phase_b_enabled"]:
            results["phase_b"] = self._run_phase_b()

        # Phase C: Survival Training
        if self.config["phase_c_enabled"]:
            results["phase_c"] = self._run_phase_c()

        # Final report
        self._generate_final_report(results)

        return results

    def _run_phase_a(self) -> dict[str, Any]:
        """Run Phase A: Map-specific curriculum training.

        Returns:
            Phase metrics.

        """
        self.current_phase = "Phase A: Map Curriculum"
        self._log_header(self.current_phase)

        phase_dir = self.base_checkpoint_dir / "phase_a"
        phase_dir.mkdir(exist_ok=True)

        # Create custom curriculum stages from map specs
        curriculum_stages = []
        for map_spec in STANDARD_CURRICULUM:
            stage = CurriculumStage(
                name=map_spec.name,
                opponent_type=map_spec.recommended_opponent,
                advancement_threshold=map_spec.success_threshold,
                min_episodes=map_spec.min_episodes,
            )
            curriculum_stages.append(stage)

        # Create checkpoint manager
        checkpoint_mgr = CheckpointManager(
            str(phase_dir / "checkpoints"),
            max_checkpoints=10,
            max_opponents=10,
        )

        # Train on each map type
        stage_results = []
        for i, map_spec in enumerate(STANDARD_CURRICULUM):
            self._log(f"\n{'=' * 80}")
            self._log(f"Stage {i + 1}/{len(STANDARD_CURRICULUM)}: {map_spec.name}")
            self._log(f"Skill Focus: {map_spec.description}")
            self._log(f"Target: {map_spec.success_threshold:.0%} win rate")
            self._log(f"{'=' * 80}\n")

            # Generate map
            map_generator = MapGenerator(map_spec.config)
            game_map = map_generator.generate()

            # Use SmartBot only for first 2 stages to learn basics, then self-play
            # This reduces reliance on coded bots while providing initial guidance
            use_bot_opponent = i < 2  # Only first 2 stages

            # Create environment with exploration-focused rewards
            env = TrainingEnvironment(
                map_config={"map": game_map},
                max_steps=3000,
                action_space=self._get_action_space(),
                opponent_bot=SmartBot() if use_bot_opponent else None,  # None triggers opponent pool
                reward_calculator=self._create_exploration_rewards(),
            )

            # Create curriculum trainer for this stage
            trainer = CurriculumTrainer(
                env=env,
                agent=self.agent,
                checkpoint_manager=checkpoint_mgr,
                stages=[curriculum_stages[i]],
                log_interval=self.config["log_interval"],
            )

            # Train
            metrics = trainer.train(
                max_episodes=self.config["phase_a_episodes_per_stage"],
                save_interval=self.config["save_interval"],
            )

            stage_results.append(
                {
                    "stage": map_spec.name,
                    "episodes": len(metrics["episode_rewards"]),
                    "avg_reward": float(np.mean(metrics["episode_rewards"])),
                    "win_rate": float(np.mean(metrics["episode_wins"])),
                }
            )

            self.total_episodes += len(metrics["episode_rewards"])

        # Save phase results
        self._save_phase_results("phase_a", stage_results)

        return {
            "stages": stage_results,
            "total_episodes": self.total_episodes,
        }

    def _run_phase_b(self) -> dict[str, Any]:
        """Run Phase B: Random map generalization with self-play.

        Returns:
            Phase metrics.

        """
        self.current_phase = "Phase B: Random Map Self-Play"
        self._log_header(self.current_phase)

        phase_dir = self.base_checkpoint_dir / "phase_b"
        phase_dir.mkdir(exist_ok=True)

        # Create checkpoint manager for self-play
        checkpoint_mgr = CheckpointManager(
            str(phase_dir / "checkpoints"),
            max_checkpoints=10,
            max_opponents=15,  # Larger opponent pool for self-play
        )

        # Create environment with random maps
        # We'll regenerate the map each episode using different configs
        env = TrainingEnvironment(
            map_config=None,
            max_steps=3000,
            action_space=self._get_action_space(),
            opponent_bot=None,  # Pure self-play using opponent pool
            reward_calculator=self._create_exploration_rewards(),
        )

        # Create self-play trainer
        trainer = SelfPlayTrainer(
            env=env,
            agent=self.agent,
            checkpoint_manager=checkpoint_mgr,
            snapshot_interval=30,  # Add opponent every 30 episodes
            opponent_prob=0.7,  # 70% self-play, 30% bots
            log_interval=self.config["log_interval"],
        )

        self._log(f"Training on random maps for {self.config['phase_b_episodes']} episodes")
        self._log("Map diversity: Size 30-60 tiles, Density 10-35%, All patterns")
        self._log("Self-play: Opponent snapshots every 30 episodes\n")

        # Override env reset to generate random maps
        original_reset = env.reset

        def random_map_reset():
            # Generate new random map
            config = create_random_map_config(
                min_size=(30, 17),
                max_size=(60, 34),
                min_density=0.10,
                max_density=0.35,
            )
            map_generator = MapGenerator(config)
            env.game_map = map_generator.generate()
            return original_reset()

        env.reset = random_map_reset

        # Train
        metrics = trainer.train(
            num_episodes=self.config["phase_b_episodes"],
            save_interval=self.config["save_interval"],
        )

        self.total_episodes += len(metrics["episode_rewards"])

        results = {
            "episodes": len(metrics["episode_rewards"]),
            "avg_reward": float(np.mean(metrics["episode_rewards"])),
            "win_rate": float(np.mean(metrics["episode_wins"])),
            "final_opponent_pool_size": checkpoint_mgr.get_opponent_count(),
        }

        self._save_phase_results("phase_b", results)

        return results

    def _run_phase_c(self) -> dict[str, Any]:
        """Run Phase C: Survival training (1v2, 1v3).

        Returns:
            Phase metrics.

        """
        self.current_phase = "Phase C: Survival Training"
        self._log_header(self.current_phase)

        phase_dir = self.base_checkpoint_dir / "phase_c"
        phase_dir.mkdir(exist_ok=True)

        checkpoint_mgr = CheckpointManager(
            str(phase_dir / "checkpoints"),
            max_checkpoints=10,
            max_opponents=10,
        )

        stage_results = []

        # Stage 1: 1v2 (2 opponents)
        for i, (map_spec, num_opponents) in enumerate(
            [
                (SURVIVAL_SMALL_SPEC, 2),
                (SURVIVAL_MEDIUM_SPEC, 2),
                (SURVIVAL_EXTREME_SPEC, 3),
            ]
        ):
            self._log(f"\n{'=' * 80}")
            self._log(f"Survival Stage {i + 1}/3: 1v{num_opponents} - {map_spec.name}")
            self._log(f"Challenge: {map_spec.description}")
            self._log(f"Success: {map_spec.success_threshold:.0%} win rate OR 45s+ survival")
            self._log(f"{'=' * 80}\n")

            # Generate map
            map_generator = MapGenerator(map_spec.config)
            game_map = map_generator.generate()

            # Use self-play: agent vs previous versions of itself in NvM scenarios
            # This teaches survival tactics against competent, evolving opponents
            opponent_bots = None  # Triggers opponent pool (self-play)
            env = MultiAgentEnvironment(
                num_opponents=num_opponents,
                opponent_bots=opponent_bots,
                map_generator_config=map_spec.config,
                max_steps=3000,
                action_space=self._get_action_space(),
                reward_calculator=self._create_survival_rewards(),
            )

            # Override map
            env.game_map = game_map

            # Train
            metrics = self._train_survival(
                env=env,
                checkpoint_mgr=checkpoint_mgr,
                episodes=self.config["phase_c_episodes_per_stage"],
                stage_name=map_spec.name,
            )

            stage_results.append(
                {
                    "stage": map_spec.name,
                    "opponents": num_opponents,
                    "episodes": len(metrics["episode_rewards"]),
                    "avg_reward": float(np.mean(metrics["episode_rewards"])),
                    "win_rate": float(np.mean(metrics["episode_wins"])),
                    "avg_survival_time": float(np.mean(metrics.get("survival_times", [0]))),
                }
            )

            self.total_episodes += len(metrics["episode_rewards"])

        self._save_phase_results("phase_c", stage_results)

        return {
            "stages": stage_results,
            "total_episodes": self.total_episodes,
        }

    def _train_survival(
        self,
        env: MultiAgentEnvironment,
        checkpoint_mgr: CheckpointManager,
        episodes: int,
        stage_name: str,
    ) -> dict[str, Any]:
        """Train in survival scenario.

        Args:
            env: Multi-agent environment.
            checkpoint_mgr: Checkpoint manager.
            episodes: Number of episodes.
            stage_name: Stage name for logging.

        Returns:
            Training metrics.

        """
        episode_rewards = []
        episode_wins = []
        survival_times = []
        replay_buffer = None
        batch_size = 64

        if isinstance(self.agent, DQNAgent):
            replay_buffer = ReplayBuffer(capacity=100_000, state_dim=self.agent.state_dim)

        pbar = tqdm(range(episodes), desc=f"Survival: {stage_name}", unit="ep", ncols=100)

        for episode in pbar:
            state = env.reset()
            done = False
            episode_reward = 0.0
            steps = 0
            ppo_states: list[np.ndarray] = []
            ppo_actions: list[np.ndarray] = []
            ppo_log_probs: list[float] = []
            ppo_values: list[float] = []
            ppo_rewards: list[float] = []
            ppo_dones: list[bool] = []

            while not done and steps < 3000:
                if isinstance(self.agent, DQNAgent):
                    action = self.agent.select_action(state)
                else:
                    assert isinstance(self.agent, PPOAgent)
                    action, log_prob, value = self.agent.get_action(state, deterministic=False)

                next_state, reward, done, info = env.step(action)
                episode_reward += reward

                if isinstance(self.agent, DQNAgent) and replay_buffer is not None:
                    replay_buffer.add(state, int(action), reward, next_state, done)
                    if len(replay_buffer) >= batch_size:
                        batch = replay_buffer.sample(batch_size)
                        self.agent.train_step(*batch)
                        if self.agent.steps_done % 1000 == 0:
                            self.agent.update_target_network()
                elif isinstance(self.agent, PPOAgent):
                    ppo_states.append(state)
                    ppo_actions.append(action)
                    ppo_log_probs.append(log_prob)
                    ppo_values.append(value)
                    ppo_rewards.append(reward)
                    ppo_dones.append(done)

                state = next_state
                steps += 1

                # Train agent here (simplified - should use proper trainer)
                # This is just for survival metrics tracking

            won = info.get("won", False)
            survival_time = steps / 30.0  # Convert to seconds (30 Hz input rate)

            episode_rewards.append(episode_reward)
            episode_wins.append(won)
            survival_times.append(survival_time)

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
                self.agent.train_step(states, actions, log_probs, advantages, returns)
            elif isinstance(self.agent, DQNAgent):
                self.agent.decay_epsilon()

            # Update progress bar
            recent_win_rate = np.mean(episode_wins[-20:])
            recent_survival = np.mean(survival_times[-20:])
            pbar.set_postfix(
                {
                    "win_rate": f"{recent_win_rate:.1%}",
                    "survival": f"{recent_survival:.1f}s",
                }
            )

            # Save checkpoint periodically
            if (episode + 1) % self.config["save_interval"] == 0:
                checkpoint_mgr.save_checkpoint(self.agent, self.total_episodes + episode)

        pbar.close()

        return {
            "episode_rewards": episode_rewards,
            "episode_wins": episode_wins,
            "survival_times": survival_times,
        }

    def _get_action_space(self) -> ActionSpace:
        """Get action space compatible with the current agent type."""
        if isinstance(self.agent, PPOAgent):
            return create_continuous_action_space()
        return create_discrete_action_space(auto_aim=True)

    def _create_exploration_rewards(self) -> RewardCalculator:
        """Create reward calculator with boosted exploration."""
        weights = RewardWeights(
            kill=100.0,
            death=-100.0,
            bullet_hit=10.0,
            survival_per_second=0.1,
            standing_still_penalty=-1.0,
            new_terrain_revealed=self.config["exploration_weight"],  # Boosted!
        )

        return RewardCalculator(weights=weights, enable_shaping=True)

    def _create_survival_rewards(self) -> RewardCalculator:
        """Create reward calculator for survival scenarios."""
        weights = RewardWeights(
            kill=150.0,  # Bonus for kills when outnumbered
            death=-200.0,  # Heavy penalty
            bullet_hit=15.0,
            survival_per_second=0.5,  # Strong survival incentive
            bullet_hit_taken=-10.0,
            standing_still_penalty=-1.5,  # Must keep moving!
            new_terrain_revealed=10.0,  # Strong exploration when outnumbered
        )

        return RewardCalculator(weights=weights, enable_shaping=True)

    def _save_phase_results(self, phase_name: str, results: Any) -> None:
        """Save phase results to JSON."""
        results_file = self.base_checkpoint_dir / f"{phase_name}_results.json"
        with results_file.open("w") as f:
            json.dump(results, f, indent=2)

        self._log(f"\nPhase results saved to: {results_file}")

    def _generate_final_report(self, results: dict[str, Any]) -> None:
        """Generate comprehensive final training report."""
        self._log_header("TRAINING REGIME COMPLETE")

        duration = datetime.now(tz=timezone.utc) - self.regime_start_time

        report = f"""
{{'='*80}}
FINAL TRAINING REPORT
{{'='*80}}

Total Duration: {duration}
Total Episodes: {self.total_episodes}

Phase A - Map Curriculum:
"""

        if "phase_a" in results:
            for stage in results["phase_a"]["stages"]:
                report += f"  {stage['stage']}: {stage['win_rate']:.1%} win rate ({stage['episodes']} episodes)\n"

        report += "\nPhase B - Random Map Self-Play:\n"
        if "phase_b" in results:
            report += f"  Episodes: {results['phase_b']['episodes']}\n"
            report += f"  Win Rate: {results['phase_b']['win_rate']:.1%}\n"
            report += f"  Opponent Pool: {results['phase_b']['final_opponent_pool_size']}\n"

        report += "\nPhase C - Survival Training:\n"
        if "phase_c" in results:
            for stage in results["phase_c"]["stages"]:
                report += f"  {stage['stage']} (1v{stage['opponents']}): {stage['win_rate']:.1%} win rate, "
                report += f"{stage['avg_survival_time']:.1f}s survival\n"

        report += "\n" + "=" * 80 + "\n"
        report += "Agent has completed comprehensive training regime!\n"
        report += "Ready for deployment and competitive play.\n"
        report += "=" * 80 + "\n"

        self._log(report)

        # Save final report
        report_file = self.base_checkpoint_dir / "final_report.txt"
        with report_file.open("w") as f:
            f.write(report)

        self._log(f"Full report saved to: {report_file}")

    def _log_header(self, message: str) -> None:
        """Log a prominent header."""
        if self.verbose:
            print(f"\n{'=' * 80}")
            print(f"{message:^80}")
            print(f"{'=' * 80}\n")

    def _log(self, message: str) -> None:
        """Log a message."""
        if self.verbose:
            print(message)  # noqa: T201
