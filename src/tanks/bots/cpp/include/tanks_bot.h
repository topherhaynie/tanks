/**
 * Tanks Bot API - C++ SDK
 * 
 * This header defines the data structures and interface for creating
 * C++ bots that communicate with the Tanks game engine via JSON stdin/stdout.
 * 
 * Protocol: JSON objects over stdin/stdout, one request per input tick (30Hz).
 * The engine sends a "state" message, bot must reply with "action" message.
 * 
 * See docs/Project Plans/06_Bot_API.md for full protocol specification.
 */

#ifndef TANKS_BOT_H
#define TANKS_BOT_H

#include <vector>
#include <optional>
#include <string>

namespace tanks {

/**
 * Map bounds in pixels.
 */
struct MapBounds {
    int width;
    int height;
};

/**
 * Fog memory summary - revealed tile rectangles.
 * Each rectangle is (x, y, width, height) in fog-tile coordinates.
 */
struct FogMemorySummary {
    std::vector<std::array<int, 4>> revealed_bounds;
};

/**
 * State of the bot-controlled tank.
 */
struct SelfState {
    int id;
    double x;
    double y;
    double rotation;          // radians
    double turret_rotation;   // radians
    double speed;             // pixels/second
    int hp;
    double shoot_cooldown;    // seconds remaining
    int team;
};

/**
 * Visible entity (tank, bullet, obstacle, mine).
 */
struct VisibleEntity {
    int id;
    std::string kind;         // "tank", "bullet", "obstacle", "mine"
    double x;
    double y;
    std::optional<double> rotation;        // radians (null for obstacles)
    std::optional<double> turret_rotation; // radians (null for non-tanks)
    std::optional<int> team;               // null for obstacles/bullets
    bool active;
    double distance;          // pixels from self
    double bearing;           // radians relative to tank forward
};

/**
 * Radar detection (through-wall, no visual).
 */
struct RadarHit {
    int id;
    std::string kind;         // "tank" or "mine"
    double distance;          // pixels from self
    double bearing;           // radians relative to tank forward
};

/**
 * Complete bot state snapshot for one input tick.
 */
struct BotState {
    std::string type;         // Always "state"
    int tick_id;
    double dt;                // seconds per tick
    SelfState self;
    std::vector<VisibleEntity> visible_entities;
    std::vector<RadarHit> radar_hits;
    std::optional<FogMemorySummary> fog_memory;
    MapBounds map_bounds;
    int tile_size;            // pixels per game tile
};

/**
 * Bot action response for one input tick.
 */
struct BotAction {
    std::string type;         // Always "action"
    int tick_id;              // Must match request tick_id
    bool move_forward;
    bool move_backward;
    bool turn_left;
    bool turn_right;
    bool turret_left;
    bool turret_right;
    bool shoot;
    std::optional<double> desired_turret_angle;  // radians (overrides turret_left/right)
    
    // Constructor with defaults
    BotAction() 
        : type("action")
        , tick_id(0)
        , move_forward(false)
        , move_backward(false)
        , turn_left(false)
        , turn_right(false)
        , turret_left(false)
        , turret_right(false)
        , shoot(false)
    {}
};

/**
 * Abstract bot interface.
 * Implement this class to create your bot logic.
 */
class TankBot {
public:
    virtual ~TankBot() = default;
    
    /**
     * Update bot logic for current state.
     * Called once per input tick (30Hz).
     * 
     * @param state Current game state snapshot.
     * @return Action to execute this tick.
     */
    virtual BotAction update(const BotState& state) = 0;
};

} // namespace tanks

#endif // TANKS_BOT_H
