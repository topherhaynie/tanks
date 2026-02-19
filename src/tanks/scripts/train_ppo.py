"""PPO training script with CLI interface.

This script provides a complete training pipeline with:
- Start/stop/resume functionality
- TensorBoard logging
- Checkpoint management
- Self-play opponent pool
- Evaluation modes
- Progress monitoring

Usage:
    # Start new training
    python -m tanks.scripts.train_ppo --rollouts 100

    # Resume from checkpoint
    python -m tanks.scripts.train_ppo --resume

    # Training with TensorBoard
    python -m tanks.scripts.train_ppo --rollouts 100 --tensorboard

    # View TensorBoard
    tensorboard --logdir runs/

    # Evaluate trained agent
    python -m tanks.scripts.train_ppo --evaluate --checkpoint checkpoints/best_model.pt

Examples:
    # Basic training (100 rollouts)
    python -m tanks.scripts.train_ppo

    # Fast training (no render, larger rollout)
    python -m tanks.scripts.train_ppo --rollouts 200 --n-steps 4096

    # Debug mode (visualize agent)
    python -m tanks.scripts.train_ppo --rollouts 10 --save-interval 5

    # Resume interrupted training
    python -m tanks.scripts.train_ppo --resume

    # Evaluate best model
    python -m tanks.scripts.train_ppo --evaluate

"""

import argparse
import signal
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import torch
from tqdm import tqdm

from tanks.rl.checkpoint import CheckpointManager
from tanks.rl.metrics import MetricsTracker, TensorBoardLogger
from tanks.rl.models import PPOAgent
from tanks.rl.trainers.ppo_trainer import PPOTrainer
from tanks.training.env import TrainingEnvironment

if TYPE_CHECKING:
    from argparse import Namespace


# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum: int, frame: object) -> None:
    """Handle Ctrl+C gracefully."""
    global shutdown_requested
    print("\n\n🛑 Shutdown requested. Saving checkpoint...")
    shutdown_requested = True


def parse_args() -> "Namespace":
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Train PPO agent for tank battle",
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
        "--rollouts",
        type=int,
        default=100,
        help="Number of training rollouts (default: 100)",
    )
    parser.add_argument(
        "--n-steps",
        type=int,
        default=2048,
        help="Steps per rollout (default: 2048)",
    )
    parser.add_argument(
        "--n-epochs",
        type=int,
        default=10,
        help="Training epochs per rollout (default: 10)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Mini-batch size (default: 64)",
    )
    parser.add_argument(
        "--max-episode-steps",
        type=int,
        default=3000,
        help="Maximum steps per episode (default: 3000)",
    )

    # PPO hyperparameters
    parser.add_argument(
        "--lr",
        type=float,
        default=3e-4,
        help="Learning rate (default: 3e-4)",
    )
    parser.add_argument(
        "--gamma",
        type=float,
        default=0.99,
        help="Discount factor (default: 0.99)",
    )
    parser.add_argument(
        "--gae-lambda",
        type=float,
        default=0.95,
        help="GAE lambda parameter (default: 0.95)",
    )
    parser.add_argument(
        "--clip-epsilon",
        type=float,
        default=0.2,
        help="PPO clipping parameter (default: 0.2)",
    )
    parser.add_argument(
        "--value-coef",
        type=float,
        default=0.5,
        help="Value loss coefficient (default: 0.5)",
    )
    parser.add_argument(
        "--entropy-coef",
        type=float,
        default=0.01,
        help="Entropy bonus coefficient (default: 0.01)",
    )
    parser.add_argument(
        "--max-grad-norm",
        type=float,
        default=0.5,
        help="Gradient clipping threshold (default: 0.5)",
    )

    # Network architecture
    parser.add_argument(
        "--hidden-size",
        type=int,
        default=256,
        help="Hidden layer size (default: 256)",
    )
    parser.add_argument(
        "--separate-networks",
        action="store_true",
        help="Use separate actor/critic networks instead of shared",
    )

    # Logging and checkpointing
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=Path("checkpoints/ppo"),
        help="Checkpoint directory (default: checkpoints/ppo)",
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=10,
        help="Save checkpoint every N rollouts (default: 10)",
    )
    parser.add_argument(
        "--eval-interval",
        type=int,
        default=10,
        help="Evaluate agent every N rollouts (default: 10)",
    )
    parser.add_argument(
        "--eval-episodes",
        type=int,
        default=5,
        help="Number of evaluation episodes (default: 5)",
    )
    parser.add_argument(
        "--tensorboard",
        action="store_true",
        help="Enable TensorBoard logging",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path("runs/ppo"),
        help="TensorBoard log directory (default: runs/ppo)",
    )

    # Environment settings
    parser.add_argument(
        "--map-name",
        type=str,
        default="small_arena",
        help="Map name (default: small_arena)",
    )
    parser.add_argument(
        "--render",
        action="store_true",
        help="Render game during training (slower)",
    )
    parser.add_argument(
        "--render-interval",
        type=int,
        default=10,
        help="Render every N rollouts (default: 10)",
    )

    # Advanced options
    parser.add_argument(
        "--checkpoint",
        type=Path,
        help="Load specific checkpoint (for evaluation/resume)",
    )
    parser.add_argument(
        "--opponent-pool-size",
        type=int,
        default=5,
        help="Number of past agents to keep as opponents (default: 5)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        choices=["auto", "cpu", "cuda", "mps"],
        help="Device to train on (default: auto)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed training information",
    )

    return parser.parse_args()


def setup_device(device_str: str) -> torch.device:
    """Setup PyTorch device.

    Args:
        device_str: Device string ("auto", "cpu", "cuda", "mps").

    Returns:
        PyTorch device object.

    """
    if device_str == "auto":
        if torch.cuda.is_available():
            device = torch.device("cuda")
            print(f"🎮 Using GPU: {torch.cuda.get_device_name(0)}")
        elif torch.backends.mps.is_available():
            device = torch.device("mps")
            print("🍎 Using Apple Silicon GPU (MPS)")
        else:
            device = torch.device("cpu")
            print("💻 Using CPU")
    else:
        device = torch.device(device_str)
        print(f"🎯 Using device: {device}")

    return device


def create_agent(
    state_dim: int,
    args: "Namespace",
    device: torch.device,
) -> PPOAgent:
    """Create PPO agent with specified architecture.

    Args:
        state_dim: State space dimensionality.
        args: Parsed CLI arguments.
        device: PyTorch device.

    Returns:
        Initialized PPO agent.

    """
    # Create agent (network is created internally)
    agent = PPOAgent(
        state_dim=state_dim,
        action_dim=4,  # Continuous: move_speed, turn_rate, turret_delta, shoot_confidence
        learning_rate=args.lr,
        gamma=args.gamma,
        gae_lambda=args.gae_lambda,
        clip_epsilon=args.clip_epsilon,
        value_loss_coef=args.value_coef,
        entropy_coef=args.entropy_coef,
        max_grad_norm=args.max_grad_norm,
        device=device.type,
        network_type="separate" if args.separate_networks else "shared",
    )

    return agent


def train(args: "Namespace") -> None:
    """Main training loop.

    Args:
        args: Parsed CLI arguments.

    """
    # Setup device
    device = setup_device(args.device)

    # Set random seed if provided
    if args.seed is not None:
        torch.manual_seed(args.seed)
        print(f"🎲 Random seed set to {args.seed}")

    # Setup signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create environment
    env = TrainingEnvironment(
        map_name=args.map_name,
        max_steps=args.max_episode_steps,
        render=args.render,
    )
    state_dim = env.state_space.shape[0]

    print(f"\n{'=' * 60}")
    print("🎮 Training PPO Agent")
    print(f"{'=' * 60}")
    print(f"State dim: {state_dim}")
    print("Action space: Continuous (4D)")
    print(f"Map: {args.map_name}")
    print(f"Max episode steps: {args.max_episode_steps}")
    print(f"{'=' * 60}\n")

    # Create agent
    agent = create_agent(state_dim, args, device)

    # Setup checkpoint manager
    checkpoint_manager = CheckpointManager(
        checkpoint_dir=args.checkpoint_dir,
        max_checkpoints=args.opponent_pool_size,
    )

    # Load checkpoint if resuming or evaluating
    start_rollout = 0
    if args.resume:
        print("📂 Loading latest checkpoint...")
        checkpoint = checkpoint_manager.load_latest()
        if checkpoint is not None:
            agent.load_checkpoint(checkpoint)
            start_rollout = checkpoint.get("rollout", 0)
            print(f"✅ Resumed from rollout {start_rollout}")
        else:
            print("⚠️ No checkpoint found, starting from scratch")
    elif args.checkpoint is not None:
        print(f"📂 Loading checkpoint: {args.checkpoint}")
        checkpoint = checkpoint_manager.load(args.checkpoint)
        agent.load_checkpoint(checkpoint)
        print("✅ Checkpoint loaded")

    # Setup metrics tracking
    metrics_tracker = MetricsTracker(
        checkpoint_dir=args.checkpoint_dir / "metrics",
    )

    # Setup TensorBoard
    tensorboard_logger = None
    if args.tensorboard:
        tensorboard_logger = TensorBoardLogger(log_dir=args.log_dir)
        print(f"📊 TensorBoard logging enabled: {args.log_dir}")
        print(f"   Run: tensorboard --logdir {args.log_dir}")

    # Create trainer
    trainer = PPOTrainer(
        agent=agent,
        env=env,
        n_steps=args.n_steps,
        n_epochs=args.n_epochs,
        batch_size=args.batch_size,
        metrics_tracker=metrics_tracker,
        tensorboard_logger=tensorboard_logger,
        checkpoint_manager=checkpoint_manager,
        eval_interval=args.eval_interval,
        eval_episodes=args.eval_episodes,
        save_interval=args.save_interval,
        verbose=args.verbose,
    )

    # Training loop
    print(f"\n🚀 Starting training for {args.rollouts} rollouts")
    print(f"   Each rollout collects {args.n_steps} steps")
    print(f"   Training for {args.n_epochs} epochs per rollout")
    print(f"   Mini-batch size: {args.batch_size}")
    print("   Press Ctrl+C to stop and save\n")

    # Create progress bar
    pbar = tqdm(
        range(start_rollout, start_rollout + args.rollouts),
        desc="Training PPO",
        unit="rollout",
        ncols=100,
    )

    try:
        for rollout in pbar:
            if shutdown_requested:
                break

            # Render periodically
            should_render = args.render and (rollout % args.render_interval == 0)
            trainer.env.render = should_render

            # Train one rollout
            trainer.train(num_rollouts=1)

            # Update progress bar
            stats = metrics_tracker.get_recent_stats(window=10)
            pbar.set_postfix(
                {
                    "return": f"{stats['episode_return']:+.1f}",
                    "hit_rate": f"{stats['hit_rate']:.1%}",
                    "entropy": f"{stats['entropy']:.2f}",
                    "p_loss": f"{stats['policy_loss']:.3f}",
                }
            )

            # Detailed progress update
            if (rollout + 1) % 10 == 0:
                pbar.write(
                    f"\n{'=' * 80}\n"
                    f"Rollout {rollout + 1}/{start_rollout + args.rollouts}\n"
                    f"{'=' * 80}\n"
                    f"📈 Return: {stats['episode_return']:+.2f} | Hit Rate: {stats['hit_rate']:.1%}\n"
                    f"💥 Damage: {stats['damage_dealt']:.1f} | Length: {stats['episode_length']:.0f}\n"
                    f"🔄 Policy Loss: {stats['policy_loss']:.4f} | Value Loss: {stats['value_loss']:.4f}\n"
                    f"🎲 Entropy: {stats['entropy']:.4f} | Clip Frac: {stats.get('clip_fraction', 0):.2f}\n"
                    f"{'=' * 80}\n",
                )

    except KeyboardInterrupt:
        print("\n\n⚠️ Training interrupted by user")

    finally:
        # Save final checkpoint
        print("\n💾 Saving final checkpoint...")
        checkpoint = agent.create_checkpoint()
        checkpoint["rollout"] = rollout + 1
        checkpoint_manager.save(checkpoint, f"final_rollout_{rollout + 1}.pt")
        print("✅ Final checkpoint saved")

        # Export metrics
        print("📊 Exporting metrics...")
        metrics_tracker.export_to_csv()
        print("✅ Metrics exported")

        # Close TensorBoard
        if tensorboard_logger is not None:
            tensorboard_logger.close()

        # Close environment
        env.close()

        print(f"\n{'=' * 60}")
        print("🎉 Training complete!")
        print(f"{'=' * 60}")
        print(f"📂 Checkpoints saved to: {args.checkpoint_dir}")
        print(f"📊 Metrics saved to: {args.checkpoint_dir / 'metrics'}")
        if tensorboard_logger is not None:
            print(f"📈 TensorBoard logs: {args.log_dir}")
        print(f"{'=' * 60}\n")


def evaluate(args: "Namespace") -> None:
    """Evaluate trained agent.

    Args:
        args: Parsed CLI arguments.

    """
    # Setup device
    device = setup_device(args.device)

    # Create environment
    env = TrainingEnvironment(
        map_name=args.map_name,
        max_steps=args.max_episode_steps,
        render=True,  # Always render during evaluation
    )
    state_dim = env.state_space.shape[0]

    print(f"\n{'=' * 60}")
    print("🎯 Evaluating PPO Agent")
    print(f"{'=' * 60}")

    # Create agent
    agent = create_agent(state_dim, args, device)

    # Load checkpoint
    checkpoint_manager = CheckpointManager(checkpoint_dir=args.checkpoint_dir)

    if args.checkpoint is not None:
        print(f"📂 Loading checkpoint: {args.checkpoint}")
        checkpoint = checkpoint_manager.load(args.checkpoint)
    else:
        print("📂 Loading best checkpoint...")
        checkpoint = checkpoint_manager.load_best()

    if checkpoint is None:
        print("❌ No checkpoint found!")
        sys.exit(1)

    agent.load_checkpoint(checkpoint)
    print("✅ Checkpoint loaded")

    # Create trainer for evaluation
    trainer = PPOTrainer(
        agent=agent,
        env=env,
        n_steps=args.n_steps,
        eval_episodes=args.eval_episodes,
    )

    # Run evaluation
    print(f"\n🎮 Running {args.eval_episodes} evaluation episodes...")
    print("   Press Ctrl+C to stop\n")

    try:
        eval_metrics = trainer.evaluate()

        print(f"\n{'=' * 60}")
        print("📊 Evaluation Results")
        print(f"{'=' * 60}")
        print(f"📈 Average Return: {eval_metrics.episode_return:.2f}")
        print(f"⏱️  Average Length: {eval_metrics.episode_length:.1f}")
        print(f"💥 Average Damage: {eval_metrics.damage_dealt:.1f}")
        print(f"🎯 Hit Rate: {eval_metrics.hit_rate:.1%}")
        print(f"🏆 Win Rate: {eval_metrics.win_rate:.1%}")
        print(f"☠️  Deaths: {eval_metrics.deaths:.1f}")
        print(f"{'=' * 60}\n")

    except KeyboardInterrupt:
        print("\n\n⚠️ Evaluation interrupted")

    finally:
        env.close()


def main() -> None:
    """Main entry point."""
    args = parse_args()

    if args.evaluate:
        evaluate(args)
    else:
        train(args)


if __name__ == "__main__":
    main()
