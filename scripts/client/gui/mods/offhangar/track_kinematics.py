# Pure Python, no engine deps. Must stay Python 2.7 + 3 compatible.
#
# The game's WGVehicleFashion reads movementInfo as TRACK SPEEDS (m/s), not
# accumulated distance: in vehicleappearance.py it computes
# `trackSpeedRel = movementInfo[iTrack + 1] / maxMovement`. So we feed
# instantaneous left/right track speed and let the fashion integrate the
# texture scroll and wheel rotation internally.


def track_speeds(v, omega, half_width):
    """Left/right track linear speed (m/s) from hull forward speed v (m/s)
    and yaw rate omega (rad/s). half_width is the half track gauge (m)."""
    return (v - omega * half_width, v + omega * half_width)


def movement_info(v, left_speed, right_speed):
    """movementInfo Vector4 the fashion expects:
    [0] hull forward speed, [1] left track speed, [2] right track speed, [3] unused."""
    return (v, left_speed, right_speed, 0.0)
