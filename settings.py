SECRET_KEY = 'abcdefghijklmnopqrstuvwxyz1234567890randomstringpleasechange'

INSTALLED_APPS = ['pgg', 'otree']

SESSION_CONFIGS = [
    dict(
        name='pgg_multi_treatment',
        display_name="Public Goods Game (All Treatments)",
        num_demo_participants=9,  # must be a multiple of 9 (3 treatments × 3 players per group). Min = 9.
        app_sequence=['pgg'],
        num_rounds=4,
    ),
    # --- Demo-only single-treatment configs ---
    dict(
        name='pgg_control',
        display_name="Public Goods Game — Control (Demo)",
        num_demo_participants=3,
        app_sequence=['pgg'],
        num_rounds=4,
        forced_treatment='Control',
    ),
    dict(
        name='pgg_binary',
        display_name="Public Goods Game — Binary (Demo)",
        num_demo_participants=3,
        app_sequence=['pgg'],
        num_rounds=4,
        forced_treatment='Binary',
    ),
    dict(
        name='pgg_chat',
        display_name="Public Goods Game — Chat (Demo)",
        num_demo_participants=3,
        app_sequence=['pgg'],
        num_rounds=4,
        forced_treatment='Chat',
    ),
    # --- Bot test config (999 players = 333 groups, 111 per treatment) ---
    dict(
        name='pgg_bot_test',
        display_name="Public Goods Game — Bot Test (999 players)",
        num_demo_participants=999,
        app_sequence=['pgg'],
        num_rounds=20,
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=0.01,
    participation_fee=1.00,
)

POINTS_DECIMAL_PLACES = 2

# These lines are required to avoid the LANGUAGE_CODE error
LANGUAGE_CODE = 'en'
USE_I18N = True
USE_L10N = True
TIME_ZONE = 'UTC'
USE_TZ = True

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'otree'