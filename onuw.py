import random
import os
import sys
import json
import time
from collections import defaultdict
from copy import copy
from slack import post_message, get_slack_ids

def wait():
    input()

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

roles_in_category = {
        "all_wolves": ["werewolf", "alphawolf", "dreamwolf", "mysticwolf", "lucidwolf"],
        "see_wolves": ["werewolf", "alphawolf", "mysticwolf", "minion"],
        "suspicious": ["werewolf", "alphawolf", "dreamwolf", "mysticwolf", "minion", "tanner", "lucidwolf",
                       "loverwolf", "lovervillager", "god"],
        "lovers": ["loverwolf", "lovervillager"],
}

valid_roles = {"villager", "minion", "werewolf", "doppelganger", "troublemaker",
               "robber", "bandit", "seer", "mason", "hunter", "bodyguard", "tanner",
               "sentinel", "drunk", "fool", "villageidiot", "alphawolf", "mysticwolf", "dreamwolf",
               "apprenticeseer", "insomniac", "revealer", "witch", "PI", "curator",
               "lucidwolf", "god", "madseer", "loverwolf", "lovervillager"}

marks = ["mark of villager", "mark of werewolf", "mark of tanner",
         "mark of nothing", "mark of shame", "mark of muting"]

"""
All roles are randomized. This has a few material changes:

    * Seer looks in middle 50% of the time
    * Witch takes suspicious roles for herself 50% of the time
    * PI always looks at first role, looks at second role 50% of the time
    * Village idiot doesn't rotate 20% of the time
    * Troublemaker, robber, and witch always act
    * No one can plan around village idiot affecting nearby locations
    * Village idiot can't choose direction based on shield
    * Curator marks a revealed player with the same probability rate as other players
    * Doppelganger troublemaker switches troublemaker at same probabiity
    * Doppelganger revealer reveals the revealer at same proability
    * Doppelganger curator marks the curator at same probability
    * Doppelganger witch never switches the witch
    * Doppelganger robber never robs the robber
    * Doppelganger PI never looks at the PI

TODO
    * timer
    * (low) handle cases where there are no targets
"""

def timer(f, *events):
    current = 0
    for t, event in events:
        time.sleep(t-current)
        current=t
        f(event)

class Role():
    def __init__(self, name):
        self.name = name
        assert name in valid_roles, name
        self.copied = None

    def __str__(self):
        return self.name

    def full_str(self):
        parts = [self.name]
        if self.copied is not None:
            parts.append(f"({self.copied.full_str()})")
        return " ".join(parts)

def rotate(xs, locations):
    values = [xs[i] for i in locations]
    for loc, value in zip(locations, [values[-1]] + values[:-1]):
        xs[loc] = value

class NoTarget(Exception):
    pass

#pick something from none of the excludes if possible
#otherwise, start trying to pick from the first of the excludes
#never pick from the last of the excludes, raise NoTarget if there are no options
def random_choice(N, *excludes):
    all_excludes = [x for exclude in excludes for x in exclude]
    options = [i for i in list(range(N)) if i not in all_excludes]
    if options:
        return random.choice(options)
    for exclude in excludes[:-1]:
        if exclude:
            return random.choice(exclude)
    raise NoTarget()

def reveal(singular, plural, people):
    if len(people) == 0:
        return f"there are no {plural}"
    elif len(people) == 1:
        return f"the only {singular} is {people[0]}"
    else:
        return f"the {plural} are {', '.join(people[1:])} and {people[0]}"


def game(players, roles, lonewolf=True, use_slack=False):
    N = len(players)
    assert len(roles) == N + 3
    roles = [Role(role) for role in roles]
    random.shuffle(roles)
    initial_roles = copy(roles)
    slack_ids = {} if not use_slack else get_slack_ids(players)

    log = []
    messages = [[] for _ in range(N)] #messages that will be seen by player i
    players_by_role = defaultdict(list) #which players believe they are role X
    initial_players_by_role = defaultdict(list) #which players initially believe they are role X
    for i in range(N):
        players_by_role[roles[i].name].append(i)
        initial_players_by_role[roles[i].name].append(i)

    #(role, index) pairs to invoke after everything else is done (from doppelganger)
    wrapup = []

    shielded = []
    revealed = []
    marked = {}

    def players_in_category(cat):
        return [player for role in roles_in_category[cat] for player in players_by_role[role]]

    def message_and_log(i, during, after=None):
        messages[i].append(f"{players[i]} {during}")
        log.append(f"{players[i]} {after or during}")

    def broadcast_and_log(during, after=None):
        for i in range(N):
            messages[i].append(during)
        log.append(after or during)

    clear()

    def try_for_nonwolf(i, doppelganged):
        if not doppelganged:
            return ([j for j in range(N) if j not in players_in_category("all_wolves") and j != i and j not in shielded]
                 or [j for j in range(N) if i != j and j not in shielded])
        else:
            return [j for j in range(N) if i != j and j not in shielded+doppelganged]

    def do_role(i, role, doppelganged=[]):
        #print(f"{players[i]} doing {role}")
        #print(f"shielded = {shielded}")
        #print(f"revealed   = {revealed}")
        #print(f"roles = {roles}")
        if role.name in ("werewolf", "dreamwolf", "minion", "villager", "hunter", "bodyguard"):
            pass
        elif role.name == "sentinel":
            try:
                j = random_choice(N, [i] + shielded)
                shielded.append(j)
                broadcast_and_log(f"{players[j]} was marked with a shield",
                                  f"{players[i]} marked {players[j]} with a shield")
            except NoTarget:
                broadcast_and_log(i, "had no one to mark")
        elif role.name == "witch":
            j = random.randint(1, 3)
            role = roles[N+j-1]
            message_and_log(i, f"looked at middle card {j} and saw {role}")
            if role.name in roles_in_category["suspicious"] and random.random() < 0.5 and i not in shielded:
                target = i
            else:
                target = random_choice(N, [i] + doppelganged, shielded)
            rotate(roles, [target, N+j-1])
            message_and_log(i, f"gave {players[target]} role {role}")
        elif role.name == "PI":
            exclude = [i] + shielded + doppelganged
            for _ in range(2):
                try:
                    j = random_choice(N, exclude)
                    exclude.append(j)
                    message_and_log(i, f"looked at {players[j]} and saw {roles[j]}")
                    if roles[j].name in roles_in_category["suspicious"]:
                        message_and_log(i, f"became {roles[j]}")
                        role.copied = roles[j]
                        break
                    if random.random() < 0.5:
                        break
                except NoTarget:
                    message_and_log(i, "had no one to look at")
        elif role.name == "curator":
            if doppelganged:
                wrapup.append((i, role))
            else:
                try:
                    j = random_choice(N, [i]+shielded+list(marked.keys()))
                    mark = random.choice(marks)
                    marked[j] = mark
                    messages[i].append(f"{players[i]} gave {players[j]} a mark")
                    messages[j].append(f"{players[j]} received {mark}")
                    for k in range(N):
                        if k not in (i, j):
                            messages[k].append(f"{players[j]} received a mark")
                    log.append(f"{players[i]} gave {players[j]} {mark}")
                except NoTarget:
                    message_and_log(i, "had no one to mark")
            pass
        elif role.name in ("drunk", "fool"):
            j = random.randint(1, 3)
            if role.name == "fool":
                for k in [1, 2, 3]:
                    if k != j:
                        message_and_log(i, f"looked at middle card {k} and saw {roles[N+k-1]}")
            if i in shielded:
                message_and_log(i, "did nothing, because they were shielded")
            else:
                rotate(roles, (i, N-1+j))
                message_and_log(i, f"took middle card {j}",
                                   f"took middle card {j} which was {roles[i]}")
        elif role.name == "mysticwolf":
            targets = try_for_nonwolf(i, doppelganged)
            if not targets:
                message_and_log(i, "looked at no one")
            else:
                j = random.choice(targets)
                message_and_log(i, f"looked at {players[j]} and saw {roles[j]}")
        elif role.name == "villageidiot":
            to_rotate = [j for j in range(N) if j != i and j not in shielded]
            if random.random() < 0.5:
                to_rotate.reverse()
            if random.random() < 0.2 or len(to_rotate) < 2:
                message_and_log(i, "didn't rotate anyone")
            else:
                rotate_str = ' -> '.join([players[i] for i in to_rotate + [to_rotate[0]]])
                rotate(roles, to_rotate)
                message_and_log(i, f"rotated {rotate_str}")
        elif role.name == "revealer":
            if doppelganged:
                wrapup.append((i, role))
                return
            else:
                try:
                    j = random_choice(N, [i] + shielded + revealed)
                    if roles[j].name in roles_in_category['suspicious']:
                        message_and_log(i, f"looked at {players[j]} and saw {roles[j]}, but did not reveal")
                    else:
                        revealed.append(j)
                        broadcast_and_log(f"{players[j]} was revealed to be {roles[j]}",
                                          f"{players[i]} revealed {players[j]} to be {roles[j]}")
                except NoTarget:
                    message_and_log(i, "had no one to reveal")
        elif role.name == "doppelganger":
            try:
                j = random_choice(N, [i] + shielded + doppelganged)
                role.copied = Role(roles[j].name)
                message_and_log(i, f"doppelganged {players[j]}, who was {roles[j]}")
                players_by_role[role.copied.name].append(i)
                do_role(i, role.copied, doppelganged + [j])
            except NoTarget:
                message_and_log(i, f"had no one to copy")
        elif role.name == "seer":
            looked = False
            if random.random() < 0.5:
                try:
                    j = random_choice(N, [i] + doppelganged + shielded)
                    message_and_log(i, f"looked at {players[j]} and saw {roles[j]}")
                    looked = True
                except NoTarget:
                    looked = False
            if not looked:
                j = random.randint(1, 3)
                for k in [1, 2, 3]:
                    if k != j:
                        message_and_log(i, f"looked at middle card {k} and saw {roles[N+k-1]}")
        elif role.name == "madseer":
            try:
                j = random_choice(N, [i] + doppelganged + shielded)
                k = random_choice(N, [j], [i] + doppelganged + shielded)
                rolej = roles[j]
                rolek = None
                #if you see a madseer, should see double madseer, otherwise should see no madseer
                while rolek is None or ((rolej.name == "madseer") != (rolek.name == "madseer")):
                    rolek = roles[random_choice(N+3)]
                true_message = f"looked at {players[j]} and saw {rolej}"
                true_messages = (true_message, true_message)
                false_message = f"looked at {players[k]} and saw {rolek}"
                false_messages = (false_message, f"looked at {players[k]} and hallucinated {rolek}")
                for during, after in random.choice([[true_messages, false_messages],
                                                    [false_messages, true_messages]]):
                    message_and_log(i, during, after)
            except NoTarget:
                message_and_log(i, f"had no one to look at")
        elif role.name == "apprenticeseer":
            j = random.randint(1, 3)
            message_and_log(i, f"looked at middle card {j} and saw {roles[N+j-1]}")
        elif role.name == "lucidwolf":
            j = random.randint(1, 3)
            message_and_log(i, f"looked at middle card {j} and saw {roles[N+j-1]}")
        elif role.name in ("robber", "bandit"):
            if i in shielded:
                message_and_log(i, f"did nothing, because they were shielded")
            else:
                try:
                    j = random_choice(N, doppelganged, [i] + shielded)
                    if role.name == "robber":
                        rotate(roles, (i, j))
                        message_and_log(i, f"stole {roles[i]} from {players[j]}")
                    elif role.name == "bandit":
                        k = random.randint(1, 3)
                        rotate(roles, (i, j, N+k-1))
                        msg = f"stole {roles[i]} from {players[j]} and gave them middle card {k}"
                        message_and_log(i, msg, f"{msg} which was {roles[N+k-1]}")
                except NoTarget:
                    message_and_log(i, f"couldn't rob anyone")
        elif role.name == "alphawolf":
            targets = try_for_nonwolf(i, doppelganged)
            if not targets:
                message_and_log(i, "turned no one into a wolf")
            else:
                j = random.choice(targets)
                message_and_log(i, f"turned {players[j]} into a wolf")
                roles[j], do_role.current_center_card = do_role.current_center_card, roles[j]
        elif role.name == "insomniac":
            if doppelganged:
                wrapup.append((i, "insomniac"))
            else:
                if i in shielded:
                    messages[i].append(f"{players[i]} did not see their role, because they were shielded")
                else:
                    messages[i].append(f"{players[i]} ended the night as {roles[i]}")
        elif role.name == "mason":
            messages[i].append(reveal("mason", "masons", [players[i] for i in players_by_role['mason']]))
        elif role.name in ("loverwolf", "lovervillager"):
            messages[i].append(reveal("lover", "lovers", [players[i] for i in players_in_category('lovers')]))
        elif role.name == "god":
            for m in log:
                messages[i].append(f"[God] {m}")
        elif role.name == "troublemaker":
            try:
                j = random_choice(N, [i] + shielded)
                k = random_choice(N, [i, j] + shielded)
                rotate(roles, (j, k))
                message_and_log(i, f"switched {players[j]} and {players[k]}")
            except NoTarget:
                message_and_log(i, "couldn't switch anybody")
        else:
            raise ValueError(role.name)
    do_role.current_center_card = Role("werewolf")

    wake_order = []
    def wake_role(role_name):
        for i in initial_players_by_role[role_name]:
            do_role(i, initial_roles[i])
        if role_name in [role.name for role in roles]:
            wake_order.append(role_name)

    def do_werewolves():
        wolves = players_in_category('all_wolves')
        message = reveal("wolf", "wolves", [players[i] for i in wolves])
        for player in players_in_category("see_wolves"):
            messages[player].append(message)
        if len(wolves) == 1 and lonewolf:
            wolf = wolves[0]
            if wolf not in players_by_role['dreamwolf'] + players_by_role['lucidwolf']:
                j = random.randint(1, 3)
                message_and_log(wolf, f"looked at middle card {j} and saw {roles[N-1+j]}")

    def display(text):
        print(text)
        if slack_ids:
            for player in slack_ids:
                post_message(slack_ids[player], text)
    
    display(f"--------------------\nSeating order: {', '.join(players)}")

    for i in range(N):
        message_and_log(i, f"began the night as {roles[i]}")

    wake_role("villager")
    wake_role("sentinel")
    wake_role("doppelganger")
    do_werewolves()
    wake_role("werewolf")
    wake_role("dreamwolf")
    wake_role("alphawolf")
    wake_role("mysticwolf")
    wake_role("minion")
    wake_role("mason")
    wake_role("loverwolf")
    wake_role("lovervillager")
    wake_role("seer")
    wake_role("madseer")
    wake_role("apprenticeseer")
    wake_role("lucidwolf")
    wake_role("PI")
    wake_role("robber")
    wake_role("witch")
    wake_role("bandit")
    wake_role("troublemaker")
    wake_role("villageidiot")
    wake_role("fool")
    wake_role("drunk")
    wake_role("insomniac")
    wake_role("revealer")
    wake_role("curator")
    wake_role("god")

    for i, role in wrapup:
        do_role(i, role)

    def make_wake_order_str(role):
        num_roles = len([x for x in roles if x.name == role])
        return role if num_roles == 1 else f"{role} (x{num_roles})"

    for i, player in enumerate(players):
        if player in slack_ids:
            post_message([slack_ids[player]], '\n'.join(messages[i]))

    clear()
    for i, player in enumerate(players):
        if player not in slack_ids:
            print(f"pass the computer to {player}")
            wait()
            clear()
            for message in messages[i]:
                print(message)
            wait()
            clear()

    display("Wake order:\n\n" +
            "\n".join([f"{i+1}. {make_wake_order_str(x)}" for i, x in enumerate(wake_order)]))
    print()
    try:
        timer(display,
              (0, "One minute to think..."),
              (60, "Five minutes to discus..."),
              (60 + 5 * 60 - 30, "Thirty seconds left..."),
              (60 + 5 * 60, "Vote!"))
    except KeyboardInterrupt:
        pass
    else:
        print("Press any key to see final roles")
        wait()
    finally:
        def final_role_str(i):
            result = f"{players[i]}: {roles[i].full_str()}"
            if i in marked:
                result += f" ({marked[i]})"
            return result
        log.append("\nFinal roles:")
        log.extend([final_role_str(i) for i in range(N)])
        display('\n'.join(log))

if __name__ == '__main__':
    players = sys.argv[1]
    roles = sys.argv[2]
    game(players.split(","), roles.split(","), use_slack='slack' in sys.argv)
