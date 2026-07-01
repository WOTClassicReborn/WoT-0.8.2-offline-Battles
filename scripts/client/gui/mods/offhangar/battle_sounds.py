from gui.mods.offhangar.logging import LOG_DEBUG

try:
	_STRING_TYPES = (basestring,)
except NameError:
	_STRING_TYPES = (str,)


def _safe_call(obj, name, *args):
	try:
		fn = getattr(obj, name, None)
		if callable(fn):
			return fn(*args)
	except Exception:
		pass
	return None


def _music_controller():
	try:
		import MusicController
		return (MusicController, getattr(MusicController, 'g_musicController', None))
	except Exception:
		return (None, None)


def _arena_type(player):
	try:
		return player.arena.arenaType
	except Exception:
		return None


def _event_const(module, *names):
	if module is None:
		return None
	for name in names:
		try:
			if hasattr(module, name):
				return getattr(module, name)
		except Exception:
			pass
	return None


def _arena_sound_name(player, event_id, module):
	arena_type = _arena_type(player)
	if arena_type is None:
		return ''
	pairs = (
		(_event_const(module, 'MUSIC_EVENT_COMBAT_LOADING'), 'loadingMusic'),
		(_event_const(module, 'MUSIC_EVENT_COMBAT'), 'music'),
		(_event_const(module, 'AMBIENT_EVENT_COMBAT'), 'ambientSound'),
	)
	for const_value, attr_name in pairs:
		if const_value is not None and event_id == const_value:
			try:
				value = getattr(arena_type, attr_name, '') or ''
				if isinstance(value, (tuple, list)) and value:
					value = value[0]
				return str(value)
			except Exception:
				return ''
	return ''


def _patch_music_controller(player):
	module, controller = _music_controller()
	if module is None or controller is None:
		return None
	if not hasattr(controller, '_offhangar_orig_getArenaSoundEvent'):
		try:
			controller._offhangar_orig_getArenaSoundEvent = getattr(controller, '_MusicController__getArenaSoundEvent')
		except Exception:
			controller._offhangar_orig_getArenaSoundEvent = None

	def _offline_get_arena_sound_event(self, event_id):
		name = _arena_sound_name(player, event_id, module)
		if name:
			try:
				import FMOD
				LOG_DEBUG('OfflineBattle.sound.resolve', event_id, name)
				return FMOD.getSound(name)
			except Exception as exc:
				LOG_DEBUG('OfflineBattle.sound.resolveFailed', event_id, name, exc)
		orig = getattr(self, '_offhangar_orig_getArenaSoundEvent', None)
		if callable(orig):
			try:
				return orig(event_id)
			except TypeError:
				try:
					return orig(self, event_id)
				except Exception:
					pass
			except Exception:
				pass
		return None

	try:
		import types
		try:
			controller._MusicController__getArenaSoundEvent = types.MethodType(_offline_get_arena_sound_event, controller)
		except TypeError:
			controller._MusicController__getArenaSoundEvent = types.MethodType(_offline_get_arena_sound_event, controller, controller.__class__)
	except Exception as exc:
		LOG_DEBUG('OfflineBattle.sound.patchFailed', exc)
	return controller


def _set_sound_groups(in_battle):
	try:
		import SoundGroups
		sg = getattr(SoundGroups, 'g_instance', None)
		if sg is None:
			return
		_safe_call(sg, 'enableLobbySounds', not in_battle)
		_safe_call(sg, 'enableArenaSounds', in_battle)
		_safe_call(sg, 'setVolume', 'music', 1.0)
		_safe_call(sg, 'setVolume', 'ambient', 1.0)
		_safe_call(sg, 'setVolume', 'vehicles', 1.0)
		_safe_call(sg, 'setVolume', 'effects', 1.0)
	except Exception:
		pass


def _play(controller, event_id):
	if controller is None or event_id is None:
		return False
	try:
		controller.play(event_id)
		return True
	except Exception as exc:
		LOG_DEBUG('OfflineBattle.sound.playFailed', event_id, exc)
	return False


def _stop_private_event_handles(controller):
	if controller is None:
		return
	for attr_name in ('_MusicController__sndEventMusic', '_MusicController__sndEventAmbient'):
		event = getattr(controller, attr_name, None)
		if event is not None:
			try:
				event.stop()
			except Exception:
				pass
			try:
				setattr(controller, attr_name, None)
			except Exception:
				pass


def _stop_controller_audio(controller):
	if controller is None:
		return
	_stop_private_event_handles(controller)
	_safe_call(controller, 'stopAmbient')
	_safe_call(controller, 'stopMusic')


def start_loading_audio(player):
	module, controller = _music_controller()
	_set_sound_groups(True)
	controller = _patch_music_controller(player) or controller
	_stop_controller_audio(controller)
	_play(controller, _event_const(module, 'MUSIC_EVENT_COMBAT_LOADING'))
	_play(controller, _event_const(module, 'AMBIENT_EVENT_COMBAT'))
	LOG_DEBUG('OfflineBattle.sound.loadingStarted')


def start_combat_audio(player):
	module, controller = _music_controller()
	_set_sound_groups(True)
	controller = _patch_music_controller(player) or controller
	_stop_controller_audio(controller)
	_play(controller, _event_const(module, 'MUSIC_EVENT_COMBAT'))
	_play(controller, _event_const(module, 'AMBIENT_EVENT_COMBAT'))
	LOG_DEBUG('OfflineBattle.sound.combatStarted')


def stop_battle_audio():
	module, controller = _music_controller()
	if controller is not None:
		_stop_controller_audio(controller)
		_safe_call(controller, 'stop')
	_set_sound_groups(False)
	LOG_DEBUG('OfflineBattle.sound.stopped')


def play_result_audio(result_name):
	module, controller = _music_controller()
	if controller is None:
		return
	events = {
		'victory': _event_const(module, 'MUSIC_EVENT_COMBAT_VICTORY', 'MUSIC_EVENT_VICTORY'),
		'defeat': _event_const(module, 'MUSIC_EVENT_COMBAT_LOSE', 'MUSIC_EVENT_LOSE'),
		'draw': _event_const(module, 'MUSIC_EVENT_COMBAT_DRAW', 'MUSIC_EVENT_DRAW')
	}
	_play(controller, events.get(result_name))


def play_notification(names):
	try:
		import BigWorld
		player = BigWorld.player()
		if player is None:
			return False
		if not hasattr(player, 'soundNotifications'):
			import gui.IngameSoundNotifications as IngameSoundNotifications
			player.soundNotifications = IngameSoundNotifications.IngameSoundNotifications()
			player.soundNotifications.start()
		for name in names:
			try:
				player.soundNotifications.play(name)
				LOG_DEBUG('OfflineBattle.sound.notification', name)
				return True
			except Exception:
				continue
	except Exception:
		pass
	return False


def play_vehicle_sound(model, event_name):
	if model is None or not event_name:
		return False
	try:
		model.playSound(event_name)
		return True
	except Exception:
		return False


def _sound_event_from_value(value):
	if value is None:
		return ''
	try:
		if isinstance(value, _STRING_TYPES):
			value = str(value)
			if value.startswith('/tanks/guns/') or value.startswith('gun_') or '/guns/' in value:
				return value
			return ''
	except Exception:
		pass
	try:
		if isinstance(value, (tuple, list)):
			for item in value:
				event_name = _sound_event_from_value(item)
				if event_name:
					return event_name
	except Exception:
		pass
	try:
		if hasattr(value, 'get'):
			for key in ('shotSound', 'shootSound', 'fireSound', 'sound', 'event', 'eventName', 'name'):
				event_name = _sound_event_from_value(value.get(key, None))
				if event_name:
					return event_name
	except Exception:
		pass
	for attr_name in ('shotSound', 'shootSound', 'fireSound', 'sound', 'event', 'eventName', 'name'):
		try:
			event_name = _sound_event_from_value(getattr(value, attr_name, None))
			if event_name:
				return event_name
		except Exception:
			pass
	return ''


def _shot_from_gun(gun_descr, shot_index):
	try:
		shots = gun_descr.get('shots', [])
	except Exception:
		shots = []
	try:
		if not shots and hasattr(gun_descr, 'shots'):
			shots = gun_descr.shots
	except Exception:
		pass
	if not shots:
		return None
	try:
		shot_index = int(shot_index)
	except Exception:
		shot_index = 0
	if shot_index < 0:
		shot_index = 0
	if shot_index >= len(shots):
		shot_index = len(shots) - 1
	return shots[shot_index]


def gun_sound_event_from_descriptor(gun_descr, shot_index=0):
	for key in ('shotSound', 'shootSound', 'fireSound', 'sound', 'effects'):
		try:
			event_name = _sound_event_from_value(gun_descr.get(key, None))
			if event_name:
				return event_name
		except Exception:
			pass
	shot = _shot_from_gun(gun_descr, shot_index)
	shell = {}
	if shot is not None:
		try:
			shell = shot.get('shell', {}) or {}
		except Exception:
			shell = {}
		try:
			from items import vehicles
			effects_descr = vehicles.g_cache.shotEffects[shell['effectsIndex']]
			event_name = _sound_event_from_value(effects_descr)
			if event_name:
				return event_name
		except Exception:
			pass
	return gun_sound_event(shell.get('caliber', 75.0) if hasattr(shell, 'get') else 75.0)


def gun_sound_event(caliber):
	try:
		caliber = float(caliber)
	except Exception:
		caliber = 75.0
	if caliber >= 150:
		return '/tanks/guns/gun_huge/gun_huge_152mm'
	if caliber > 100:
		return '/tanks/guns/gun_large/gun_large_115-152mm'
	if caliber > 75:
		return '/tanks/guns/gun_main/gun_main_85-107mm'
	if caliber > 45:
		return '/tanks/guns/gun_medium/gun_medium_50-75mm'
	return '/tanks/guns/gun_small/gun_small_20-45mm'


def play_gunshot(model, caliber_or_gun_descr, shot_index=0):
	try:
		if hasattr(caliber_or_gun_descr, 'get'):
			return play_vehicle_sound(model, gun_sound_event_from_descriptor(caliber_or_gun_descr, shot_index))
	except Exception:
		pass
	return play_vehicle_sound(model, gun_sound_event(caliber_or_gun_descr))
