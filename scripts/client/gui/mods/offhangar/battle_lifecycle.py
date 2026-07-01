from gui.mods.offhangar.logging import LOG_DEBUG


STATE_HANGAR = 'HANGAR'
STATE_QUEUED = 'QUEUED'
STATE_LOADING = 'LOADING'
STATE_PREBATTLE = 'PREBATTLE'
STATE_BATTLE = 'BATTLE'
STATE_RESULTS = 'RESULTS'

_VALID_STATES = (
	STATE_HANGAR,
	STATE_QUEUED,
	STATE_LOADING,
	STATE_PREBATTLE,
	STATE_BATTLE,
	STATE_RESULTS
)

_STATE = {
	'name': STATE_HANGAR,
	'reason': 'init',
	'seq': 0
}


def set_battle_state(name, reason=''):
	if name not in _VALID_STATES:
		LOG_DEBUG('BattleLifecycle.invalid', name, reason)
		return _STATE['name']
	if _STATE['name'] == name and _STATE['reason'] == reason:
		return _STATE['name']
	_STATE['name'] = name
	_STATE['reason'] = reason
	_STATE['seq'] += 1
	LOG_DEBUG('BattleLifecycle.state', _STATE['seq'], name, reason)
	return name


def get_battle_state():
	return _STATE.copy()


def is_battle_live():
	return _STATE['name'] in (STATE_PREBATTLE, STATE_BATTLE)

