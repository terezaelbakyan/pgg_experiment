from otree.api import Bot, Submission
import random

from . import (
    Gender, Introduction, Quiz,
    ChatInfo, ChatQuiz,
    BinaryInfo, BinaryQuiz,
    Communication, Contribution, Results, FinalResults,
)


class PlayerBot(Bot):

    def play_round(self):
        num_rounds = self.session.config['num_rounds']
        treatment = self.player.group.field_maybe_none('treatment')

        # --- Round 1 only pages ---
        if self.round_number == 1:
            yield Submission(Gender, {'gender': random.choice(['Male', 'Female'])}, check_html=False)
            yield Submission(Introduction, check_html=False)
            yield Submission(Quiz, {'quiz_passed': 'yes'}, check_html=False)

            if treatment == 'Chat':
                yield Submission(ChatInfo, check_html=False)
                yield Submission(ChatQuiz, {'chat_quiz_passed': 'yes'}, check_html=False)
            elif treatment == 'Binary':
                yield Submission(BinaryInfo, check_html=False)
                yield Submission(BinaryQuiz, {'binary_quiz_passed': 'yes'}, check_html=False)

        # --- Active rounds only ---
        if self.round_number <= num_rounds:
            if treatment == 'Chat':
                # Simulate timer expiring — no waiting 90 seconds
                yield Submission(Communication, timeout_happened=True, check_html=False)
            elif treatment == 'Binary':
                yield Submission(
                    Communication,
                    {'intention': random.randint(0, 10)},
                    check_html=False,
                )

            yield Submission(Contribution, {'contribution': random.randint(0, 10)}, check_html=False)
            yield Submission(Results, check_html=False)

        # --- Final round only ---
        if self.round_number == num_rounds:
            yield Submission(FinalResults, check_html=False)
