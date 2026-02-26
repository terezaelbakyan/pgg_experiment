from otree.api import *
import random


class C(BaseConstants):
    NAME_IN_URL = 'pgg'
    PLAYERS_PER_GROUP = 3
    NUM_ROUNDS = 20  # maximum ceiling; actual rounds controlled by session config num_rounds

    ENDOWMENT = 10
    THRESHOLD = 15
    MULTIPLIER = 2

class Subsession(BaseSubsession):
    pass

class Group(BaseGroup):

    treatment = models.StringField()
    total_contribution = models.IntegerField()
    threshold_met = models.BooleanField()
    chat_transcript = models.LongStringField(blank=True)

    def set_payoffs(self):

        players = self.get_players()

        self.total_contribution = sum(p.contribution for p in players)

        if self.total_contribution >= C.THRESHOLD:
            self.threshold_met = True
            public_good = self.total_contribution * C.MULTIPLIER
            share = public_good / C.PLAYERS_PER_GROUP

            for p in players:
                p.payoff = C.ENDOWMENT - p.contribution + share
        else:
            self.threshold_met = False
            for p in players:
                p.payoff = C.ENDOWMENT - p.contribution


class Player(BasePlayer):

    contribution = models.IntegerField(
        min=0,
        max=C.ENDOWMENT
    )

    intention = models.IntegerField(
        min=0,
        max=C.ENDOWMENT,
        blank=True
    )


    chat_q1 = models.StringField(
        choices=['Yes', 'No'],
        blank=True
    )

    chat_q2 = models.StringField(
        choices=['Yes', 'No'],
        blank=True
    )


# Stores one row per chat message — avoids race conditions and captures full history
class ChatMessage(ExtraModel):
    group = models.Link(Group)
    round_number = models.IntegerField()
    sender_id = models.IntegerField()
    message = models.StringField()


def custom_export(_players):
    # Available in Admin → Data → "pgg (custom export)"
    yield ['sep=,']  # tells Excel to use comma as delimiter when opening directly
    yield ['session_code', 'group_id', 'treatment', 'round_number', 'sender_id', 'message']
    for msg in ChatMessage.filter():
        group = msg.group
        yield [
            group.session.code,
            group.id,
            group.field_maybe_none('treatment') or '',
            msg.round_number,
            msg.sender_id,
            msg.message,
        ]


def creating_session(subsession: Subsession):

    if subsession.round_number == 1:

        subsession.group_randomly()

        groups = subsession.get_groups()

        # Build a shuffled treatment list so assignment is random each session
        treatments = (['Control', 'Binary', 'Chat'] * len(groups))[:len(groups)]
        random.shuffle(treatments)

        for g, treatment in zip(groups, treatments):
            g.treatment = treatment

    else:
        # Keep the same groups and treatments as round 1
        subsession.group_like_round(1)
        for g in subsession.get_groups():
            g.treatment = g.in_round(1).treatment

# PAGES

class Introduction(Page):

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1


class Quiz(Page):
    form_model = 'player'
    form_fields = []

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1


class ChatInfo(Page):

    @staticmethod
    def is_displayed(player):
        return (player.round_number == 1 and
                player.group.field_maybe_none('treatment') == 'Chat')


class ChatQuiz(Page):

    form_model = 'player'
    form_fields = ['chat_q1', 'chat_q2']

    @staticmethod
    def is_displayed(player):
        return (player.round_number == 1 and
                player.group.field_maybe_none('treatment') == 'Chat')

    @staticmethod
    def error_message(player, values):

        if values['chat_q1'] != 'No':
            return "Communication is binding."

        if values['chat_q2'] != 'Yes':
            return "The chat duration is 120 seconds."

class WaitBeforeChat(WaitPage):

    @staticmethod
    def is_displayed(player):
        return player.group.field_maybe_none('treatment') == 'Chat'

class Communication(Page):

    form_model = 'player'
    form_fields = ['intention']

    @staticmethod
    def is_displayed(player):
        return (player.round_number <= player.session.config['num_rounds'] and
                player.group.field_maybe_none('treatment') in ['Binary', 'Chat'])

    @staticmethod
    def get_timeout_seconds(player):
        if player.group.field_maybe_none('treatment') == 'Chat':
            return 120
        return None

    @staticmethod
    def live_method(player, data):
        message = data.get('message', '').strip()
        if not message:
            return {}
        # Store as an individual record — no race conditions, full history preserved
        ChatMessage.create(
            group=player.group,
            round_number=player.round_number,
            sender_id=player.id_in_group,
            message=message,
        )
        # Broadcast to all group members
        return {
            p.id_in_group: {'message': message, 'sender': player.id_in_group}
            for p in player.group.get_players()
        }

    @staticmethod
    def js_vars(player):
        return dict(id_in_group=player.id_in_group)

    @staticmethod
    def vars_for_template(player):
        return dict(
            treatment=player.group.field_maybe_none('treatment')
        )

class Contribution(Page):

    form_model = 'player'
    form_fields = ['contribution']

    @staticmethod
    def is_displayed(player):
        return player.round_number <= player.session.config['num_rounds']

    @staticmethod
    def vars_for_template(player):

        group = player.group
        treatment = group.field_maybe_none('treatment')

        intentions = None

        if treatment == 'Binary':
            intentions = [
                dict(
                    id=p.id_in_group,
                    intention=p.field_maybe_none('intention')
                )
                for p in group.get_players()
            ]

        return dict(
            endowment=C.ENDOWMENT,
            threshold=C.THRESHOLD,
            treatment=treatment,
            intentions=intentions,
        )
    
class WaitAfterBinary(WaitPage):

    @staticmethod
    def is_displayed(player):
        return player.group.field_maybe_none('treatment') == 'Binary'

class WaitForOthers(WaitPage):

    @staticmethod
    def after_all_players_arrive(group: Group):
        group.set_payoffs()
        # Rebuild chat transcript from all stored messages for this group/round
        messages = ChatMessage.filter(group=group)
        if messages:
            group.chat_transcript = '\n'.join(
                f"P{m.sender_id}: {m.message}" for m in messages
            )


class Results(Page):

    @staticmethod
    def is_displayed(player):
        return player.round_number <= player.session.config['num_rounds']

    @staticmethod
    def vars_for_template(player):
        group = player.group
        return dict(
            total_contribution=group.total_contribution,
            threshold_met=group.threshold_met,
            payoff=player.payoff,
            group_players=group.get_players(),
            treatment=group.field_maybe_none('treatment'),
        )


class FinalResults(Page):

    @staticmethod
    def is_displayed(player):
        return player.round_number == player.session.config['num_rounds']


page_sequence = [
    Introduction,
    Quiz,
    ChatInfo,        
    ChatQuiz,        
    WaitBeforeChat,
    Communication,
    WaitAfterBinary,
    Contribution,
    WaitForOthers,
    Results,
    FinalResults
]