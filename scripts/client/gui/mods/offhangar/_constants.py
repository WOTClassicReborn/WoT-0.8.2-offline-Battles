import cPickle
import json
import os

import BigWorld
from debug_utils import LOG_DEBUG, LOG_ERROR
import sys


CONFIG_DEFAULTS = {
    'nickname': 'DrWeb7_1',
    'bot_name_prefix_allies': 'Ally_',
    'bot_name_prefix_enemies': 'Enemy_',
    'queue_wait_time_seconds': 4.0,
    'loading_screen_time_seconds': 5.0,
    'unknown_command_policy': 'compat_success',
    'enable_debug_session_patches': False,
    'physics_terrain_index': 0,
    'physics_engine_brake_factor': 1.15,
    'physics_slope_gravity_factor': 0.85
}


def _clamp_float(value, default, min_value, max_value):
    try:
        value = float(value)
    except Exception:
        return default
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def _clean_text(value, default, max_len=32):
    try:
        value = str(value)
    except Exception:
        return default
    value = ''.join(ch for ch in value if ch.isalnum() or ch in ('_', '-', '[', ']'))
    if not value:
        return default
    return value[:max_len]


def _load_config_options():
    raw = {}
    try:
        this_file = sys._getframe().f_code.co_filename
        path = os.path.normpath(os.path.join(os.path.dirname(this_file), 'config.json'))
        LOG_DEBUG('Loading config from: ' + path)
        with open(path, 'r') as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            raw = loaded
        else:
            LOG_ERROR('Config root is not a dict; defaults used')
    except Exception, e:
        LOG_ERROR('Failed to load config: ' + str(e))

    cfg = CONFIG_DEFAULTS.copy()
    cfg.update(raw)
    cfg['nickname'] = _clean_text(cfg.get('nickname'), CONFIG_DEFAULTS['nickname'], 32)
    cfg['bot_name_prefix_allies'] = _clean_text(cfg.get('bot_name_prefix_allies'), CONFIG_DEFAULTS['bot_name_prefix_allies'], 20)
    cfg['bot_name_prefix_enemies'] = _clean_text(cfg.get('bot_name_prefix_enemies'), CONFIG_DEFAULTS['bot_name_prefix_enemies'], 20)
    cfg['queue_wait_time_seconds'] = _clamp_float(cfg.get('queue_wait_time_seconds'), CONFIG_DEFAULTS['queue_wait_time_seconds'], 0.0, 30.0)
    cfg['loading_screen_time_seconds'] = _clamp_float(cfg.get('loading_screen_time_seconds'), CONFIG_DEFAULTS['loading_screen_time_seconds'], 0.0, 30.0)
    cfg['physics_engine_brake_factor'] = _clamp_float(cfg.get('physics_engine_brake_factor'), CONFIG_DEFAULTS['physics_engine_brake_factor'], 0.2, 5.0)
    cfg['physics_slope_gravity_factor'] = _clamp_float(cfg.get('physics_slope_gravity_factor'), CONFIG_DEFAULTS['physics_slope_gravity_factor'], 0.0, 2.0)
    try:
        cfg['physics_terrain_index'] = max(0, min(2, int(cfg.get('physics_terrain_index'))))
    except Exception:
        cfg['physics_terrain_index'] = CONFIG_DEFAULTS['physics_terrain_index']
    if cfg.get('unknown_command_policy') not in ('compat_success', 'fail_stateful'):
        cfg['unknown_command_policy'] = CONFIG_DEFAULTS['unknown_command_policy']
    cfg['enable_debug_session_patches'] = bool(cfg.get('enable_debug_session_patches'))
    LOG_DEBUG('Config loaded successfully: ' + str(cfg))
    return cfg


CONFIG_OPTIONS = _load_config_options()

from chat_shared import CHAT_RESPONSES

OFFLINE_SERVER_ADDRESS = 'offline.loc'
OFFLINE_NICKNAME = str(CONFIG_OPTIONS.get('nickname', 'DrWeb7_1'))
OFFLINE_LOGIN = OFFLINE_NICKNAME + '@' + OFFLINE_SERVER_ADDRESS
OFFLINE_PWD = '1'
OFFLINE_DBID = 13028161

OFFLINE_GUI_CTX = cPickle.dumps({
    'databaseID': OFFLINE_DBID,
    'logUXEvents': False,
    'aogasStartedAt': 0,
    'sessionStartedAt': 0,
    'isAogasEnabled': False,
    'collectUiStats': False,
    'isLongDisconnectedFromCenter': False,
}, cPickle.HIGHEST_PROTOCOL)

OFFLINE_SERVER_SETTINGS = {
    'regional_settings': {'starting_day_of_a_new_week': 0, 'starting_time_of_a_new_game_day': 0, 'starting_time_of_a_new_day': 0, 'starting_day_of_a_new_weak': 0},
    'xmpp_enabled': False,
    'xmpp_port': 0,
    'xmpp_host': '',
    'xmpp_muc_enabled': False,
    'xmpp_muc_services': [],
    'xmpp_resource': '',
    'xmpp_bosh_connections': [],
    'xmpp_connections': [],
    'xmpp_alt_connections': [],
    'file_server': {},
    'voipDomain': '',
    'voipUserDomain': ''
}

CHAT_ACTION_DATA = {
    'requestID': None,
    'action': None,
    'actionResponse': CHAT_RESPONSES.internalError.index(),
    'time': 0,
    'sentTime': 0,
    'channel': 0,
    'originator': 0,
    'originatorNickName': '',
    'group': 0,
    'data': {},
    'flags': 0
}

REQUEST_CALLBACK_TIME = 0.5
