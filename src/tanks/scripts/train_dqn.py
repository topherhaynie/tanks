"""DQN training script with CLI interface.

This script provides a complete training pipeline with:
- Start/stop/resume functionality
- TensorBoard logging
- Checkpoint management
- Self-play opponent pool
- Evaluation modes
- Progress monitoring

Usage:
    # Start new training
    python -m tanks.scripts.train_dqn --episodes 1000

    # Resume from checkpoint
    python -m tanks.scripts.train_dqn --resume

    # Training with TensorBoard
    python -m tanks.scripts.train_dqn --episodes 1000 --tensorboard
    
    # View TensorBoard
    tensorboard --logdir runs/

    # Evaluate trained agent
    python -m tanks.scripts.train_dqn --evaluate --checkpoint checkpoints/best_model.pt

Examples:
    # Basic training (1000 episodes)
    python -m tanks.scripts.train_dqn

    # Fast training (no render, larger batch)
    python -m tanks.scripts.train_dqn --episodes 5000 --batch-size 128

    # Debug mode (visualize agent)
    python -m tanks.scripts.train_dqn --episodes 100 --save-interval 10

    # Resume interrupted training
    python -m tanks.scripts.train_dqn --resume

    # Evaluate best model
    python -m tanks.scripts.train_dqn --evaluate
"""

import argparse
from pathlib import Path

from tanks.rl.checkpoint import CheckpointManager
from tanks.rl.metrics import MetricsTracker, TensorBoardLogger, TrainingMetrics
from tanks.rl.models import DQNAgent
from tanks.rl.replay_buffer import ReplayBuffer
from tanks.training.env import TrainingEnvironment


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Train DQN agent for tank battle",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    # Training modes
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--train",
        action="store_true",
        default=True,
        help="Train agent (default)",
    )
    mode.add_argument(
        "--evaluate",
        action="store_true",
        help="Evaluate trained agent",
    )
    mode.add_argument(
        "--resume",
        action="store_true",
        help="Resume from latest checkpoint",
    )
    
    # Training parameters
    parser.add_argument(
        "--episodes",
        type=int,
        default=1000,
        help="Number of training episodes (default: 1000)",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=3000,
        help="Maximum steps per episode (default: 3000)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Training batch size (default: 64)",
    )
    parser.add_argument(
        "--buffer-size",
        type=int,
        default=100_000,
        help="Replay buffer capacity (default: 100,000)",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-4,
        help="Learning rate (default: 1e-4)",
    )
    parser.add_argument(
        "--gamma",
        type=float,
        default=0.99,
        help="Discount factor (default: 0.99)",
    )
    parser.add_argument(
        "--epsilon-start",
        type=float,
        default=1.0,
        help="Initial exploration rate (default: 1.0)",
    )
    parser.add_argument(
        "--epsilon-end",
        type=float,
        default=0.05,
        help="Final exploration rate (default: 0.05)",
    )
    parser.add_argument(
        "--epsilon-decay",
        type=float,
        default=0.995,
        help="Epsilon decay per episode (default: 0.995)",
    )
    parser.add_argument(
        "--target-update-freq",
        type=int,
        default=1000,
        help="Steps between target network updates (default: 1000)",
    )
    parser.add_argument(
        "--warmup-steps",
        type=int,
        default=1000,
        help="Random exploration steps before training (default: 1000)",
    )
    
    # Checkpointing
    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="checkpoints/dqn",
        help="Checkpoint directory (default: checkpoints/dqn)",
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        help="Specific checkpoint to load",
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=100,
        help="Episodes between checkpoint saves (default: 100)",
    )
    parser.add_argument(
        "--max-checkpoints",
        type=int,
        default=10,
        help="Maximum periodic checkpoints to keep (default: 10)",
    )
    
    # Logging
    parser.add_argument(
        "--tensorboard",
        action="store_true",
        help="Enable TensorBoard logging",
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="runs/dqn",
        help="TensorBoard log directory (default: runs/dqn)",
    )
    parser.add_argument(
        "--log-interval",
        type=int,
        default=10,
        help="Episodes between progress logs (default: 10)",
    )
    parser.add_argument(
        "--eval-interval",
        type=int,
        default=100,
        help="Episodes between evaluations (default: 100)",
    )
    parser.add_argument(
        "--eval-episodes",
        type=int,
        default=10,
        help="Number of evaluation episodes (default: 10)",
    )
    
    # Self-play
    parser.add_argument(
        "--self-play",
        action="store_true",
        help="Enable self-play training with opponent pool",
    )
    parser.add_argument(
        "--opponent-prob",
        type=float,
        default=0.8,
        help="Probability of using opponent from pool (default: 0.8)",
    )
    parser.add_argument(
        "--max-opponents",
        type=int,
        default=10,
        help="Maximum opponents in pool (default: 10)",
    )
    
    # Device
    parser.add_argument(
        "--device",
        type=str,
        choices=["cpu", "cuda", "auto"],
        default="auto",
        help="Training device (default: auto)",
    )
    parser.add_argument(
        "--network-type",
        type=str,
        choices=["dqn", "dueling"],
        default="dqn",
        help="Network architecture (default: dqn)",
    )
    
    return parser.parse_args()


def main() -> None:
    """Main training entry point."""
    args = parse_args()
    
    # Print configuration
    print("=" * 70)
    print("DQN Training Configuration")
    print("=" * 70)
    print(f"Mode: {'Evaluate' if args.evaluate else 'Resume' if args.resume else 'Train'}")
    print(f"Episodes: {args.episodes}")
    print(f"Max Steps: {args.max_steps}")
    print(f"Batch Size: {args.batch_size}")
    print(f"Buffer Size: {args.buffer_size:,}")
    print(f"Learning Rate: {args.learning_rate}")
    print(f"Gamma: {args.gamma}")
    print(f"Epsilon: {args.epsilon_start} → {args.epsilon_end} (decay: {args.epsilon_decay})")
    print(f"Target Update Freq: {args.target_update_freq}")
    print(f"Network Type: {args.network_type}")
    print(f"Device: {args.device}")
    print(f"Self-Play: {args.self_play}")
    print(f"TensorBoard: {args.tensorboard}")
    if args.tensorboard:
        print(f"  Log Dir: {args.log_dir}")
        print(f"  View with: tensorboard --logdir {Path(args.log_dir).parent}")
    print(f"Checkpoints: {args.checkpoint_dir}")
    print(f"  Save Interval: {args.save_interval} episodes")
    print(f"  Max Checkpoints: {args.max_checkpoints}")
    print("=" * 70)
    print()
    
    # Initialize components
    env = TrainingEnvironment(max_steps=args.max_steps)
    
    checkpoint_manager = CheckpointManager(
        checkpoint_dir=args.checkpoint_dir,
        max_checkpoints=args.max_checkpoints,
        max_opponents=args.max_opponents,
    )
    
    metrics_tracker = MetricsTracker(
        window_size=100,
        save_dir=args.checkpoint_dir,
    )
    
    tb_logger = TensorBoardLogger(
        log_dir=args.log_dir,
        enabled=args.tensorboard,
    )
    
    # Create or load agent
    agent = None
    start_episode = 0
    
    if args.evaluate:
        # Load checkpoint for evaluation
        checkpoint_path = args.checkpoint or str(Path(args.checkpoint_dir) / "best_model.pt")
        if not Path(checkpoint_path).exists():
            print(f"Error: Checkpoint not found: {checkpoint_path}")
            return
        
        agent = DQNAgent.load(checkpoint_path, device=args.device if args.device != "auto" else None)
        print(f"Loaded agent from: {checkpoint_path}")
        
        # Run evaluation
        print("\nEvaluating agent...")
        evaluate_agent(agent, env, args.eval_episodes, args.max_steps)
        return
    
    if args.resume:
        # Resume from latest checkpoint
        result = checkpoint_manager.load_latest(DQNAgent)
        if result:
            agent, start_episode = result
            print(f"Resumed training from episode {start_episode}")
        else:
            print("No checkpoint found. Starting new training.")
    
    if agent is None:
        # Create new agent
        device = None if args.device == "auto" else args.device
        agent = DQNAgent(
            state_dim=78,
            action_dim=12,
            learning_rate=args.learning_rate,
            gamma=args.gamma,
            epsilon=args.epsilon_start,
            epsilon_min=args.epsilon_end,
            epsilon_decay=args.epsilon_decay,
            device=device,
            network_type=args.network_type,
        )
        print(f"Created new {args.network_type.upper()} agent on device: {agent.device}")
    
    # Training loop
    print("\nStarting training...")
    print("Press Ctrl+C to stop and save checkpoint\n")
    
    try:
        train_agent(
            agent=agent,
            env=env,
            checkpoint_manager=checkpoint_manager,
            metrics_tracker=metrics_tracker,
            tb_logger=tb_logger,
            args=args,
            start_episode=start_episode,
        )
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user")
    finally:
        # Save final checkpoint
        print("\nSaving final checkpoint...")
        checkpoint_manager.save_latest(agent, agent.episodes_done)
        metrics_tracker.save_csv()
        tb_logger.close()
        env.close()
        
        print("\nTraining session complete!")
        metrics_tracker.print_summary()


def train_agent(
    agent: DQNAgent,
    env: TrainingEnvironment,
    checkpoint_manager: CheckpointManager,
    metrics_tracker: MetricsTracker,
    tb_logger: TensorBoardLogger,
    args: argparse.Namespace,
    start_episode: int = 0,
) -> None:
    """Run training loop.
    
    Args:
        agent: DQN agent to train.
        env: Training environment.
        checkpoint_manager: Checkpoint manager.
        metrics_tracker: Metrics tracker.
        tb_logger: TensorBoard logger.
        args: Command-line arguments.
        start_episode: Starting episode number.
    """
    # Create replay buffer
    replay_buffer = ReplayBuffer(
        capacity=args.buffer_size,
        state_dim=78,
    )
    
    total_steps = 0
    warmup = total_steps < args.warmup_steps
    
    for episode in range(start_episode, start_episode + args.episodes):
        # Run episode
        state = env.reset()
        episode_reward = 0.0
        episode_loss = 0.0
        loss_count = 0
        actions_taken: dict[int, int] = {}
        
        for step in range(args.max_steps):
            # Select action
            if warmup:
                import numpy as np
                action = int(np.random.randint(0, 12))
            else:
                action = agent.select_action(state)
            
            # Track actions
            actions_taken[action] = actions_taken.get(action, 0) + 1
            
            # Execute action
            next_state, reward, done, info = env.step(action)
            episode_reward += reward
            
            # Store experience
            replay_buffer.add(state, action, reward, next_state, done)
            
            # Train if enough experiences
            if not warmup and len(replay_buffer) >= args.batch_size:
                batch = replay_buffer.sample(args.batch_size)
                loss = agent.train_step(*batch)
                episode_loss += loss
                loss_count += 1
            
            # Update target network
            if total_steps % args.target_update_freq == 0 and total_steps > 0:
                agent.update_target_network()
            
            state = next_state
            total_steps += 1
            
            if done:
                break
            
            # Check if warmup complete
            if warmup and total_steps >= args.warmup_steps:
                warmup = False
                print(f"Warmup complete ({args.warmup_steps} steps). Starting training...")
        
        # Decay epsilon
        if not warmup:
            agent.decay_epsilon()
        
        # Create metrics
        metrics = TrainingMetrics(
            episode=episode,
            reward=episode_reward,
            length=step + 1,
            loss=episode_loss / max(loss_count, 1),
            epsilon=agent.epsilon,
            won=info.get("won", False),
            actions_taken=actions_taken,
        )
        
        # Add additional metrics from info
        if "stats" in info:
            stats = info["stats"]
            metrics.kills = stats.get("kills", 0)
            metrics.damage_dealt = stats.get("damage_dealt", 0.0)
            metrics.damage_taken = stats.get("damage_taken", 0.0)
            metrics.shots_fired = stats.get("shots_fired", 0)
            metrics.shots_hit = stats.get("shots_hit", 0)
        
        metrics_tracker.add(metrics)
        tb_logger.log_episode(metrics, episode)
        
        # Log progress
        if (episode + 1) % args.log_interval == 0:
            stats = metrics_tracker.get_stats()
            print(
                f"Episode {episode + 1}/{start_episode + args.episodes} | "
                f"Reward: {stats['mean_reward']:+.2f} ± {stats['std_reward']:.2f} | "
                f"Win Rate: {stats['win_rate']:.1%} | "
                f"Epsilon: {agent.epsilon:.3f} | "
                f"Buffer: {len(replay_buffer):,}"
            )
        
        # Save checkpoints
        if (episode + 1) % args.save_interval == 0:
            checkpoint_manager.save_checkpoint(agent, episode + 1)
            checkpoint_manager.save_latest(agent, episode + 1)
            
            # Check for best model
            win_rate = metrics_tracker.get_rolling_avg("win_rate", window=100)
            checkpoint_manager.save_best(agent, episode + 1, episode_reward, win_rate)
        
        # Flush TensorBoard
        if (episode + 1) % 50 == 0:
            tb_logger.flush()


def evaluate_agent(
    agent: DQNAgent,
    env: TrainingEnvironment,
    num_episodes: int,
    max_steps: int,
) -> None:
    """Evaluate trained agent.
    
    Args:
        agent: Agent to evaluate.
        env: Evaluation environment.
        num_episodes: Number of evaluation episodes.
        max_steps: Maximum steps per episode.
    """
    import numpy as np
    
    print(f"Running {num_episodes} evaluation episodes...")
    
    rewards = []
    wins = 0
    lengths = []
    
    for episode in range(num_episodes):
        state = env.reset()
        episode_reward = 0.0
        
        for step in range(max_steps):
            action = agent.predict(state, deterministic=True)
            next_state, reward, done, info = env.step(action)
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


if __name__ == "__main__":
    main()
