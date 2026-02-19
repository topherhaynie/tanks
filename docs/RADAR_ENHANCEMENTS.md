# Radar Enhancements

Implementation of all five radar enhancement features from Phase 2's future enhancements list.

## Features Implemented

### 1. Minimap with Radar Overlay ✅

**Location:** Bottom-right corner of screen

**Features:**
- 200x200 pixel minimap with semi-transparent background
- Shows entire map with walls rendered as small rectangles
- Displays radar range (600px) and vision range (200px) as concentric circles
- Shows all tanks with color coding:
  - **You (perspective tank):** Green with heading indicator line
  - **Friendly tanks:** Smaller green dots
  - **Enemy tanks:** Red dots (only visible if detected by vision or radar)
- Shows radar-detected entities with pulsing blips (same color coding as main radar)
- Auto-scales to fit any map size

**Controls:**
- `F5` - Toggle minimap on/off

**Constants Added:**
```python
MINIMAP_SIZE = 200  # pixels
MINIMAP_PADDING = 20  # Distance from edges
COLOR_MINIMAP_BACKGROUND = (20, 20, 30, 180)
COLOR_MINIMAP_BORDER = (100, 100, 120, 255)
COLOR_MINIMAP_WALL = (80, 80, 100, 255)
COLOR_MINIMAP_TANK_FRIENDLY = (50, 200, 50, 255)
COLOR_MINIMAP_TANK_ENEMY = (200, 50, 50, 255)
COLOR_MINIMAP_RADAR_RANGE = (100, 100, 255, 60)
COLOR_MINIMAP_VISION_RANGE = (100, 255, 100, 60)
```

### 2. Distance Indicators on Radar Blips ✅

**Features:**
- Distance in pixels displayed next to each radar blip
- Semi-transparent black background for readability
- White text that follows entity position
- Positioned to the right of the blip to avoid clutter

**Example:** `450px` appears next to a radar-detected enemy tank

### 3. Entity Type Color Coding ✅

**Features:**
- **Tanks:** Cyan/blue blips (`COLOR_RADAR_BLIP_TANK`)
- **Mines:** Orange blips (`COLOR_RADAR_BLIP_MINE`)
- Color coding applies to:
  - Main radar blips on game view
  - Minimap radar blips
  - Connection lines from player to detected entities

**Constants:**
```python
COLOR_RADAR_BLIP_TANK = (100, 200, 255, 200)  # Cyan
COLOR_RADAR_BLIP_MINE = (255, 150, 50, 200)   # Orange
```

### 4. Radar Ping Sound Effect ✅

**Features:**
- Plays when NEW enemy enters radar range (not visible)
- Only triggers once per new detection (not every frame)
- Volume: 30% (subtle, non-intrusive)
- Tracks previous radar detections per tank to detect new entries

**Implementation:**
- Added `previous_radar_entities` set to Tank class
- Sound triggered in perception update when new entities detected
- Only one ping per update even if multiple new entities

**Sound Method:**
```python
sound_manager.play_radar_ping()  # 30% volume
```

### 5. Radar Jamming Mechanic ✅

**Gameplay:**
- **Duration:** 3 seconds of active jamming
- **Cooldown:** 10 seconds before next use
- **Range:** 300 pixels radius
- **Effect:** Blocks all enemy radar within range (returns empty list)

**Visual Indicators:**
- **Jamming Active:**
  - 3 pulsing concentric red circles around jamming tank
  - "JAMMING" text above tank in red
  - Pulse animation synced to radar sweep (faster)
  
- **UI Status Display (top-left):**
  - **Ready:** `Jam Ready (J)` - Green text
  - **Active:** `JAMMING: 2.3s` - Red text with countdown
  - **Cooldown:** `Jam Cooldown: 7.8s` - Gray text with countdown

**Controls:**
- **Player 1:** `J` key to activate jamming
- **Player 2:** `Right Shift` key to activate jamming

**Constants:**
```python
RADAR_JAMMING_RADIUS = 300  # pixels
RADAR_JAMMING_DURATION = 3.0  # seconds
RADAR_JAMMING_COOLDOWN = 10.0  # seconds
COLOR_RADAR_JAMMING = (255, 100, 100, 150)  # Red
```

**Tank Methods:**
```python
tank.can_jam_radar() -> bool  # Check if jamming available
tank.activate_jamming() -> bool  # Activate jamming (returns success)
```

## Code Structure

### Files Modified

1. **`src/tanks/config/constants.py`**
   - Added minimap constants
   - Added jamming constants
   - Added entity type colors

2. **`src/tanks/config/settings.py`**
   - Added `show_minimap` setting (default: True)

3. **`src/tanks/entities/tank.py`**
   - Added jamming state variables (`jamming_active`, `jamming_timer`, `jamming_cooldown`)
   - Added `previous_radar_entities` for ping detection
   - Added `can_jam_radar()` and `activate_jamming()` methods
   - Updated `update()` to handle jamming timers

4. **`src/tanks/perception/vision.py`**
   - Updated `RadarSystem.detect_entities()` to check for jamming
   - Returns empty list if tank is within range of active enemy jammer

5. **`src/tanks/rendering/renderer.py`**
   - Added `render_minimap()` with helper methods:
     - `_draw_minimap_walls()`
     - `_draw_minimap_ranges()`
     - `_draw_minimap_tanks()`
     - `_draw_perspective_tank_on_minimap()`
     - `_draw_minimap_radar_blips()`
   - Added `render_jamming_effects()` for visual indicators
   - Added `render_jamming_status()` for UI display
   - Updated radar blips to use entity type colors
   - Added distance text to radar blips

6. **`src/tanks/input/keyboard.py`**
   - Added `jam` key binding (J for player 1, Right Shift for player 2)
   - Added jamming activation logic with key state tracking
   - Both KeyboardController and KeyboardController2 support jamming

7. **`src/tanks/core/game.py`**
   - Added F5 key toggle for minimap
   - Added radar ping sound trigger in perception update
   - Tracks new radar detections for sound effects

8. **`src/tanks/audio/__init__.py`**
   - Added `radar_ping` sound placeholder
   - Added `play_radar_ping()` method

## Performance Considerations

- **Minimap:** Refactored into separate helper methods to reduce complexity
- **Jamming Check:** Early return if jammed (minimal overhead)
- **Ping Detection:** Set difference operation (O(n) where n = detected entities)
- **No Additional Loops:** All features integrated into existing update cycles

## Gameplay Balance

### Radar Jamming Strategy
- **Offensive Use:** Hide your approach when pushing enemy positions
- **Defensive Use:** Prevent enemy from tracking your movements
- **Timing Critical:** 3-second window requires tactical planning
- **Cooldown Punishment:** 10 seconds vulnerable after use
- **Limited Range:** 300px means you must be relatively close

### Counter-Play
- Vision still works during jamming (200px line-of-sight)
- Teammates outside jamming radius can still detect
- Jamming tank's position revealed by visual effect
- Can be used as bait/distraction

## Controls Summary

### New Keybinds
- `J` - Player 1 radar jamming
- `Right Shift` - Player 2 radar jamming
- `F5` - Toggle minimap

### Existing Radar Controls
- `F4` - Toggle radar blips
- `F3` - Toggle vision/radar debug circles

## Future Enhancements (Optional)

- [ ] Sound files for radar ping (currently placeholder)
- [ ] Minimap zoom levels
- [ ] Minimap click-to-ping communication
- [ ] Different jamming levels (partial vs full)
- [ ] Equipment slots for jamming vs other abilities
- [ ] Jamming cooldown reduction powerups
- [ ] Passive vs active radar modes

## Technical Notes

### Type Safety
- All new code includes full type annotations
- Google-style docstrings for all public methods
- No linting errors (passed Ruff checks)

### Code Quality
- Reduced minimap complexity by extracting helper methods
- Used ternary operators for simple conditional assignments
- Combined nested if statements for cleaner logic
- Removed unused imports and variables

### Testing Recommendations
1. Test minimap scaling with different map sizes
2. Verify jamming range calculations
3. Test multiple simultaneous jammers
4. Confirm radar ping doesn't spam when many enemies enter range
5. Test jamming cooldown UI accuracy
6. Verify color coding on both minimap and main view
7. Test F5 toggle doesn't affect other rendering

## Credits

Implemented as part of Phase 2 radar enhancements based on the future enhancements list in `docs/PHASE2_ENHANCEMENTS.md`.
