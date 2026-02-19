/**
 * JSON Bridge for Tanks Bot API
 * 
 * Utilities for parsing BotState from JSON and serializing BotAction to JSON.
 * This uses nlohmann/json (header-only library).
 * 
 * Download json.hpp from: https://github.com/nlohmann/json/releases
 * Place it in include/ directory or install system-wide.
 */

#ifndef TANKS_JSON_BRIDGE_H
#define TANKS_JSON_BRIDGE_H

#include "tanks_bot.h"
#include <nlohmann/json.hpp>
#include <iostream>
#include <string>

namespace tanks {

using json = nlohmann::json;

/**
 * Parse MapBounds from JSON.
 */
inline MapBounds parse_map_bounds(const json& j) {
    return MapBounds{
        j["width"].get<int>(),
        j["height"].get<int>()
    };
}

/**
 * Parse FogMemorySummary from JSON.
 */
inline FogMemorySummary parse_fog_memory(const json& j) {
    FogMemorySummary fog;
    if (j.contains("revealed_bounds") && j["revealed_bounds"].is_array()) {
        for (const auto& rect : j["revealed_bounds"]) {
            fog.revealed_bounds.push_back({
                rect[0].get<int>(),
                rect[1].get<int>(),
                rect[2].get<int>(),
                rect[3].get<int>()
            });
        }
    }
    return fog;
}

/**
 * Parse SelfState from JSON.
 */
inline SelfState parse_self_state(const json& j) {
    return SelfState{
        j["id"].get<int>(),
        j["x"].get<double>(),
        j["y"].get<double>(),
        j["rotation"].get<double>(),
        j["turret_rotation"].get<double>(),
        j["speed"].get<double>(),
        j["hp"].get<int>(),
        j["shoot_cooldown"].get<double>(),
        j["team"].get<int>()
    };
}

/**
 * Parse VisibleEntity from JSON.
 */
inline VisibleEntity parse_visible_entity(const json& j) {
    VisibleEntity entity;
    entity.id = j["id"].get<int>();
    entity.kind = j["kind"].get<std::string>();
    entity.x = j["x"].get<double>();
    entity.y = j["y"].get<double>();
    
    // Optional fields
    if (j.contains("rotation") && !j["rotation"].is_null()) {
        entity.rotation = j["rotation"].get<double>();
    }
    if (j.contains("turret_rotation") && !j["turret_rotation"].is_null()) {
        entity.turret_rotation = j["turret_rotation"].get<double>();
    }
    if (j.contains("team") && !j["team"].is_null()) {
        entity.team = j["team"].get<int>();
    }
    
    entity.active = j["active"].get<bool>();
    entity.distance = j["distance"].get<double>();
    entity.bearing = j["bearing"].get<double>();
    
    return entity;
}

/**
 * Parse RadarHit from JSON.
 */
inline RadarHit parse_radar_hit(const json& j) {
    return RadarHit{
        j["id"].get<int>(),
        j["kind"].get<std::string>(),
        j["distance"].get<double>(),
        j["bearing"].get<double>()
    };
}

/**
 * Parse BotState from JSON.
 */
inline BotState parse_bot_state(const json& j) {
    BotState state;
    state.type = j["type"].get<std::string>();
    state.tick_id = j["tick_id"].get<int>();
    state.dt = j["dt"].get<double>();
    state.self = parse_self_state(j["self"]);
    
    // Parse visible entities
    if (j.contains("visible_entities") && j["visible_entities"].is_array()) {
        for (const auto& entity_json : j["visible_entities"]) {
            state.visible_entities.push_back(parse_visible_entity(entity_json));
        }
    }
    
    // Parse radar hits
    if (j.contains("radar_hits") && j["radar_hits"].is_array()) {
        for (const auto& hit_json : j["radar_hits"]) {
            state.radar_hits.push_back(parse_radar_hit(hit_json));
        }
    }
    
    // Parse fog memory (optional)
    if (j.contains("fog_memory") && !j["fog_memory"].is_null()) {
        state.fog_memory = parse_fog_memory(j["fog_memory"]);
    }
    
    state.map_bounds = parse_map_bounds(j["map_bounds"]);
    state.tile_size = j["tile_size"].get<int>();
    
    return state;
}

/**
 * Serialize BotAction to JSON.
 */
inline json serialize_bot_action(const BotAction& action) {
    json j;
    j["type"] = action.type;
    j["tick_id"] = action.tick_id;
    j["move_forward"] = action.move_forward;
    j["move_backward"] = action.move_backward;
    j["turn_left"] = action.turn_left;
    j["turn_right"] = action.turn_right;
    j["turret_left"] = action.turret_left;
    j["turret_right"] = action.turret_right;
    j["shoot"] = action.shoot;
    
    if (action.desired_turret_angle.has_value()) {
        j["desired_turret_angle"] = action.desired_turret_angle.value();
    } else {
        j["desired_turret_angle"] = nullptr;
    }
    
    return j;
}

/**
 * Main loop helper: read state from stdin, call bot, write action to stdout.
 * 
 * @param bot The bot implementation.
 * @return Exit code (0 = normal exit, 1 = error).
 */
inline int run_bot_loop(TankBot& bot) {
    std::string line;
    
    while (std::getline(std::cin, line)) {
        try {
            // Parse incoming state
            json state_json = json::parse(line);
            BotState state = parse_bot_state(state_json);
            
            // Call bot logic
            BotAction action = bot.update(state);
            action.tick_id = state.tick_id;  // Ensure tick_id matches
            
            // Serialize and send action
            json action_json = serialize_bot_action(action);
            std::cout << action_json.dump() << std::endl;
            std::cout.flush();  // Ensure immediate send
            
        } catch (const json::exception& e) {
            std::cerr << "JSON error: " << e.what() << std::endl;
            return 1;
        } catch (const std::exception& e) {
            std::cerr << "Bot error: " << e.what() << std::endl;
            return 1;
        }
    }
    
    return 0;  // Normal exit
}

} // namespace tanks

#endif // TANKS_JSON_BRIDGE_H
