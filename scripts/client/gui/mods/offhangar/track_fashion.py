# BigWorld-dependent. Python 2.7 runtime. Mirrors the real client's
# _setupVehicleFashion (see decompiled vehicleappearance.py) but supplies
# our own movementInfo provider instead of a WGVehicleFilter.
import BigWorld
import Math
import math
from gui.mods.offhangar.logging import LOG_DEBUG
from gui.mods.offhangar.track_kinematics import track_speeds, movement_info


def _make_movement_provider():
    """Return a settable Vector4 provider whose .value the fashion reads.
    Tries Vector4Basic first (settable), then Vector4Animation. Returns
    (provider, setter) where setter(tuple4) updates it, or (None, None)."""
    try:
        p = Math.Vector4Basic((0.0, 0.0, 0.0, 0.0))

        def _set(v4):
            p.value = Math.Vector4(v4[0], v4[1], v4[2], v4[3])

        # sanity: provider must expose .value (engine reads movementInfo.value)
        _ = p.value
        LOG_DEBUG('[tracks] provider = Vector4Basic')
        return (p, _set)
    except Exception as e:
        LOG_DEBUG('[tracks] Vector4Basic unavailable:', str(e))
    try:
        p = Math.Vector4Animation()
        p.duration = 0.0
        p.keyframes = [(0.0, (0.0, 0.0, 0.0, 0.0))]

        def _set2(v4):
            p.duration = 0.0
            p.keyframes = [(0.0, (float(v4[0]), float(v4[1]), float(v4[2]), float(v4[3])))]

        _ = p.value
        LOG_DEBUG('[tracks] provider = Vector4Animation direct')
        return (p, _set2)
    except Exception as e:
        LOG_DEBUG('[tracks] Vector4Animation unavailable:', str(e))
    return (None, None)


def _wheel_node_names(template, start_index, count):
    # Matches the game's _createWheelsListByTemplate: node name = '%s%d' % (template, i)
    return ['%s%d' % (template, i) for i in range(start_index, start_index + count)]


def _has_opposite_sign(a, b):
    return abs(a) > 0.001 and abs(b) > 0.001 and ((a > 0.0) != (b > 0.0))


def _smooth_value(current, target, dt, accel_tau, follow_tau, stop_tau, reverse_tau):
    if abs(target) < 0.02:
        tau = stop_tau
    elif _has_opposite_sign(current, target):
        tau = reverse_tau
    elif abs(target) > abs(current):
        tau = accel_tau
    else:
        tau = follow_tau
    tau = max(float(tau), 0.001)
    alpha = 1.0 - math.exp(-dt / tau)
    return current + (target - current) * alpha


def setup_track_fashion(chassis_model, td):
    """Create a WGVehicleFashion, configure it from td.chassis, attach it to
    chassis_model, and return a TrackFashionController. Returns None on any
    failure so the caller's tank still works without animation."""
    if chassis_model is None or td is None:
        return None
    try:
        chassis = td.chassis
        fashion = BigWorld.WGVehicleFashion()
    except Exception as e:
        LOG_DEBUG('[tracks] WGVehicleFashion ctor failed:', str(e))
        return None

    try:
        fashion.maxMovement = td.physics['speedLimits'][0]
    except Exception as e:
        LOG_DEBUG('[tracks] maxMovement failed:', str(e))

    provider, setter = _make_movement_provider()
    if provider is not None:
        try:
            fashion.movementInfo = provider
        except Exception as e:
            LOG_DEBUG('[tracks] assign movementInfo failed:', str(e))
            provider, setter = (None, None)

    try:
        tr = chassis['tracks']
        fashion.setTracks(tr['leftMaterial'], tr['rightMaterial'], tr['textureScale'])
    except Exception as e:
        LOG_DEBUG('[tracks] setTracks failed:', str(e))

    try:
        wh = chassis['wheels']
        for g in wh.get('groups', []):
            try:
                nodes = _wheel_node_names(g[1], g[3], g[2])  # template, startIndex, count
                fashion.addWheelGroup(g[0], g[4], nodes)     # isLeft, radius, nodes
            except Exception as e:
                LOG_DEBUG('[tracks] addWheelGroup failed:', str(e))
        for w in wh.get('wheels', []):
            try:
                fashion.addWheel(w[0], w[2], w[1])           # isLeft, radius, name
            except Exception as e:
                LOG_DEBUG('[tracks] addWheel failed:', str(e))
    except Exception as e:
        LOG_DEBUG('[tracks] wheels setup failed:', str(e))

    try:
        fashion.setLods(chassis['traces']['lodDist'], chassis['wheels']['lodDist'],
                        chassis['tracks']['lodDist'], td.hull['swinging']['lodDist'])
    except Exception as e:
        LOG_DEBUG('[tracks] setLods skipped:', str(e))

    try:
        chassis_model.wg_fashion = fashion
    except Exception as e:
        LOG_DEBUG('[tracks] attach wg_fashion failed:', str(e))
        return None

    try:
        half_width = td.chassis['topRightCarryingPoint'][0]
    except Exception:
        half_width = 1.5
    LOG_DEBUG('[tracks] fashion attached, half_width=', half_width,
              'driver=', provider is not None)
    return TrackFashionController(fashion, setter, half_width)


class TrackFashionController(object):
    def __init__(self, fashion, setter, half_width):
        self._fashion = fashion
        self._set = setter
        self._half_width = half_width
        self._visual_forward = 0.0
        self._visual_left = 0.0
        self._visual_right = 0.0
        self._animation_speed_scale = 0.65
        self._track_accel_tau = 0.38
        self._track_follow_tau = 0.16
        self._track_stop_tau = 0.32
        self._track_reverse_tau = 0.10
        LOG_DEBUG('[tracks] smooth filter scale=', self._animation_speed_scale,
                  'tau accel=', self._track_accel_tau,
                  'follow=', self._track_follow_tau,
                  'stop=', self._track_stop_tau,
                  'reverse=', self._track_reverse_tau)

    def update(self, dt, v, omega):
        if self._set is None:
            return
        try:
            dt = max(0.0, min(float(dt), 0.05))
            target_v = float(v)
            target_left, target_right = track_speeds(target_v, float(omega), self._half_width)
            self._visual_left = _smooth_value(
                self._visual_left, target_left, dt,
                self._track_accel_tau, self._track_follow_tau,
                self._track_stop_tau, self._track_reverse_tau)
            self._visual_right = _smooth_value(
                self._visual_right, target_right, dt,
                self._track_accel_tau, self._track_follow_tau,
                self._track_stop_tau, self._track_reverse_tau)
            self._visual_forward = _smooth_value(
                self._visual_forward, target_v, dt,
                self._track_accel_tau, self._track_follow_tau,
                self._track_stop_tau, self._track_reverse_tau)
            if abs(self._visual_left) < 0.03 and abs(target_left) < 0.03:
                self._visual_left = 0.0
            if abs(self._visual_right) < 0.03 and abs(target_right) < 0.03:
                self._visual_right = 0.0
            if abs(self._visual_forward) < 0.03 and abs(target_v) < 0.03:
                self._visual_forward = 0.0
            self._set(movement_info(
                self._visual_forward * self._animation_speed_scale,
                self._visual_left * self._animation_speed_scale,
                self._visual_right * self._animation_speed_scale))
        except Exception as e:
            LOG_DEBUG('[tracks] update failed:', str(e))
