# C++ Bot Interface

This directory will contain the C++ bot SDK for creating C++ bots to play the tank game.

## Phase 4 Feature

This is planned for Phase 4 of development. The interface will allow:

- C++ bots to receive sensor data via JSON stdin/stdout
- C++ bots to return actions using documented protocol
- Fair timing system (timeout enforcement, same limits as Python bots)
- Process isolation via subprocess management

## Protocol Already Documented

The JSON communication protocol is fully specified in:
- `docs/Project Plans/06_Bot_API.md` - Complete protocol documentation
- `docs/bot_api.schema.json` - JSON schema for validation

C++ bots will communicate using stdin/stdout with the engine managing the subprocess.

## Implementation Plan (Phase 4)

### Python Side (Engine)
1. **External bot runner** (`bots/external_runner.py`):
   - Subprocess.Popen for process management
   - JSON serialization/deserialization
   - Timeout watchdog (3-8ms budget)
   - Error handling for crashed/hanging bots

2. **External bot controller** (`bots/external_controller.py`):
   - Wraps external process as Controller
   - Sends BotState as JSON per tick
   - Receives BotAction as JSON response
   - Falls back to no-op on timeout

### C++ Side (SDK)
1. **Header files** (`cpp/include/tanks_bot.h`):
   ```cpp
   struct BotState { /* ... */ };
   struct BotAction { /* ... */ };
   
   class TankBot {
   public:
       virtual BotAction update(const BotState& state) = 0;
   };
   ```

2. **JSON utilities** (`cpp/src/json_bridge.cpp`):
   - Parse BotState from JSON stdin
   - Serialize BotAction to JSON stdout
   - Error handling and validation

3. **Example bot** (`cpp/examples/simple_bot.cpp`):
   - Implements TankBot interface
   - Simple wander/seek behavior
   - Shows JSON communication pattern

4. **Build system** (`cpp/CMakeLists.txt`):
   - CMake for cross-platform builds
   - JSON library dependency (nlohmann/json)
   - Example compilation targets

## Communication Flow

```
Python Engine                          C++ Bot Process
-------------                          ----------------
1. Spawn subprocess
2. Send BotState JSON →              → 3. Read stdin
                                       4. Parse JSON
                                       5. Call bot.update()
                                       6. Serialize result
7. Read stdout           ←            ← 8. Write JSON
9. Apply BotAction
10. Wait for next tick
```

## Timing Requirements

- C++ bots have 3-8ms to respond per tick (30Hz input rate = 33ms per tick)
- Engine enforces timeout with watchdog
- Late/missing responses use last known action or no-op
- Same fairness as Python bots (no peeking at future state)
