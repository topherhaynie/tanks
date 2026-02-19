# C++ Bot SDK

C++ SDK for creating external bots that play the Tanks game via JSON stdin/stdout communication.

## Overview

The C++ SDK provides:
- **Headers**: Data structures matching the bot protocol (`tanks_bot.h`)
- **JSON Bridge**: Parsing/serialization utilities (`tanks_json_bridge.h`)
- **Base Class**: Abstract `TankBot` interface for bot implementations
- **Main Loop**: Helper function for stdin/stdout communication
- **Examples**: Sample bot implementations

## Protocol

The JSON communication protocol is fully specified in:
- `docs/Project Plans/06_Bot_API.md` - Complete protocol documentation
- `docs/bot_api.schema.json` - JSON schema for validation

Bots communicate via stdin/stdout:
1. Engine sends BotState as JSON (one line per tick, 30Hz)
2. Bot responds with BotAction as JSON (must match tick_id)
3. Timeout budget: 8ms per tick (enforced by engine)

## Building

### Requirements
- CMake 3.15+
- C++17 compatible compiler (GCC 7+, Clang 5+, MSVC 2017+)
- nlohmann/json (automatically downloaded by CMake)

### Build Steps

```bash
cd src/tanks/bots/cpp
mkdir build && cd build
cmake ..
make
```

This builds the example bot `simple_bot` in `build/simple_bot`.

### Installing nlohmann/json Manually

If you prefer to install nlohmann/json system-wide instead of using FetchContent:

**Ubuntu/Debian:**
```bash
sudo apt install nlohmann-json3-dev
```

**macOS (Homebrew):**
```bash
brew install nlohmann-json
```

Then edit `CMakeLists.txt` to use `find_package` instead of `FetchContent`.

## Creating Your Own Bot

### 1. Create Bot Class

Inherit from `TankBot` and implement `update()`:

```cpp
#include "tanks_bot.h"
#include "tanks_json_bridge.h"

class MyBot : public tanks::TankBot {
public:
    tanks::BotAction update(const tanks::BotState& state) override {
        tanks::BotAction action;
        
        // Your bot logic here
        action.move_forward = true;
        action.shoot = true;
        
        return action;
    }
};
```

### 2. Add Main Function

Use the provided `run_bot_loop()` helper:

```cpp
int main() {
    MyBot bot;
    return tanks::run_bot_loop(bot);
}
```

### 3. Add to CMakeLists.txt

```cmake
add_executable(my_bot examples/my_bot.cpp)
target_link_libraries(my_bot PRIVATE nlohmann_json::nlohmann_json)
```

### 4. Build and Test

```bash
cd build
make
./my_bot  # Run standalone (will wait for stdin)
```

## Testing Your Bot

### Option 1: Direct Testing (Manual)

Run your bot and send JSON manually:

```bash
./build/simple_bot
```

Paste a state JSON (see protocol docs), bot will respond with action.

### Option 2: Python Integration

The engine can spawn your bot automatically:

```python
from tanks.bots.external_runner import ExternalBotRunner
from tanks.bots.external_controller import ExternalBotController

runner = ExternalBotRunner("./build/simple_bot")
runner.start()
controller = ExternalBotController(runner)
# Attach controller to tank...
```

See test scripts (coming soon) for full integration examples.

## API Reference

### BotState Structure

```cpp
struct BotState {
    std::string type;         // "state"
    int tick_id;
    double dt;                // seconds per tick
    SelfState self;           // Tank info
    std::vector<VisibleEntity> visible_entities;
    std::vector<RadarHit> radar_hits;
    std::optional<FogMemorySummary> fog_memory;
    MapBounds map_bounds;
    int tile_size;
};
```

### SelfState

Your tank's current state:

```cpp
struct SelfState {
    int id;
    double x, y;              // position (pixels)
    double rotation;          // body angle (radians)
    double turret_rotation;   // turret angle (radians)
    double speed;             // current speed (pixels/sec)
    int hp;                   // hit points
    double shoot_cooldown;    // seconds until can shoot
    int team;
};
```

### VisibleEntity

Entities visible to your tank:

```cpp
struct VisibleEntity {
    int id;
    std::string kind;         // "tank", "bullet", "obstacle", "mine"
    double x, y;
    std::optional<double> rotation;        // radians (null for obstacles)
    std::optional<double> turret_rotation; // radians (tanks only)
    std::optional<int> team;               // null for obstacles
    bool active;
    double distance;          // pixels from self
    double bearing;           // radians relative to forward
};
```

### RadarHit

Through-wall detections:

```cpp
struct RadarHit {
    int id;
    std::string kind;         // "tank" or "mine"
    double distance;
    double bearing;           // radians relative to forward
};
```

### BotAction

Your response:

```cpp
struct BotAction {
    std::string type;         // "action"
    int tick_id;              // Must match request
    bool move_forward;
    bool move_backward;
    bool turn_left;
    bool turn_right;
    bool turret_left;
    bool turret_right;
    bool shoot;
    std::optional<double> desired_turret_angle;  // overrides turret_left/right
};
```

**Note:** If `desired_turret_angle` is set, `turret_left` and `turret_right` are ignored.

## Examples

### Simple Wander Bot

See `examples/simple_bot.cpp` for a complete example:
- Wanders randomly when no enemies visible
- Turns toward and shoots at nearest enemy
- Uses `desired_turret_angle` for precise aiming

Build and run:
```bash
cd build && make
./simple_bot
```

## Tips

### Angles
- All angles are in radians
- `bearing` is relative to your tank's forward direction (0 = ahead, π/2 = left)
- `rotation` is absolute map angle
- Use `atan2(dy, dx)` to calculate angles

### Timing
- You have ~8ms to respond (engine enforces timeout)
- Keep computations simple and efficient
- Avoid blocking I/O or long loops

### Debugging
- Print to stderr (not stdout!) for debug messages
- stderr is visible in engine logs
- stdout is reserved for JSON communication

### Error Handling
- Engine will restart bot after 3 consecutive errors
- Timeout triggers fallback (last action reused)
- Protocol violations terminate bot

## Troubleshooting

**Bot not responding:**
- Check executable path is correct
- Ensure bot is flushing stdout after each response
- Verify JSON format matches schema

**JSON parse errors:**
- Use `jq` or online validator to check JSON syntax
- Ensure tick_id matches between state and action
- Check all required fields are present

**Timeout errors:**
- Profile your bot's update() function
- Simplify calculations or use lookup tables
- Consider pre-computing expensive operations

## Support

For questions or issues:
1. Check protocol documentation: `docs/Project Plans/06_Bot_API.md`
2. Review example bot: `examples/simple_bot.cpp`
3. See Python bot implementations: `src/tanks/bots/simple_bot.py`
