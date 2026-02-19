# Building C++ Bots for Tanks

This guide explains how to build and run C++ bots using the Tanks C++ SDK.

## Prerequisites

### Required Tools
- **CMake 3.15+**: Build system
- **C++17 Compiler**: GCC 7+, Clang 5+, or MSVC 2017+
- **Git**: For downloading dependencies

### Installing CMake

**macOS (Homebrew):**
```bash
brew install cmake
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install cmake build-essential
```

**Windows:**
Download from [cmake.org](https://cmake.org/download/) or use Chocolatey:
```powershell
choco install cmake
```

## Building the Example Bot

### 1. Navigate to C++ SDK Directory

```bash
cd src/tanks/bots/cpp
```

### 2. Create Build Directory

```bash
mkdir build
cd build
```

### 3. Configure with CMake

```bash
cmake ..
```

This will:
- Configure the build system
- Automatically download nlohmann/json library (v3.11.3)
- Generate platform-specific build files

### 4. Build the Bot

```bash
make
```

Or on Windows with Visual Studio:
```powershell
cmake --build . --config Release
```

### 5. Verify Build

The executable will be in `build/simple_bot`:

```bash
./simple_bot --version  # Should wait for stdin (Ctrl+C to exit)
```

## Testing Your Bot

### Manual Testing with JSON

You can test your bot manually by sending JSON state:

```bash
./simple_bot
```

Then paste a state JSON (example):

```json
{"type":"state","tick_id":1,"dt":0.033,"self":{"id":1,"x":100,"y":100,"rotation":0,"turret_rotation":0,"speed":0,"hp":100,"shoot_cooldown":0,"team":1},"visible_entities":[],"radar_hits":[],"fog_memory":null,"map_bounds":{"width":1280,"height":704},"tile_size":64}
```

Bot should respond with an action JSON.

### Integration Testing with Python

The Python engine can automatically spawn and manage your bot:

```python
from tanks.bots import ExternalBotRunner, ExternalBotController

# Create runner pointing to your bot executable
runner = ExternalBotRunner(
    executable_path="./src/tanks/bots/cpp/build/simple_bot",
    timeout_ms=8.0
)

# Start the bot process
runner.start()

# Create controller (requires tank and game from spawn)
controller = ExternalBotController(tank, game, runner)

# Add to game input handlers
game.add_input_handler(controller)
```

See `src/tanks/demo.py` (`run_mixed_bot_battle_demo`) for a complete example.

## Creating Your Own Bot

### 1. Copy Example

```bash
cp examples/simple_bot.cpp examples/my_bot.cpp
```

### 2. Edit Bot Logic

Implement the `update()` method:

```cpp
tanks::BotAction update(const tanks::BotState& state) override {
    tanks::BotAction action;
    
    // Your logic here
    if (/* enemy visible */) {
        action.move_forward = true;
        action.shoot = true;
    }
    
    return action;
}
```

### 3. Add to CMakeLists.txt

```cmake
add_executable(my_bot examples/my_bot.cpp)
target_link_libraries(my_bot PRIVATE nlohmann_json::nlohmann_json)
```

### 4. Rebuild

```bash
cd build
make
```

## Debugging Tips

### Enable Debug Output

Add debug prints to stderr (not stdout!):

```cpp
std::cerr << "Debug: enemy at distance " << enemy.distance << std::endl;
```

### Check JSON Communication

Capture bot's I/O for inspection:

```bash
echo '{"type":"state",...}' | ./simple_bot 2>debug.log
```

### Verify Protocol Compliance

- Ensure tick_id in response matches request
- Always set `type: "action"` in response
- Flush stdout after each response
- Don't print to stdout (only JSON)

## Performance Tips

Keep your bot under 8ms per tick:

- **Avoid expensive operations**: No disk I/O, network calls, or blocking
- **Pre-compute**: Initialize lookup tables in constructor
- **Profile**: Use `chrono` to measure update() time
- **Optimize hot paths**: Cache frequently used calculations

Example timing:

```cpp
#include <chrono>

tanks::BotAction update(const tanks::BotState& state) override {
    auto start = std::chrono::high_resolution_clock::now();
    
    // Your logic...
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    if (duration.count() > 8000) {
        std::cerr << "Warning: update took " << duration.count() << "us" << std::endl;
    }
    
    return action;
}
```

## Common Issues

### "cmake: command not found"

CMake is not installed. Install using package manager (see Prerequisites).

### "Could not find nlohmann_json"

CMake should auto-download it. If not:
- Check internet connection
- Try manual installation: `brew install nlohmann-json` (macOS)
- Or install system-wide from [GitHub](https://github.com/nlohmann/json)

### "Bot not responding"

- Check executable permissions: `chmod +x simple_bot`
- Verify JSON format matches protocol spec
- Check stderr for error messages
- Test with manual JSON input first

### "Timeout errors"

Bot is taking too long:
- Profile your update() method
- Simplify calculations
- Pre-compute expensive operations
- Check for infinite loops

## Advanced Topics

### State Machine Bots

Implement complex behavior with states:

```cpp
enum class State { WANDER, SEEK, RETREAT };

class StateMachineBot : public tanks::TankBot {
    State current_state = State::WANDER;
    
    tanks::BotAction update(const tanks::BotState& state) override {
        // Transition logic
        if (enemy_visible && hp_low) {
            current_state = State::RETREAT;
        } else if (enemy_visible) {
            current_state = State::SEEK;
        } else {
            current_state = State::WANDER;
        }
        
        // State-specific behavior
        switch (current_state) {
            case State::WANDER: return wander(state);
            case State::SEEK: return seek_enemy(state);
            case State::RETREAT: return retreat(state);
        }
    }
};
```

### Using Fog Memory

Access previously revealed areas:

```cpp
bool is_area_explored(const tanks::BotState& state, int tile_x, int tile_y) {
    if (!state.fog_memory.has_value()) return false;
    
    for (const auto& rect : state.fog_memory->revealed_bounds) {
        int rx = rect[0], ry = rect[1], rw = rect[2], rh = rect[3];
        if (tile_x >= rx && tile_x < rx + rw &&
            tile_y >= ry && tile_y < ry + rh) {
            return true;
        }
    }
    return false;
}
```

### Aiming with desired_turret_angle

For precise targeting:

```cpp
// Calculate angle to target
double dx = target.x - state.self.x;
double dy = target.y - state.self.y;
double angle_to_target = std::atan2(dy, dx);

// Set absolute turret angle
action.desired_turret_angle = angle_to_target;

// Shoot if aligned
double turret_error = normalize_angle(angle_to_target - state.self.turret_rotation);
if (std::abs(turret_error) < 0.1) {
    action.shoot = true;
}
```

## Next Steps

- Read protocol spec: `docs/Project Plans/06_Bot_API.md`
- Study Python bots: `src/tanks/bots/simple_bot.py`, `smart_bot.py`
- Experiment with strategy variations
- Compete in tournaments (Phase 4 feature coming soon)

## Support

For questions or issues:
1. Check the SDK README: `src/tanks/bots/cpp/README.md`
2. Review API documentation: Header comments in `include/tanks_bot.h`
3. See the example bot: `examples/simple_bot.cpp`
