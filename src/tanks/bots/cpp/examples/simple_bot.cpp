/**
 * Simple Wander Bot - Example C++ Bot
 * 
 * Demonstrates basic bot implementation with wander/seek behavior:
 * - Wanders when no enemies visible
 * - Seeks and shoots when enemy detected
 * - Simple shooting logic
 * 
 * Build: See CMakeLists.txt
 * Run: ./simple_bot (engine will pipe stdin/stdout)
 */

#include "tanks_bot.h"
#include "tanks_json_bridge.h"
#include <cmath>
#include <random>

namespace tanks {

class SimpleWanderBot : public TankBot {
public:
    SimpleWanderBot() 
        : rng_(std::random_device{}())
        , turn_dist_(0.0, 1.0)
        , wander_timer_(0.0)
        , turn_right_(true)
        , wander_interval_(2.5)
    {
    }
    
    BotAction update(const BotState& state) override {
        BotAction action;
        
        // Find nearest enemy
        const VisibleEntity* nearest_enemy = find_nearest_enemy(state);
        
        if (nearest_enemy) {
            // Seek mode: turn toward enemy and shoot
            action = seek_enemy(state, *nearest_enemy);
        } else {
            // Wander mode: random movement
            action = wander(state);
        }
        
        return action;
    }
    
private:
    std::mt19937 rng_;
    std::uniform_real_distribution<double> turn_dist_;
    double wander_timer_;
    bool turn_right_;
    double wander_interval_;
    
    /**
     * Find nearest visible enemy tank.
     */
    const VisibleEntity* find_nearest_enemy(const BotState& state) {
        const VisibleEntity* nearest = nullptr;
        double min_distance = std::numeric_limits<double>::infinity();
        
        for (const auto& entity : state.visible_entities) {
            if (entity.kind == "tank" && 
                entity.active && 
                entity.team.has_value() && 
                entity.team.value() != state.self.team) {
                
                if (entity.distance < min_distance) {
                    min_distance = entity.distance;
                    nearest = &entity;
                }
            }
        }
        
        return nearest;
    }
    
    /**
     * Seek behavior: turn toward enemy and shoot.
     */
    BotAction seek_enemy(const BotState& state, const VisibleEntity& enemy) {
        BotAction action;
        action.move_forward = true;
        
        // Calculate angle to enemy (bearing is relative to tank forward = 0)
        double bearing = enemy.bearing;
        
        // Turn toward enemy
        double turn_threshold = 0.1;  // radians
        if (std::abs(bearing) > turn_threshold) {
            if (bearing > 0) {
                action.turn_left = true;
            } else {
                action.turn_right = true;
            }
        }
        
        // Aim turret at enemy (use absolute angle for precision)
        double target_angle = state.self.rotation + bearing;
        action.desired_turret_angle = target_angle;
        
        // Shoot if turret roughly aligned
        double turret_error = normalize_angle(target_angle - state.self.turret_rotation);
        if (std::abs(turret_error) < 0.2 && state.self.shoot_cooldown <= 0.0) {
            action.shoot = true;
        }
        
        return action;
    }
    
    /**
     * Wander behavior: timer-based turns for smooth movement.
     */
    BotAction wander(const BotState& state) {
        BotAction action;
        action.move_forward = true;
        
        // Update wander timer
        wander_timer_ += state.dt;
        
        // Change direction every ~2.5 seconds
        if (wander_timer_ > wander_interval_) {
            wander_timer_ = 0.0;
            turn_right_ = !turn_right_;
            // Randomize next interval (1.2 to 3.3 seconds)
            wander_interval_ = 2.5 + (turn_dist_(rng_) * 1.6 - 0.8);
            if (wander_interval_ < 1.2) wander_interval_ = 1.2;
        }
        
        // Apply consistent turn direction
        if (turn_right_) {
            action.turn_right = true;
        } else {
            action.turn_left = true;
        }
        
        return action;
    }
    
    /**
     * Normalize angle to [-π, π].
     */
    double normalize_angle(double angle) {
        while (angle > M_PI) angle -= 2 * M_PI;
        while (angle < -M_PI) angle += 2 * M_PI;
        return angle;
    }
};

} // namespace tanks

int main() {
    tanks::SimpleWanderBot bot;
    return tanks::run_bot_loop(bot);
}
