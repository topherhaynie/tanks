"""Test PPO implementation components.

Tests:
1. Actor-Critic Network forward pass
2. PPO Agent initialization and action sampling
3. GAE computation
4. PPO train step
5. Checkpoint save/load
"""

import numpy as np
import torch

from tanks.rl.models import ActorCriticNetwork, PPOAgent


def test_actor_critic_network() -> None:
    """Test Actor-Critic network forward pass."""
    print("\n" + "=" * 60)
    print("Test 1: Actor-Critic Network")
    print("=" * 60)

    # Create network
    network = ActorCriticNetwork(
        state_dim=78,
        action_dim=4,
        hidden_dims=[128, 128],
        head_dim=64,
    )

    # Test single state forward pass
    state = torch.randn(1, 78)
    action_mean, action_std, value = network(state)

    print("✓ Forward pass successful")
    print(f"  Action mean shape: {action_mean.shape}")
    print(f"  Action std shape: {action_std.shape}")
    print(f"  Value shape: {value.shape}")

    assert action_mean.shape == (1, 4), f"Expected (1, 4), got {action_mean.shape}"
    assert action_std.shape == (1, 4), f"Expected (1, 4), got {action_std.shape}"
    assert value.shape == (1, 1), f"Expected (1, 1), got {value.shape}"

    # Test batch forward pass
    batch = torch.randn(32, 78)
    action_mean, action_std, value = network(batch)

    print("✓ Batch forward pass successful")
    print(f"  Batch action mean shape: {action_mean.shape}")
    print(f"  Batch value shape: {value.shape}")

    assert action_mean.shape == (32, 4)
    assert value.shape == (32, 1)

    print("✅ Actor-Critic Network test passed!")


def test_ppo_agent_get_action() -> None:
    """Test PPO agent action sampling."""
    print("\n" + "=" * 60)
    print("Test 2: PPO Agent Action Sampling")
    print("=" * 60)

    # Create agent
    agent = PPOAgent(
        state_dim=78,
        action_dim=4,
        learning_rate=3e-4,
        gamma=0.99,
        gae_lambda=0.95,
        clip_epsilon=0.2,
        value_loss_coef=0.5,
        entropy_coef=0.01,
    )

    # Test stochastic action
    state = np.random.randn(78).astype(np.float32)
    action, log_prob, value = agent.get_action(state, deterministic=False)

    print("✓ Stochastic action sampling successful")
    print(f"  Action shape: {action.shape}")
    print(f"  Action values: {action}")
    print(f"  Log prob: {log_prob:.4f}")
    print(f"  Value: {value:.4f}")

    assert action.shape == (4,), f"Expected (4,), got {action.shape}"
    assert isinstance(log_prob, float)
    assert isinstance(value, float)

    # Note: Sampled actions can be outside [-1, 1] range even though action mean
    # is constrained by Tanh. This is expected in PPO - the mean is bounded, but
    # sampling with std can produce values outside the range. Environment should
    # handle clamping if needed.

    # Test deterministic action
    action_det, log_prob_det, value_det = agent.get_action(state, deterministic=True)

    print("✓ Deterministic action successful")
    print(f"  Deterministic action: {action_det}")

    # Deterministic action should be the mean (in [-1, 1] due to Tanh)
    assert action_det.shape == (4,)
    assert action_det.min() >= -1.0 and action_det.max() <= 1.0, "Deterministic actions out of range"

    print("✅ PPO Agent action sampling test passed!")


def test_gae_computation() -> None:
    """Test Generalized Advantage Estimation."""
    print("\n" + "=" * 60)
    print("Test 3: GAE Computation")
    print("=" * 60)

    # Create agent
    agent = PPOAgent(state_dim=78, action_dim=4, gamma=0.99, gae_lambda=0.95)

    # Create sample trajectory
    n_steps = 10
    rewards = np.array([1.0, 0.5, -0.5, 0.0, 2.0, 1.0, 0.0, -1.0, 1.5, 0.5])
    values = np.array([0.5, 0.4, 0.3, 0.2, 0.6, 0.5, 0.3, 0.2, 0.4, 0.3])
    dones = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 1])  # Episode ends at last step
    next_value = 0.0  # Terminal state value

    # Compute GAE advantages
    advantages, returns = agent.compute_gae(rewards, values, dones, next_value)

    print("✓ GAE computation successful")
    print(f"  Advantages shape: {advantages.shape}")
    print(f"  Returns shape: {returns.shape}")
    print(f"  Mean advantage: {advantages.mean():.4f}")
    print(f"  Mean return: {returns.mean():.4f}")
    print(f"  Advantage range: [{advantages.min():.4f}, {advantages.max():.4f}]")

    assert advantages.shape == (n_steps,)
    assert returns.shape == (n_steps,)

    # Returns should be values + advantages
    expected_values = values + advantages
    np.testing.assert_allclose(returns, expected_values, rtol=1e-5)

    print("✅ GAE computation test passed!")


def test_ppo_train_step() -> None:
    """Test PPO training step."""
    print("\n" + "=" * 60)
    print("Test 4: PPO Train Step")
    print("=" * 60)

    # Create agent
    agent = PPOAgent(
        state_dim=78,
        action_dim=4,
        learning_rate=3e-4,
        gamma=0.99,
        clip_epsilon=0.2,
        value_loss_coef=0.5,
        entropy_coef=0.01,
    )

    # Create sample batch
    batch_size = 32
    states = np.random.randn(batch_size, 78).astype(np.float32)
    actions = np.random.randn(batch_size, 4).astype(np.float32)
    old_log_probs = np.random.randn(batch_size).astype(np.float32)
    advantages = np.random.randn(batch_size).astype(np.float32)
    returns = np.random.randn(batch_size).astype(np.float32)

    # Perform training step
    loss_dict = agent.train_step(states, actions, old_log_probs, advantages, returns)

    print("✓ Training step successful")
    print(f"  Policy loss: {loss_dict['policy_loss']:.4f}")
    print(f"  Value loss: {loss_dict['value_loss']:.4f}")
    print(f"  Entropy: {loss_dict['entropy']:.4f}")
    print(f"  Total loss: {loss_dict['total_loss']:.4f}")

    # Check loss keys
    assert "policy_loss" in loss_dict
    assert "value_loss" in loss_dict
    assert "entropy" in loss_dict
    assert "total_loss" in loss_dict
    assert "clip_fraction" in loss_dict

    # Losses should be finite
    for key, value in loss_dict.items():
        assert not np.isnan(value), f"{key} is NaN"
        assert not np.isinf(value), f"{key} is Inf"

    print("✅ PPO train step test passed!")


def test_checkpoint_save_load() -> None:
    """Test checkpoint saving and loading."""
    print("\n" + "=" * 60)
    print("Test 5: Checkpoint Save/Load")
    print("=" * 60)

    # Create agent
    agent = PPOAgent(state_dim=78, action_dim=4, learning_rate=3e-4)

    # Get initial first parameter value
    first_param_name = list(agent.network.state_dict().keys())[0]
    initial_value = agent.network.state_dict()[first_param_name].clone()

    print(f"  Initial value sample: {initial_value.flatten()[:4]}")

    # Create checkpoint
    checkpoint = agent.create_checkpoint()

    print("✓ Checkpoint created")
    print(f"  Keys: {list(checkpoint.keys())}")

    assert "network_state_dict" in checkpoint
    assert "optimizer_state_dict" in checkpoint

    # Modify network weights
    for param in agent.network.parameters():
        param.data.fill_(1.0)

    modified_value = agent.network.state_dict()[first_param_name]
    print(f"  Modified value sample: {modified_value.flatten()[:4]}")

    # Load checkpoint
    agent.load_checkpoint(checkpoint)

    print("✓ Checkpoint loaded")

    restored_value = agent.network.state_dict()[first_param_name]
    print(f"  Restored value sample: {restored_value.flatten()[:4]}")

    # Verify weights restored
    for key, initial_param in checkpoint["network_state_dict"].items():
        loaded_param = agent.network.state_dict()[key]
        torch.testing.assert_close(loaded_param, initial_param)

    print("✅ Checkpoint save/load test passed!")


def test_ppo_integration() -> None:
    """Integration test: sample trajectory and train."""
    print("\n" + "=" * 60)
    print("Test 6: PPO Integration")
    print("=" * 60)

    # Create agent
    agent = PPOAgent(
        state_dim=78,
        action_dim=4,
        learning_rate=3e-4,
        gamma=0.99,
        gae_lambda=0.95,
    )

    # Simulate a short trajectory
    n_steps = 20
    states = []
    actions_list = []
    log_probs_list = []
    rewards = []
    values_list = []
    dones = []

    for i in range(n_steps):
        state = np.random.randn(78).astype(np.float32)
        action, log_prob, value = agent.get_action(state, deterministic=False)

        states.append(state)
        actions_list.append(action)
        log_probs_list.append(log_prob)
        values_list.append(value)
        rewards.append(np.random.randn())
        dones.append(1 if i == n_steps - 1 else 0)

    print(f"✓ Collected {n_steps} steps of experience")

    # Convert to numpy arrays
    states_np = np.array(states, dtype=np.float32)
    actions_np = np.array(actions_list, dtype=np.float32)
    old_log_probs_np = np.array(log_probs_list, dtype=np.float32)
    rewards_np = np.array(rewards, dtype=np.float32)
    values_np = np.array(values_list, dtype=np.float32)
    dones_np = np.array(dones, dtype=np.float32)

    # Compute advantages
    next_value = 0.0  # Terminal state
    advantages, returns = agent.compute_gae(rewards_np, values_np, dones_np, next_value)

    print("✓ Computed GAE advantages")

    # Train for a few steps
    n_epochs = 3
    for epoch in range(n_epochs):
        loss_dict = agent.train_step(
            states_np,
            actions_np,
            old_log_probs_np,
            advantages,
            returns,
        )
        print(f"  Epoch {epoch + 1}: Loss = {loss_dict['total_loss']:.4f}")

    print("✅ PPO integration test passed!")


def main() -> None:
    """Run all PPO tests."""
    print("\n" + "=" * 60)
    print("🧪 Testing PPO Implementation")
    print("=" * 60)

    try:
        test_actor_critic_network()
        test_ppo_agent_get_action()
        test_gae_computation()
        test_ppo_train_step()
        test_checkpoint_save_load()
        test_ppo_integration()

        print("\n" + "=" * 60)
        print("🎉 All PPO tests passed!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()
