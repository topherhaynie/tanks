# Phase 2 Enhancements - Fog of War & Radar

## Issues Fixed

### 1. **Entity Visibility Through Fog** ✅
- **Problem**: All entities were rendered, then fog overlaid on top, making them visible (albeit obscured)
- **Solution**: Implemented filtered rendering methods:
  - `render_tanks_filtered()` - Only renders tanks in perspective tank's `visible_entities` list
  - `render_bullets_filtered()` - Only renders bullets that are visible
  - Perspective tank always renders itself

### 2. **Dark Coloring on Revealed Tiles** ✅
- **Problem**: Revealed areas still had dark coloring
- **Solution**: 
  - Increased fog opacity from 180 to 240 for truly dark fog in unrevealed areas
  - Ensured fog only draws on unrevealed tiles
  - Revealed tiles are completely clear with no overlay

### 3. **Blocky Fog Edges** ✅
- **Problem**: Tile-based fog rendering created harsh, blocky edges
- **Solution**: Added smooth gradient system:
  - Detects unrevealed neighbor tiles
  - Draws subtle alpha gradient (30% opacity) at edges toward fog
  - Gradient width: 16 pixels (1/4 of tile size)
  - Directional gradients (left, right, top, bottom)
  - Creates soft, natural fog boundary

### 4. **No Radar Visualization** ✅
- **Problem**: No visual indicator for radar-detected entities
- **Solution**: Added comprehensive radar system:
  - **Radar Blips**:
    - Pulsing circles on radar-detected entities
    - Size based on distance (closer = larger)
    - Pulse animation synced to radar sweep
    - Only shows entities NOT in direct line of sight
    - Semi-transparent connection lines from perspective tank to blips
  - **Radar Sweep Animation**:
    - 180°/second rotating sweep line (visible in F3 debug mode)
    - Cyan color with alpha transparency
    - Adds dynamic "scanning" feel
  - **Always-On Indicator**:
    - Radar blips enabled by default (`show_radar_blips = True`)
    - Toggle with F4 key if desired

## New Controls

- **F4** - Toggle radar blips on/off

## Visual Improvements

### Fog Rendering
- **Unrevealed areas**: Solid black fog (alpha 240/255)
- **Fog edges**: Smooth 16-pixel gradient with 30% opacity fade
- **Revealed areas**: Completely clear, no darkness

### Radar Blips
- **Outer ring**: Pulsing cyan circle (size varies 1.0x to 1.3x)
- **Inner circle**: Filled cyan with inverse alpha (brighter when smaller)
- **Connection line**: Thin cyan line from tank to blip (alpha 80)
- **Size range**: 4-12 pixels based on distance
- **Pulse rate**: 4x radar sweep speed

### Debug Mode (F3)
- **Vision circle**: Green filled circle (300px radius)
- **Radar circle**: Blue outline (600px radius)
- **Radar sweep**: Rotating cyan line from center

## Technical Details

### Performance
- Fog gradients add minimal overhead (only drawn at revealed tile edges)
- Radar sweep animation runs at 60fps without impact
- Entity filtering reduces draw calls in fog mode

### Code Quality
- Refactored complex fog rendering into helper methods:
  - `_draw_fog_gradient()` - Handles gradient calculation
  - `_draw_gradient_line()` - Draws individual gradient lines
- Reduced McCabe complexity from 16 to under 15
- Fixed all linting issues

## Configuration Constants

```python
# New constants in constants.py
COLOR_FOG = (0, 0, 0, 240)  # Very dark fog
COLOR_RADAR_BLIP = (100, 200, 255, 200)  # Cyan blips
COLOR_RADAR_SWEEP = (100, 200, 255, 60)  # Cyan sweep line

# New setting in settings.py
show_radar_blips = True  # Always-on by default
```

## Gameplay Impact

### Strategic Elements
1. **True Fog of War**: Enemies completely invisible outside line of sight
2. **Radar Advantage**: Detect hidden enemies through walls
3. **Exploration**: Smooth fog reveal feels natural and rewarding
4. **Tactical Awareness**: Radar blips show enemy positions without cluttering view

### User Experience
- Fog edges look professional with gradients
- Radar blips provide clear enemy location feedback
- Pulsing animation draws attention to threats
- No visual clutter (blips only for hidden enemies)

## Future Enhancements (Optional)

- [ ] Minimap with radar overlay
- [ ] Distance indicators on radar blips
- [ ] Different blip colors for different entity types
- [ ] Sound effect when enemy enters radar range
- [ ] Radar jamming/disruption mechanic
