"""
AI vs AI Public Goods Game Simulation
9 Claude agents (3 per treatment: Control, Binary, Chat)
20 rounds, stranger matching within treatment
"""

import sys
import random
import json
import pandas as pd
from datetime import datetime

MOCK_MODE = "--mock" in sys.argv  # run with: python ai_simulation.py --mock

# ── Game constants ─────────────────────────────────────────────
ENDOWMENT = 10
THRESHOLD = 15
MULTIPLIER = 2
NUM_ROUNDS = 20
PLAYERS_PER_GROUP = 3

SYSTEM_PROMPT = """You are a participant in a repeated public goods game experiment.

RULES:
- Each round you receive 10 coins as your endowment
- You are in a group of 3 participants each round
- You choose how many coins to contribute to a public project (integer: 0 to 10)
- The project succeeds only if total group contributions reach at least 15 coins

If the project succeeds (total >= 15):
  Your payoff = 10 - your_contribution + (2 x total_contributions / 3)

If the project fails (total < 15):
  All contributions are lost.
  Your payoff = 10 - your_contribution

Groups are reshuffled each round — you may play with different partners.
Your goal is to maximize your TOTAL payoff across all rounds.

Always reply with valid JSON only. No extra text outside the JSON."""


# ── AI Player ──────────────────────────────────────────────────
class AIPlayer:
    def __init__(self, player_id, treatment, client):
        self.player_id = player_id
        self.treatment = treatment
        self.client = client
        self.history = []
        self.total_payoff = 0
        self.round_data = []

    def _call(self, prompt):
        if MOCK_MODE:
            # Simple rule-based mock: no API calls, no cost
            if '"message"' in prompt:
                reply = '{"message": "Let\'s all contribute 5 to reach the threshold."}'
            elif '"intention"' in prompt:
                reply = f'{{"intention": {random.randint(4, 6)}}}'
            else:
                # Conditional cooperator: contribute more if last round succeeded
                last_met = self.round_data and self.round_data[-1]["threshold_met"]
                contrib = random.randint(5, 8) if last_met else random.randint(3, 6)
                reply = f'{{"contribution": {contrib}, "reasoning": "mock reasoning"}}'
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": reply})
            return reply

        import anthropic
        self.history.append({"role": "user", "content": prompt})
        response = self.client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=SYSTEM_PROMPT,
            messages=self.history,
        )
        reply = response.content[0].text.strip()
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def _last_round_summary(self, round_number):
        if round_number == 1 or not self.round_data:
            return "This is the first round — no previous results yet."
        last = self.round_data[-1]
        status = "SUCCEEDED (threshold met)" if last["threshold_met"] else "FAILED (threshold not met)"
        return (
            f"Last round result: you contributed {last['contribution']} coins | "
            f"group total: {last['group_total']} | project {status} | "
            f"your payoff: {last['payoff']:.1f} | cumulative payoff: {self.total_payoff:.1f}"
        )

    def get_chat_message(self, round_number):
        prompt = (
            f"Round {round_number} of {NUM_ROUNDS}. Treatment: Free Chat.\n"
            f"{self._last_round_summary(round_number)}\n\n"
            f"Send a short message to your group before everyone decides (max 2 sentences).\n"
            f'Reply in JSON: {{"message": "your message"}}'
        )
        try:
            return json.loads(self._call(prompt))["message"]
        except Exception:
            return "Let's all contribute enough to reach the threshold."

    def get_intention(self, round_number):
        prompt = (
            f"Round {round_number} of {NUM_ROUNDS}. Treatment: Intent Signaling.\n"
            f"{self._last_round_summary(round_number)}\n\n"
            f"State your intended contribution (non-binding, 0–10).\n"
            f'Reply in JSON: {{"intention": <integer>}}'
        )
        try:
            val = json.loads(self._call(prompt))["intention"]
            return max(0, min(10, int(val)))
        except Exception:
            return 5

    def get_contribution(self, round_number, communication_info=""):
        comm = f"\n{communication_info}" if communication_info else ""
        prompt = (
            f"Round {round_number} of {NUM_ROUNDS}.\n"
            f"{self._last_round_summary(round_number)}{comm}\n\n"
            f"Decide your contribution (integer 0–10).\n"
            f'Reply in JSON: {{"contribution": <integer>, "reasoning": "brief explanation"}}'
        )
        try:
            val = json.loads(self._call(prompt))["contribution"]
            return max(0, min(10, int(val)))
        except Exception:
            return random.randint(0, 10)

    def record(self, round_number, contribution, intention, message, group_total, threshold_met, payoff):
        self.total_payoff += payoff
        self.round_data.append({
            "round": round_number,
            "contribution": contribution,
            "group_total": group_total,
            "threshold_met": threshold_met,
            "payoff": payoff,
        })
        return {
            "player_id": self.player_id,
            "treatment": self.treatment,
            "round": round_number,
            "contribution": contribution,
            "intention": intention,
            "message": message,
            "group_total": group_total,
            "threshold_met": threshold_met,
            "payoff": payoff,
            "cumulative_payoff": self.total_payoff,
        }


# ── Simulation ─────────────────────────────────────────────────
def run_simulation():
    if MOCK_MODE:
        print("*** MOCK MODE — no API calls, no cost ***\n")
        client = None
    else:
        import anthropic
        client = anthropic.Anthropic()

    treatments = ["Control", "Binary", "Chat"]
    players = []
    pid = 1
    for t in treatments:
        for _ in range(PLAYERS_PER_GROUP):
            players.append(AIPlayer(pid, t, client))
            pid += 1

    all_data = []

    for round_num in range(1, NUM_ROUNDS + 1):
        print(f"\n{'='*55}")
        print(f"  ROUND {round_num} / {NUM_ROUNDS}")
        print(f"{'='*55}")

        groups = {t: [p for p in players if p.treatment == t] for t in treatments}

        for treatment, group in groups.items():
            print(f"\n  [{treatment}]")

            contributions = {}
            intentions   = {}
            messages     = {}

            # --- Communication phase ---
            if treatment == "Chat":
                for p in group:
                    msg = p.get_chat_message(round_num)
                    messages[p.player_id] = msg
                    print(f"    P{p.player_id} says: \"{msg}\"")

            elif treatment == "Binary":
                for p in group:
                    intention = p.get_intention(round_num)
                    intentions[p.player_id] = intention
                    print(f"    P{p.player_id} intends: {intention}")

            # --- Contribution phase ---
            for p in group:
                comm_info = ""
                if treatment == "Chat" and messages:
                    others = [f"P{i}: \"{m}\"" for i, m in messages.items() if i != p.player_id]
                    comm_info = "Group messages: " + " | ".join(others)
                elif treatment == "Binary" and intentions:
                    others = [f"P{i} intends {v}" for i, v in intentions.items() if i != p.player_id]
                    comm_info = "Others' stated intentions: " + ", ".join(others)

                contrib = p.get_contribution(round_num, comm_info)
                contributions[p.player_id] = contrib
                print(f"    P{p.player_id} contributes: {contrib}")

            # --- Payoffs ---
            total = sum(contributions.values())
            met   = total >= THRESHOLD

            for p in group:
                c = contributions[p.player_id]
                payoff = (ENDOWMENT - c + MULTIPLIER * total / PLAYERS_PER_GROUP) if met else (ENDOWMENT - c)
                row = p.record(
                    round_num, c,
                    intentions.get(p.player_id),
                    messages.get(p.player_id),
                    total, met, payoff
                )
                all_data.append(row)

            print(f"    → Group total: {total} | {'✓ THRESHOLD MET' if met else '✗ failed'}")

    # --- Save results ---
    df = pd.DataFrame(all_data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = f"/Users/terezaelbakyan/Desktop/ai_vs_ai_{timestamp}.xlsx"
    df.to_excel(output, index=False)

    print(f"\n\n{'='*55}")
    print("  FINAL SUMMARY")
    print(f"{'='*55}")
    for p in players:
        print(f"  P{p.player_id} ({p.treatment}): total payoff = {p.total_payoff:.1f}")

    # Treatment averages
    print("\n  Average payoff by treatment:")
    print(df.groupby("treatment")["payoff"].mean().round(2).to_string())
    print(f"\n  Threshold success rate by treatment:")
    print(df.groupby("treatment")["threshold_met"].mean().round(2).to_string())

    print(f"\n  Saved to: {output}")
    return df


if __name__ == "__main__":
    run_simulation()
