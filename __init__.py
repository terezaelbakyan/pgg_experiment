from otree.api import (
    models,
    widgets,
    BaseConstants,
    BaseSubsession,
    BaseGroup,
    BasePlayer,
    Currency as c,
    currency_range,
    Page,
)

class Constants(BaseConstants):
    NAME_IN_URL = 'pgg'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 1   # only 1 round for testing

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):
    pass

class Player(BasePlayer):
    pass

class TestPage(Page):
    @staticmethod
    def vars_for_template(player):
        return dict(test_message="THIS TEXT SHOULD APPEAR IF TEMPLATE LOADS")

page_sequence = [TestPage]