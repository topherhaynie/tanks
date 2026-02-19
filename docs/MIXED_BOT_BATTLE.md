# Mixed Bot Battle Demo

This demo showcases the external bot system by running a 3-way battle between:
- **C++ External Bot** (Team 0 - Blue fog) - Uses the C++ SDK
- **Python SimpleBot** (Team 1 - Red fog) - Wander/seek behavior
- **Python SmartBot** (Team 2 - Green fog) - Radar pursuit with stuck detection

## Requirements

The C++ bot must be built before running this demo:

```bash
cd src/tanks/bots/cpp
mkdir -p build
cd build
cmake ..
make
```

This creates `src/tanks/bots/cpp/build/simple_bot`.

## Running the Demo

```bash
python -m tanks
```

Then select option **4. Mixed Bot Battle (C++ + Python) 🆕**

## What You'll See

- **Global Observer View**: Watch all three bots simultaneously
- **Color-Coded Fog**: Each bot has its own fog of war (blue, red, green)
- **Different AI Strategies**: Compare external C++ bot vs internal Python bots
- **Real-Time Competition**: Bots detect and engage each other

## Bot Positioning

- **C++ Bot**: Spawns top-left (Team 0)
- **SimpleBot**: Spawns top-right (Team 1)  
- **SmartBot**: Spawns bottom-center (Team 2)

## Controls

- **F1**: Toggle debug overlay (all systems)
- **F2**: Toggle hitboxes
- **F3**: Toggle vision ranges
- **F4**: Toggle radar blips
- **P**: Pause/unpause
- **ESC**: Return to menu

## Technical Details

### External Bot Integration

The C++ bot runs as a separate process:
1. Engine spawns subprocess via `ExternalBotRunner`
2. JSON state sent to bot via stdin (30Hz)
3. Bot responds with action via stdout
4. `ExternalBotController` applies actions to tank

### Observer Rendering

- Each bot has independent fog of war
- Fog is rendered with RGB tinting per team
- Hidden tanks (outside enemy vision) shown with reduced alpha
- Radar blips shown above fog layer

## Troubleshooting

**"C++ bot not found!"**
- Build the C++ bot first (see Requirements above)
- Check path: `src/tanks/bots/cpp/build/simple_bot`

**C++ bot not moving:**
- Check stderr for JSON errors
- Verify bot built successfully: `./src/tanks/bots/cpp/build/simple_bot --version`
- Test bot standalone: `echo '{"type":"state",...}' | ./src/tanks/bots/cpp/build/simple_bot`

**Performance issues:**
- C++ bot timeout is 8ms per tick
- Check bot statistics in console output
- Reduce map size or disable debug overlays

## Future Enhancements

- Support for more than 3 bots
- Team-based battles (2v2, 3v3)
- Tournament mode with automatic matchmaking
- Bot performance metrics display (kills, deaths, accuracy)
- Replay recording and playback
