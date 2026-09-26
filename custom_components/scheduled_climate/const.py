"""Constants for Scheduled Climate."""

from homeassistant.components.climate import HVACMode

DOMAIN = "scheduled_climate"

CONF_TARGETS = "targets"
CONF_TARGET_KEY = "key"
CONF_TARGET_NAME = "name"
CONF_TARGET_ENTITY_ID = "target_entity_id"

CONF_SCHEDULE_ENTITY_ID = "schedule_entity_id"
CONF_SCHEDULE_ENABLED = "schedule_enabled"
CONF_DEFAULT_HVAC_MODE = "default_hvac_mode"
CONF_OFF_BEHAVIOR = "off_behavior"
CONF_APPLY_ON_START = "apply_on_start"
CONF_LEGACY_ON_TIME = "legacy_on_time"
CONF_LEGACY_OFF_TIME = "legacy_off_time"

CONF_PLANS = "plans"
CONF_PLAN_ID = "id"
CONF_PLAN_NAME = "name"
CONF_PLAN_ICON = "icon"
CONF_PLAN_MIN_OUTDOOR_TEMP = "min_outdoor_temp"
CONF_PLAN_MAX_OUTDOOR_TEMP = "max_outdoor_temp"
CONF_PLAN_SCHEDULES = "schedules"

CONF_PLAN_SELECTION = "plan_selection"
CONF_PLAN_SELECTION_MODE = "mode"
CONF_OUTDOOR_TEMP_ENTITY_ID = "outdoor_temp_entity_id"
CONF_HYSTERESIS = "hysteresis"
CONF_SUSTAIN_MINUTES = "sustain_minutes"

CONF_OVERRIDE = "override"
CONF_OVERRIDE_DEFAULT_MINUTES = "default_minutes"
CONF_OVERRIDE_MAX_MINUTES = "max_minutes"

CONF_HIDE_TARGETS = "hide_targets"

SERVICE_START_ON_TIMER = "start_on_timer"
SERVICE_START_OFF_TIMER = "start_off_timer"
SERVICE_CANCEL_TIMER = "cancel_timer"
SERVICE_LINK_SCHEDULE = "link_schedule"
SERVICE_ENABLE_SCHEDULE = "enable_schedule"
SERVICE_DISABLE_SCHEDULE = "disable_schedule"
SERVICE_SET_OVERRIDE = "set_override"
SERVICE_CLEAR_OVERRIDE = "clear_override"
SERVICE_SELECT_PLAN = "select_plan"

ATTR_DURATION = "duration"
ATTR_SCHEDULE_ID = "schedule_id"
ATTR_TIMER_ACTION = "timer_action"
ATTR_TIMER_DEADLINE = "timer_deadline"
ATTR_UNTIL_NEXT_BLOCK = "until_next_block"
ATTR_PLAN = "plan"

OFF_BEHAVIOR_TURN_OFF = "turn_off"
OFF_BEHAVIOR_IGNORE = "ignore"
OFF_BEHAVIORS = (OFF_BEHAVIOR_TURN_OFF, OFF_BEHAVIOR_IGNORE)

PLAN_MODE_MANUAL = "manual"
PLAN_MODE_OUTDOOR_TEMP = "outdoor_temp"
PLAN_MODES = (PLAN_MODE_MANUAL, PLAN_MODE_OUTDOOR_TEMP)

PLAN_AUTOMATIC = "automatic"

DEFAULT_SCHEDULE_ENABLED = False
DEFAULT_HVAC_MODE = HVACMode.HEAT
DEFAULT_OFF_BEHAVIOR = OFF_BEHAVIOR_TURN_OFF
DEFAULT_APPLY_ON_START = True
DEFAULT_PLAN_NAME = "Default"
DEFAULT_PLAN_SELECTION_MODE = PLAN_MODE_MANUAL
DEFAULT_HYSTERESIS = 2.0
DEFAULT_SUSTAIN_MINUTES = 30
DEFAULT_OVERRIDE_MINUTES = 120
DEFAULT_OVERRIDE_MAX_MINUTES = 480
DEFAULT_HIDE_TARGETS = True

ISSUE_SCHEDULE_MISSING = "schedule_missing"
ISSUE_SCHEDULE_NOT_LINKED = "schedule_not_linked"
ISSUE_BLOCK_UNSUPPORTED = "block_unsupported"
ISSUE_OUTDOOR_SENSOR_UNAVAILABLE = "outdoor_sensor_unavailable"
ISSUE_NO_PLANS = "no_plans"

ATTR_SCHEDULE_ENABLED = "schedule_enabled"
ATTR_SCHEDULE_ENTITY_ID = "schedule_entity_id"
ATTR_SCHEDULE_ACTIVE = "schedule_active"
ATTR_ACTIVE_SCHEDULE_BLOCK = "active_schedule_block"
ATTR_NEXT_SCHEDULE_EVENT = "next_schedule_event"
ATTR_SCHEDULE_ISSUES = "schedule_issues"
ATTR_LEGACY_SCHEDULE = "legacy_schedule"
ATTR_TEMPERATURE_UNIT = "temperature_unit"
ATTR_TARGET_HUMIDITY_STEP = "target_humidity_step"
ATTR_TARGET_TEMP_STEP = "target_temp_step"
ATTR_MAX_HUMIDITY = "max_humidity"
ATTR_MAX_TEMP = "max_temp"
ATTR_MIN_HUMIDITY = "min_humidity"
ATTR_MIN_TEMP = "min_temp"

ATTR_TARGET_KEY = "target_key"
ATTR_ROOM_ENTITIES = "room_entities"
ATTR_PLAN_OPTIONS = "plan_options"
ATTR_PLAN_SCHEDULES = "plan_schedules"
ATTR_ACTIVE_PLAN = "active_plan"
ATTR_PLAN_SELECTION_MODE = "plan_selection_mode"
ATTR_PLAN_RESOLVED_AUTOMATICALLY = "plan_resolved_automatically"
ATTR_OUTDOOR_TEMPERATURE = "outdoor_temperature"
ATTR_OVERRIDE_ACTIVE = "override_active"
ATTR_OVERRIDE_UNTIL = "override_until"
ATTR_OVERRIDE_BLOCK = "override_block"
