"""Complete training regime script.

Run the full training pipeline from beginner to expert:
- Phase A: Map-specific curriculum (6 stages)
- Phase B: Random map generalization (self-play)
- Phase C: Survival training (1v2, 1v3)

Usage:
    python -m tanks.scripts.train_regime --agent dqn --episodes-per-stage 150
    python -m tanks.scripts.train_regime --agent ppo --skip-phase-c
    python -m tanks.scripts.train_regime --agent dqn --config config.json
"""

import argparse
import json
from pathlib import Path

import torch

from tanks.rl.models.agent import DQNAgent, PPOAgent
from tanks.rl.trainers.orchestrator import TrainingOrchestrator


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run complete training regime for RL agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train DQN agent through full regime (default)
  python -m tanks.scripts.train_regime --agent dqn

    # Non-interactive start (for overnight runs)
    python -m tanks.scripts.train_regime --agent dqn --config regime_m4_competitive.json --yes
  
  # Train PPO agent, skip survival phase
  python -m tanks.scripts.train_regime --agent ppo --skip-phase-c
  
  # Custom configuration
  python -m tanks.scripts.train_regime --agent dqn --episodes-per-stage 200 --exploration-weight 10.0
  
  # Resume from checkpoint
  python -m tanks.scripts.train_regime --agent dqn --resume checkpoints/regime/phase_a/checkpoints/latest_model.pt

    # Resume from most recent checkpoint under checkpoint dir
    python -m tanks.scripts.train_regime --agent dqn --checkpoint-dir checkpoints/regime --resume-latest
  
  # Load regime config from JSON
  python -m tanks.scripts.train_regime --agent ppo --config my_regime.json
        """,
    )

    # Agent configuration
    parser.add_argument(
        "--agent",
        type=str,
        choices=["dqn", "ppo"],
        default="dqn",
        help="Agent type to train (default: dqn)",
    )

    parser.add_argument(
        "--resume",
        type=str,
        default=None,
        help="Resume from checkpoint path",
    )

    parser.add_argument(
        "--resume-latest",
        action="store_true",
        help="Auto-resume from most recent checkpoint under --checkpoint-dir",
    )

    # Regime configuration
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="JSON file with regime configuration",
    )

    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="checkpoints/regime",
        help="Base directory for checkpoints (default: checkpoints/regime)",
    )

    # Phase toggles
    parser.add_argument(
        "--skip-phase-a",
        action="store_true",
        help="Skip Phase A (map curriculum)",
    )

    parser.add_argument(
        "--skip-phase-b",
        action="store_true",
        help="Skip Phase B (random map self-play)",
    )

    parser.add_argument(
        "--skip-phase-c",
        action="store_true",
        help="Skip Phase C (survival training)",
    )

    # Episode configuration
    parser.add_argument(
        "--episodes-per-stage",
        type=int,
        default=150,
        help="Episodes per curriculum stage (default: 150)",
    )

    parser.add_argument(
        "--phase-b-episodes",
        type=int,
        default=500,
        help="Episodes for Phase B (default: 500)",
    )

    parser.add_argument(
        "--phase-c-episodes",
        type=int,
        default=200,
        help="Episodes per survival stage (default: 200)",
    )

    parser.add_argument(
        "--max-steps-per-episode",
        type=int,
        default=3000,
        help="Maximum environment steps per episode (default: 3000)",
    )

    # Reward tuning
    parser.add_argument(
        "--exploration-weight",
        type=float,
        default=8.0,
        help="Weight for exploration rewards (default: 8.0)",
    )

    # Training parameters
    parser.add_argument(
        "--save-interval",
        type=int,
        default=50,
        help="Episodes between checkpoint saves (default: 50)",
    )

    parser.add_argument(
        "--log-interval",
        type=int,
        default=10,
        help="Episodes between progress logs (default: 10)",
    )

    # Agent hyperparameters (DQN)
    parser.add_argument(
        "--dqn-lr",
        type=float,
        default=1e-4,
        help="DQN learning rate (default: 1e-4)",
    )

    parser.add_argument(
        "--dqn-gamma",
        type=float,
        default=0.99,
        help="DQN discount factor (default: 0.99)",
    )

    parser.add_argument(
        "--dqn-epsilon-start",
        type=float,
        default=1.0,
        help="DQN starting epsilon (default: 1.0)",
    )

    parser.add_argument(
        "--dqn-epsilon-end",
        type=float,
        default=0.01,
        help="DQN final epsilon (default: 0.01)",
    )

    parser.add_argument(
        "--dqn-epsilon-decay",
        type=float,
        default=0.995,
        help="DQN epsilon decay multiplier per episode (default: 0.995)",
    )

    # Agent hyperparameters (PPO)
    parser.add_argument(
        "--ppo-lr",
        type=float,
        default=3e-4,
        help="PPO learning rate (default: 3e-4)",
    )

    parser.add_argument(
        "--ppo-gamma",
        type=float,
        default=0.99,
        help="PPO discount factor (default: 0.99)",
    )

    parser.add_argument(
        "--ppo-clip",
        type=float,
        default=0.2,
        help="PPO clip parameter (default: 0.2)",
    )

    # Device
    parser.add_argument(
        "--device",
        type=str,
        choices=["cpu", "cuda", "mps", "auto"],
        default="auto",
        help="Training device: cpu, cuda (NVIDIA), mps (Apple Silicon), or auto (default: auto)",
    )

    # Misc
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output",
    )

    parser.add_argument(
        "--yes",
        action="store_true",
        help="Start immediately without confirmation prompt",
    )

    return parser.parse_args()


def load_regime_config(config_path: str) -> dict:
    """Load regime configuration from JSON file.

    Args:
        config_path: Path to JSON config file.

    Returns:
        Configuration dictionary.

    """
    with open(config_path) as f:
        return json.load(f)


def setup_device(device_str: str) -> torch.device:
    """Setup training device (CPU, CUDA, or MPS).

    Args:
        device_str: Device string ("cpu", "cuda", "mps", or "auto").

    Returns:
        torch.device object.

    """
    if device_str == "auto":
        if torch.cuda.is_available():
            device = torch.device("cuda")
            print(f"Using NVIDIA GPU: {torch.cuda.get_device_name(0)}")
        elif torch.backends.mps.is_available():
            device = torch.device("mps")
            print("Using Apple Silicon GPU (Metal Performance Shaders)")
        else:
            device = torch.device("cpu")
            print("Using CPU (no GPU available)")
    else:
        device = torch.device(device_str)
        print(f"Using device: {device_str}")

    return device


def create_regime_config(args) -> dict:
    """Create regime configuration from command line args.

    Args:
        args: Parsed command line arguments.

    Returns:
        Regime configuration dictionary.

    """
    if args.config:
        # Load from JSON file
        return load_regime_config(args.config)

    # Build from command line args
    return {
        "phase_a_enabled": not args.skip_phase_a,
        "phase_b_enabled": not args.skip_phase_b,
        "phase_c_enabled": not args.skip_phase_c,
        "max_steps_per_episode": args.max_steps_per_episode,
        "phase_a_episodes_per_stage": args.episodes_per_stage,
        "phase_b_episodes": args.phase_b_episodes,
        "phase_c_episodes_per_stage": args.phase_c_episodes,
        "exploration_weight": args.exploration_weight,
        "save_interval": args.save_interval,
        "log_interval": args.log_interval,
    }


def resolve_resume_checkpoint(args) -> str | None:
    """Resolve checkpoint path to resume from.

    Priority:
    1) Explicit --resume path (if provided)
    2) Auto-detected newest checkpoint if --resume-latest is set

    Args:
        args: Parsed command line arguments.

    Returns:
        Resolved checkpoint path, or None when starting fresh.

    Raises:
        ValueError: If resume options conflict or no checkpoint is found.

    """
    if args.resume and args.resume_latest:
        msg = "Use only one of --resume or --resume-latest"
        raise ValueError(msg)

    if args.resume:
        checkpoint_path = Path(args.resume)
        if not checkpoint_path.exists():
            msg = f"Checkpoint not found: {checkpoint_path}"
            raise ValueError(msg)
        return str(checkpoint_path)

    if not args.resume_latest:
        return None

    checkpoint_dir = Path(args.checkpoint_dir)
    if not checkpoint_dir.exists():
        msg = f"Checkpoint directory not found: {checkpoint_dir}"
        raise ValueError(msg)

    candidates: list[Path] = []
    candidates.extend(checkpoint_dir.rglob("latest_model.pt"))
    candidates.extend(checkpoint_dir.rglob("best_model.pt"))

    if not candidates:
        msg = f"No checkpoints found under: {checkpoint_dir}"
        raise ValueError(msg)

    def is_compatible(path: Path) -> bool:
        try:
            checkpoint = torch.load(path, map_location="cpu", weights_only=True)
        except Exception:
            return False

        if args.agent == "dqn":
            return "policy_net_state_dict" in checkpoint and "target_net_state_dict" in checkpoint

        return "network_state_dict" in checkpoint

    compatible_candidates = [path for path in candidates if is_compatible(path)]

    if not compatible_candidates:
        msg = f"No {args.agent.upper()}-compatible checkpoints found under: {checkpoint_dir}"
        raise ValueError(msg)

    newest = max(compatible_candidates, key=lambda path: path.stat().st_mtime)
    return str(newest)


def create_agent(args, device: torch.device, resume_checkpoint: str | None = None) -> DQNAgent | PPOAgent:
    """Create agent from command line args.

    Args:
        args: Parsed command line arguments.
        device: Torch device for training.

    Returns:
        Initialized agent (DQN or PPO).

    """
    if resume_checkpoint:
        # Load from checkpoint
        if args.agent == "dqn":
            agent = DQNAgent.load(resume_checkpoint, device=device.type)
        else:
            agent = PPOAgent.load(resume_checkpoint, device=device.type)

        print(f"Resumed agent from: {resume_checkpoint}")
        return agent

    # Create new agent
    if args.agent == "dqn":
        agent = DQNAgent(
            state_dim=78,  # Standard state encoding
            action_dim=12,  # Standard discrete action space
            learning_rate=args.dqn_lr,
            gamma=args.dqn_gamma,
            epsilon=args.dqn_epsilon_start,
            epsilon_min=args.dqn_epsilon_end,
            epsilon_decay=args.dqn_epsilon_decay,
            device=device.type,
        )
        print(f"Created new DQN agent (lr={args.dqn_lr}, gamma={args.dqn_gamma}, device={device})")
    else:
        agent = PPOAgent(
            state_dim=78,
            action_dim=4,
            learning_rate=args.ppo_lr,
            gamma=args.ppo_gamma,
            clip_epsilon=args.ppo_clip,
            device=device.type,
        )
        print(
            f"Created new PPO agent (lr={args.ppo_lr}, gamma={args.ppo_gamma}, clip={args.ppo_clip}, device={device})",
        )

    return agent


def main():
    """Main training regime entry point."""
    args = parse_args()

    # Print banner
    print("\n" + "=" * 80)
    print("TANKS RL TRAINING REGIME".center(80))
    print("=" * 80 + "\n")

    # Setup training device
    device = setup_device(args.device)

    # Resolve resume checkpoint (explicit path or auto-detected latest)
    try:
        resume_checkpoint = resolve_resume_checkpoint(args)
    except ValueError as error:
        print(f"Error: {error}")
        return

    # Create agent
    agent = create_agent(args, device, resume_checkpoint)

    # Create regime config
    regime_config = create_regime_config(args)

    # Print regime plan
    print("Training Plan:")
    if regime_config["phase_a_enabled"]:
        episodes = regime_config["phase_a_episodes_per_stage"] * 6  # 6 stages
        print(f"  Phase A: Map Curriculum ({episodes} episodes across 6 stages)")
    if regime_config["phase_b_enabled"]:
        print(f"  Phase B: Random Map Self-Play ({regime_config['phase_b_episodes']} episodes)")
    if regime_config["phase_c_enabled"]:
        episodes = regime_config["phase_c_episodes_per_stage"] * 3  # 3 survival stages
        print(f"  Phase C: Survival Training ({episodes} episodes across 3 stages)")

    total_episodes = 0
    if regime_config["phase_a_enabled"]:
        total_episodes += regime_config["phase_a_episodes_per_stage"] * 6
    if regime_config["phase_b_enabled"]:
        total_episodes += regime_config["phase_b_episodes"]
    if regime_config["phase_c_enabled"]:
        total_episodes += regime_config["phase_c_episodes_per_stage"] * 3

    print(f"\nEstimated Total Episodes: {total_episodes}")
    print(f"Checkpoint Directory: {args.checkpoint_dir}")
    print(f"Device: {device}")
    print(f"Exploration Weight: {regime_config['exploration_weight']}")
    print("\n" + "=" * 80 + "\n")

    # Confirm start
    if not args.yes:
        response = input("Start training regime? [y/N]: ")
        if response.lower() != "y":
            print("Training cancelled.")
            return
    else:
        print("Auto-confirm enabled (--yes). Starting training...")

    # Create orchestrator
    orchestrator = TrainingOrchestrator(
        agent=agent,
        base_checkpoint_dir=args.checkpoint_dir,
        regime_config=regime_config,
        verbose=not args.quiet,
    )

    # Run full regime
    try:
        orchestrator.run_full_regime()
    except KeyboardInterrupt:
        print("\nTraining interrupted by user (Ctrl+C).")
        print("Recent periodic checkpoints remain in your checkpoint directory.")
        return

    # Final summary
    print("\n" + "=" * 80)
    print("TRAINING REGIME COMPLETE!".center(80))
    print("=" * 80)
    print(f"\nFinal agent checkpoint: {args.checkpoint_dir}/best_model.pt")
    print(f"Full results: {args.checkpoint_dir}/final_report.txt")
    print("\nAgent is ready for deployment and competitive play!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
