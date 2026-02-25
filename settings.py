SECRET_KEY = 'abcdefghijklmnopqrstuvwxyz1234567890randomstringpleasechange'

INSTALLED_APPS = ['pgg', 'otree']

SESSION_CONFIGS = [
    dict(
        name='pgg_multi_treatment',
        display_name="Public Goods Game (All Treatments in One Session)",
        num_demo_participants=9,  # min 9, multiples of 9
        app_sequence=['pgg'],
        num_rounds=4,  # <-- change this to set the number of rounds per session
    ),
]

SESSION_CONFIG_DEFAULTS = dict(
    real_world_currency_per_point=0.01,
    participation_fee=1.00,
)

# These lines are required to avoid the LANGUAGE_CODE error
LANGUAGE_CODE = 'en'
USE_I18N = True
USE_L10N = True
TIME_ZONE = 'UTC'
USE_TZ = True

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'otree'