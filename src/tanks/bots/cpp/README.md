# C++ Bot Interface

This directory will contain the C++ bot interface for creating C++ bots to play the tank game.

## Phase 4 Feature

This is planned for Phase 4 of development. The interface will allow:

- C++ bots to receive sensor data
- C++ bots to return actions
- Fair timing system (same time limits as Python bots)
- Inter-process communication via shared memory or pipes

## Implementation Options

1. **ctypes**: Simple FFI for C functions
2. **pybind11**: More sophisticated C++ binding (recommended)
3. **Shared Memory**: For high-performance communication
4. **IPC Pipes**: For process isolation

## API Design

The C++ bot will implement:

```cpp
class TankBot {
public:
    virtual Action getAction(const SensorData& sensors) = 0;
};
```

Where `SensorData` contains:
- Tank state (position, HP, cooldown)
- Visible entities
- Wall distances
- Radar pings
