# Physics & Movement Specification (v1)

## Tank Movement

-   Arcade style (no acceleration)
-   Rotate in place
-   Smooth continuous movement
-   Diagonal naturally supported

### Parameters (tunable)

-   Max Speed: Slow
-   Max Turn Rate: Moderate
-   Turret Turn Rate: Faster than body

## Collision

-   Tank hitbox: Circle
-   Tank vs wall: Slide along surface
-   Tank vs tank: Solid collision (slide)

## Shooting

-   Unlimited ammo
-   Cooldown between shots
-   Bullet speed: Medium (tactical)
-   Bullet lifetime limited
-   Ricochet: 1 bounce max

## Damage

-   Tank HP: 3--5 hits
-   No knockback

## Future Weapons

-   Mines (proximity trigger)
-   Heavy shot (fast projectile, long cooldown)
