from otree.api import *
import random
from datetime import datetime


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

    treatment = models.StringField(blank=True)

    contribution = models.IntegerField(
        min=0,
        max=C.ENDOWMENT
    )

    intention = models.IntegerField(
        min=0,
        max=C.ENDOWMENT,
        blank=True
    )


    quiz_passed = models.StringField(blank=True)
    chat_quiz_passed = models.StringField(blank=True)
    binary_quiz_passed = models.StringField(blank=True)


# Stores one row per chat message — avoids race conditions and captures full history
class ChatMessage(ExtraModel):
    group = models.Link(Group)
    round_number = models.IntegerField()
    participant_code = models.StringField()
    sender_id = models.IntegerField()
    message = models.StringField()
    timestamp = models.StringField()


def custom_export(_players):
    # Available in Admin → Data → "pgg (custom export)"
    yield ['sep=,']
    yield ['session.code', 'round_number', 'group.id_in_subsession', 'participant.code', 'id_in_group', 'body', 'timestamp']
    for msg in ChatMessage.filter():
        group = msg.group
        if group.field_maybe_none('treatment') != 'Chat':
            continue
        yield [
            group.session.code,
            msg.round_number,
            group.id_in_subsession,
            msg.participant_code,
            msg.sender_id,
            msg.message,
            msg.timestamp,
        ]


def creating_session(subsession: Subsession):

    if subsession.round_number == 1:

        subsession.group_randomly()
        groups = subsession.get_groups()

        # Use forced_treatment if set (demo single-treatment configs), otherwise random balanced assignment
        forced = subsession.session.config.get('forced_treatment')
        if forced:
            treatments = [forced] * len(groups)
        else:
            treatments = (['Control', 'Binary', 'Chat'] * len(groups))[:len(groups)]
            random.shuffle(treatments)

        for g, treatment in zip(groups, treatments):
            g.treatment = treatment
            # Also store treatment on each player for cross-round access
            for p in g.get_players():
                p.treatment = treatment

    else:
        # Reshuffle players within their treatment — players never cross treatment boundaries
        players = subsession.get_players()

        buckets = {'Control': [], 'Binary': [], 'Chat': []}
        for p in players:
            t = p.in_round(1).treatment   # read treatment assigned in round 1
            p.treatment = t               # propagate to current round
            buckets[t].append(p)

        # Shuffle within each treatment bucket and build new group matrix
        new_matrix = []
        for t_players in buckets.values():
            random.shuffle(t_players)
            for i in range(0, len(t_players), C.PLAYERS_PER_GROUP):
                chunk = t_players[i:i + C.PLAYERS_PER_GROUP]
                if len(chunk) == C.PLAYERS_PER_GROUP:
                    new_matrix.append(chunk)

        subsession.set_group_matrix(new_matrix)

        # Set treatment on each new group
        for g in subsession.get_groups():
            g.treatment = g.get_players()[0].treatment

# PAGES

class Introduction(Page):

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1


class Quiz(Page):
    form_model = 'player'
    form_fields = ['quiz_passed']

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def error_message(_player, values):
        if values['quiz_passed'] != 'yes':
            return "Some answers are incorrect. Please review and try again."


class ChatInfo(Page):

    @staticmethod
    def is_displayed(player):
        return (player.round_number == 1 and
                player.group.field_maybe_none('treatment') == 'Chat')


class ChatQuiz(Page):

    form_model = 'player'
    form_fields = ['chat_quiz_passed']

    @staticmethod
    def is_displayed(player):
        return (player.round_number == 1 and
                player.group.field_maybe_none('treatment') == 'Chat')

    @staticmethod
    def error_message(_player, values):
        if values['chat_quiz_passed'] != 'yes':
            return "Some answers are incorrect. Please review and try again."

class BinaryInfo(Page):

    @staticmethod
    def is_displayed(player):
        return (player.round_number == 1 and
                player.group.field_maybe_none('treatment') == 'Binary')


class BinaryQuiz(Page):

    form_model = 'player'
    form_fields = ['binary_quiz_passed']

    @staticmethod
    def is_displayed(player):
        return (player.round_number == 1 and
                player.group.field_maybe_none('treatment') == 'Binary')

    @staticmethod
    def error_message(_player, values):
        if values['binary_quiz_passed'] != 'yes':
            return "Some answers are incorrect. Please review and try again."


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
            return 90
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
            participant_code=player.participant.code,
            sender_id=player.id_in_group,
            message=message,
            timestamp=datetime.now().strftime('%H:%M:%S'),
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

    @staticmethod
    def vars_for_template(player):
        played_rounds = player.session.config['num_rounds']
        all_rounds = player.in_all_rounds()[:played_rounds]
        rounds_data = [
            dict(
                round=p.round_number,
                contribution=p.contribution,
                group_total=p.group.total_contribution,
                threshold_met=p.group.threshold_met,
                payoff=p.payoff,
            )
            for p in all_rounds
        ]
        total_payoff = sum(p.payoff for p in all_rounds)
        return dict(
            rounds_data=rounds_data,
            total_payoff=total_payoff,
        )


page_sequence = [
    Introduction,
    Quiz,
    ChatInfo,
    ChatQuiz,
    BinaryInfo,
    BinaryQuiz,
    WaitBeforeChat,
    Communication,
    WaitAfterBinary,
    Contribution,
    WaitForOthers,
    Results,
    FinalResults
]