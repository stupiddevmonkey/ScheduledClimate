"""Constants for Scheduled Climate."""

from homeassistant.components.climate import HVACMode

DOMAIN = "scheduled_climate"
CONF_TARGET_ENTITY_ID = "target_entity_id"
CONF_SCHEDULE_ENTITY_ID = "schedule_entity_id"
CONF_SCHEDULE_ENABLED = "schedule_enabled"
CONF_DEFAULT_HVAC_MODE = "default_hvac_mode"
CONF_OFF_BEHAVIOR = "off_behavior"
CONF_APPLY_ON_START = "apply_on_start"
CONF_LEGACY_ON_TIME = "legacy_on_time"
CONF_LEGACY_OFF_TIME = "legacy_off_time"

SERVICE_START_ON_TIMER = "start_on_timer"
SERVICE_START_OFF_TIMER = "start_off_timer"
SERVICE_CANCEL_TIMER = "cancel_timer"
SERVICE_LINK_SCHEDULE = "link_schedule"
SERVICE_ENABLE_SCHEDULE = "enable_schedule"
SERVICE_DISABLE_SCHEDULE = "disable_schedule"

ATTR_DURATION = "duration"
ATTR_SCHEDULE_ID = "schedule_id"
ATTR_TIMER_ACTION = "timer_action"
ATTR_TIMER_DEADLINE = "timer_deadline"

OFF_BEHAVIOR_TURN_OFF = "turn_off"
OFF_BEHAVIOR_IGNORE = "ignore"
OFF_BEHAVIORS = (OFF_BEHAVIOR_TURN_OFF, OFF_BEHAVIOR_IGNORE)

DEFAULT_SCHEDULE_ENABLED = False
DEFAULT_HVAC_MODE = HVACMode.HEAT
DEFAULT_OFF_BEHAVIOR = OFF_BEHAVIOR_TURN_OFF
DEFAULT_APPLY_ON_START = True

ISSUE_SCHEDULE_MISSING = "schedule_missing"
ISSUE_SCHEDULE_NOT_LINKED = "schedule_not_linked"
ISSUE_BLOCK_UNSUPPORTED = "block_unsupported"

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
