"""Test script for Phase 6.2 - DQN Implementation.

This script verifies that all DQN components work together:
- DQN network forward pass
- Replay buffer add/sample
- DQN agent training step
- DQN trainer integration with environment
"""

import numpy as np
import torch

print("=" * 60)
print("Phase 6.2 Test - DQN Implementation")
print("=" * 60)

# Test 1: Import all modules
print("\n1. Testing imports...")
try:
    from tanks.rl.models import DQNAgent, DQNNetwork, DuelingDQNNetwork
    from tanks.rl.replay_buffer import ReplayBuffer
    from tanks.training.env import TrainingEnvironment

    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    raise

# Test 2: DQN Network
print("\n2. Testing DQN Network...")
try:
    state_dim = 78
    action_dim = 12
    batch_size = 4

    # Standard DQN
    dqn = DQNNetwork(state_dim, action_dim)
    states = torch.randn(batch_size, state_dim)
    q_values = dqn(states)

    assert q_values.shape == (batch_size, action_dim), (
        f"Expected shape ({batch_size}, {action_dim}), got {q_values.shape}"
    )
    print(f"  ✓ DQN forward pass: {states.shape} → {q_values.shape}")

    # Dueling DQN
    dueling = DuelingDQNNetwork(state_dim, action_dim)
    q_values_dueling = dueling(states)

    assert q_values_dueling.shape == (batch_size, action_dim), f"Expected shape ({batch_size}, {action_dim})"
    print(f"  ✓ Dueling DQN forward pass: {states.shape} → {q_values_dueling.shape}")

    # Single state (no batch)
    single_state = torch.randn(state_dim)
    single_q = dqn(single_state)
    assert single_q.shape == (action_dim,), f"Expected shape ({action_dim},), got {single_q.shape}"
    print(f"  ✓ Single state forward pass: {single_state.shape} → {single_q.shape}")

except Exception as e:
    print(f"  ✗ DQN Network test failed: {e}")
    raise

# Test 3: Replay Buffer
print("\n3. Testing Replay Buffer...")
try:
    buffer = ReplayBuffer(capacity=1000, state_dim=state_dim)

    # Add experiences
    for i in range(100):
        state = np.random.randn(state_dim).astype(np.float32)
        action = np.random.randint(0, action_dim)
        reward = np.random.randn() * 10
        next_state = np.random.randn(state_dim).astype(np.float32)
        done = bool(np.random.random() < 0.1)

        buffer.add(state, action, reward, next_state, done)

    assert len(buffer) == 100, f"Expected buffer size 100, got {len(buffer)}"
    print("  ✓ Added 100 experiences to buffer")

    # Sample batch
    batch_size = 32
    states, actions, rewards, next_states, dones = buffer.sample(batch_size)

    assert states.shape == (batch_size, state_dim), f"Expected states shape ({batch_size}, {state_dim})"
    assert actions.shape == (batch_size,), f"Expected actions shape ({batch_size},)"
    assert rewards.shape == (batch_size,), f"Expected rewards shape ({batch_size},)"
    assert next_states.shape == (batch_size, state_dim), f"Expected next_states shape ({batch_size}, {state_dim})"
    assert dones.shape == (batch_size,), f"Expected dones shape ({batch_size},)"

    print(f"  ✓ Sampled batch of {batch_size} experiences")
    print(f"    States: {states.shape}, Actions: {actions.shape}, Rewards: {rewards.shape}")

    # Test circular buffer (overfill)
    for i in range(1500):  # Exceed capacity
        buffer.add(
            np.random.randn(state_dim).astype(np.float32),
            np.random.randint(0, action_dim),
            float(np.random.randn()),
            np.random.randn(state_dim).astype(np.float32),
            bool(np.random.random() < 0.1),
        )

    assert len(buffer) == 1000, f"Expected buffer size 1000 (capacity), got {len(buffer)}"
    print("  ✓ Buffer correctly limits to capacity (1000)")

except Exception as e:
    print(f"  ✗ Replay Buffer test failed: {e}")
    raise

# Test 4: DQN Agent
print("\n4. Testing DQN Agent...")
try:
    # Create agent
    agent = DQNAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        learning_rate=1e-3,
        epsilon=0.5,
    )

    print(f"  ✓ Created DQN agent on device: {agent.device}")
    print(f"    State dim: {state_dim}, Action dim: {action_dim}")
    print(f"    Epsilon: {agent.epsilon}, Gamma: {agent.gamma}")

    # Test action selection
    test_state = np.random.randn(state_dim).astype(np.float32)

    # Deterministic (greedy)
    action_det = agent.predict(test_state, deterministic=True)
    assert isinstance(action_det, int), f"Expected int action, got {type(action_det)}"
    assert 0 <= action_det < action_dim, f"Action {action_det} out of range [0, {action_dim})"
    print(f"  ✓ Deterministic action: {action_det}")

    # Epsilon-greedy
    action_explore = agent.select_action(test_state)
    assert isinstance(action_explore, int), f"Expected int action, got {type(action_explore)}"
    assert 0 <= action_explore < action_dim, f"Action {action_explore} out of range"
    print(f"  ✓ Epsilon-greedy action: {action_explore}")

    # Test training step
    batch_size = 32
    states_np = np.random.randn(batch_size, state_dim).astype(np.float32)
    actions_np = np.random.randint(0, action_dim, size=batch_size)
    rewards_np = np.random.randn(batch_size).astype(np.float32) * 10
    next_states_np = np.random.randn(batch_size, state_dim).astype(np.float32)
    dones_np = np.random.random(batch_size) < 0.1

    loss = agent.train_step(states_np, actions_np, rewards_np, next_states_np, dones_np)

    assert isinstance(loss, float), f"Expected float loss, got {type(loss)}"
    assert not np.isnan(loss), "Loss is NaN!"
    assert not np.isinf(loss), "Loss is infinite!"
    print(f"  ✓ Training step: loss = {loss:.6f}")

    # Test target network update
    old_target_params = [p.clone() for p in agent.target_net.parameters()]
    agent.update_target_network()
    new_target_params = [p for p in agent.target_net.parameters()]

    # Verify parameters changed
    changed = any(not torch.equal(old, new) for old, new in zip(old_target_params, new_target_params, strict=False))
    assert changed, "Target network parameters did not update"
    print("  ✓ Target network updated")

    # Test epsilon decay
    old_epsilon = agent.epsilon
    agent.decay_epsilon()
    assert agent.epsilon < old_epsilon, "Epsilon did not decay"
    print(f"  ✓ Epsilon decay: {old_epsilon:.3f} → {agent.epsilon:.3f}")

except Exception as e:
    print(f"  ✗ DQN Agent test failed: {e}")
    raise

# Test 5: Integration with TrainingEnvironment
print("\n5. Testing TrainingEnvironment integration...")
try:
    # Create training environment (uses default simple arena)
    env = TrainingEnvironment(
        max_steps=100,
    )

    print("  ✓ Created training environment")

    # Create fresh agent for this test
    agent = DQNAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        learning_rate=1e-3,
        epsilon=1.0,  # Full exploration for testing
    )

    # Run a few steps
    state = env.reset()
    total_reward = 0.0

    for step in range(10):
        action = agent.select_action(state)
        next_state, reward, done, info = env.step(action)

        total_reward += reward
        state = next_state

        if done:
            break

    print(f"  ✓ Ran {step + 1} steps, cumulative reward: {total_reward:+.2f}")

    env.close()

except Exception as e:
    print(f"  ✗ TrainingEnvironment integration failed: {e}")
    raise

# Test 6: Save/Load
print("\n6. Testing agent save/load...")
try:
    import os
    import tempfile

    # Create agent
    agent = DQNAgent(
        state_dim=state_dim,
        action_dim=action_dim,
        epsilon=0.456,
    )

    # Get prediction before save
    test_state = np.random.randn(state_dim).astype(np.float32)
    action_before = agent.predict(test_state, deterministic=True)
    epsilon_before = agent.epsilon

    # Save
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "test_agent.pt")
        agent.save(save_path)
        print(f"  ✓ Saved agent to {save_path}")

        # Load
        loaded_agent = DQNAgent.load(save_path)
        print(f"  ✓ Loaded agent from {save_path}")

        # Verify loaded agent
        action_after = loaded_agent.predict(test_state, deterministic=True)
        epsilon_after = loaded_agent.epsilon

        assert action_before == action_after, f"Actions differ: {action_before} vs {action_after}"
        assert abs(epsilon_before - epsilon_after) < 1e-6, f"Epsilon differs: {epsilon_before} vs {epsilon_after}"

        print(f"  ✓ Loaded agent produces same outputs (action={action_after}, epsilon={epsilon_after:.3f})")

except Exception as e:
    print(f"  ✗ Save/Load test failed: {e}")
    raise

# Summary
print("\n" + "=" * 60)
print("✓ All Phase 6.2 tests passed!")
print("=" * 60)
print("\nDQN components ready:")
print("  • DQN Network (standard + dueling)")
print("  • Replay Buffer (uniform sampling)")
print("  • DQN Agent (train_step, target network, epsilon-greedy)")
print("  • TrainingEnvironment integration")
print("  • Save/Load checkpoints")
print("\nReady for DQN training!")
