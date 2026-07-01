import math

from gui.mods.offhangar.logging import LOG_DEBUG


def _short_geometry_name(arena_type):
	try:
		name = getattr(arena_type, 'geometryName', '') or ''
		return name.split('/')[-1]
	except Exception:
		return ''


def _value(obj, attr):
	try:
		val = getattr(obj, attr)
		if callable(val):
			return val()
		return val
	except Exception:
		return None


def _vec2_from_section(section):
	if section is None:
		return None
	for attr in ('asVector2', 'asVector3'):
		vec = _value(section, attr)
		if vec is None:
			continue
		try:
			if attr == 'asVector3':
				return (float(vec.x), float(vec.z))
			return (float(vec.x), float(vec.y))
		except Exception:
			try:
				return (float(vec[0]), float(vec[1]))
			except Exception:
				pass
	return None


def _collect_positions(section):
	result = []
	seen = set()

	def add_vec(vec):
		if vec is None:
			return
		key = (round(vec[0], 2), round(vec[1], 2))
		if key in seen:
			return
		seen.add(key)
		result.append(vec)

	def walk(sec, depth):
		if sec is None or depth > 3:
			return
		try:
			items = sec.items()
		except Exception:
			items = []
		for key, child in items:
			lkey = str(key).lower()
			if 'position' in lkey or str(key).isdigit():
				add_vec(_vec2_from_section(child))
			walk(child, depth + 1)

	walk(section, 0)
	return result


def _snap_to_ground(space_id, x, z, fallback_y=100.0):
	try:
		import BigWorld, Math
		hit = BigWorld.wg_collideSegment(
			space_id,
			Math.Vector3(x, 1000.0, z),
			Math.Vector3(x, -1000.0, z),
			128
		)
		if hit is not None:
			return hit[0].y
	except Exception:
		pass
	return fallback_y


def _points_for_team(player, team):
	try:
		import ResMgr
		arena_type = player.arena.arenaType
		map_name = _short_geometry_name(arena_type)
		LOG_DEBUG('OfflineBattle.spawn.dbg team', team, 'map_name', repr(map_name),
		          'geometryName', repr(getattr(arena_type, 'geometryName', '?')),
		          'gameplayName', repr(getattr(arena_type, 'gameplayName', '?')))
		if not map_name:
			LOG_DEBUG('OfflineBattle.spawn.dbg no map_name')
			return []
		section = ResMgr.openSection('scripts/arena_defs/%s.xml' % map_name)
		LOG_DEBUG('OfflineBattle.spawn.dbg section opened:', section is not None)
		if section is None:
			return []
		gameplay_name = getattr(arena_type, 'gameplayName', 'ctf') or 'ctf'
		gp = section['gameplayTypes/%s' % gameplay_name]
		LOG_DEBUG('OfflineBattle.spawn.dbg gameplay', repr(gameplay_name), 'gp found:', gp is not None)
		if gp is None and gameplay_name != 'ctf':
			gp = section['gameplayTypes/ctf']
			LOG_DEBUG('OfflineBattle.spawn.dbg ctf fallback gp found:', gp is not None)
		if gp is None:
			return []
		team_key = 'team%d' % int(team)
		sp_points = _collect_positions(gp['teamSpawnPoints/%s' % team_key])
		bp_points = _collect_positions(gp['teamBasePositions/%s' % team_key])
		LOG_DEBUG('OfflineBattle.spawn.dbg', team_key, 'teamSpawnPoints', len(sp_points),
		          sp_points[:3], 'teamBasePositions', len(bp_points), bp_points[:3])
		points = sp_points if sp_points else bp_points
		return points
	except Exception as exc:
		import traceback
		LOG_DEBUG('OfflineBattle.spawn.pointsError', team, exc, traceback.format_exc())
	return []


def _space_settings_fallback(player):
	try:
		import ResMgr, Math
		map_name = _short_geometry_name(player.arena.arenaType)
		section = ResMgr.openSection('spaces/%s/space.settings' % map_name)
		if section is not None:
			pos = Math.Vector3(0, 100.0, 0)
			yaw = math.pi
			try:
				if section.has_key('startPosition'):
					pos = section.readVector3('startPosition')
				if section.has_key('startDirection'):
					yaw = section.readVector3('startDirection').z
			except Exception:
				pass
			return (pos, yaw)
	except Exception:
		pass
	return None


def _yaw_between(a, b, default_yaw=0.0):
	try:
		return math.atan2(b.x - a.x, b.z - a.z)
	except Exception:
		return default_yaw


def _offset_position(space_id, pos, yaw, spawn_index, point_count):
	try:
		import Math
		point_count = max(int(point_count), 1)
		cycle = int(spawn_index) // point_count
		if cycle <= 0:
			return pos
		rank = cycle - 1
		slot = rank % 5
		depth = rank // 5 + 1
		side = (slot - 2) * 4.0
		back = depth * 7.0
		x = pos.x + math.cos(yaw) * side - math.sin(yaw) * back
		z = pos.z - math.sin(yaw) * side - math.cos(yaw) * back
		y = _snap_to_ground(space_id, x, z, pos.y)
		return Math.Vector3(x, y, z)
	except Exception:
		return pos


def resolve_spawn(player, team=1, spawn_index=0, allow_space_settings=True):
	try:
		import Math
		space_id = getattr(player, 'spaceID', 0)
		team = int(team)
		points = _points_for_team(player, team)
		enemy_points = _points_for_team(player, 2 if team == 1 else 1)
		if points:
			idx = int(spawn_index) % len(points)
			x, z = points[idx]
			y = _snap_to_ground(space_id, x, z)
			pos = Math.Vector3(x, y, z)
			if enemy_points:
				ex, ez = enemy_points[int(spawn_index) % len(enemy_points)]
				enemy_pos = Math.Vector3(ex, _snap_to_ground(space_id, ex, ez), ez)
				yaw = _yaw_between(pos, enemy_pos, 0.0 if team == 1 else math.pi)
			else:
				yaw = 0.0 if team == 1 else math.pi
			pos = _offset_position(space_id, pos, yaw, int(spawn_index), len(points))
			LOG_DEBUG('OfflineBattle.spawn.resolve', 'team', team, 'idx', spawn_index, 'points', len(points), 'pos', pos, 'yaw', yaw)
			return (pos, yaw)
		if allow_space_settings:
			fallback = _space_settings_fallback(player)
			if fallback is not None:
				LOG_DEBUG('OfflineBattle.spawn.spaceSettingsFallback', fallback[0], fallback[1])
				return fallback
	except Exception as exc:
		LOG_DEBUG('OfflineBattle.spawn.resolveError', team, spawn_index, exc)
	if not allow_space_settings:
		return (None, None)
	try:
		import Math
		return (Math.Vector3(0, 100.0, 0), math.pi)
	except Exception:
		return (None, math.pi)


def resolve_player_spawn(player):
	return resolve_spawn(player, 1, 0, True)


def resolve_bot_spawn(player, team, spawn_index):
	return resolve_spawn(player, team, spawn_index, False)
