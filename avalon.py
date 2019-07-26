import random
import os
import sys

good_roles = ["merlin", "percival", "good"]
evil_roles = ["assassin", "snape", "evil", "morgana", "mordred"]

# role : [(description, roles to be revealed)]
reveals = {
    "merlin": [("evil players you see", [x for x in evil_roles if x != "mordred"])],
    "percival": [("merlin and morgana", ["morgana", "merlin"])],
    "good": [],
}
for x in evil_roles: reveals[x] = [("evil players", evil_roles)]

# number of players : (number good, number evil)
composition = {
    4: (3, 1),
    5: (3, 2),
    6: (4, 2),
    7: (4, 3),
    8: (5, 3),
    9: (6, 3),
    10: (6, 4)
}

# number of players : sizes of quests
quests = {
    4: (3, 3, 3),
    5: (3, 3, 3),
    6: (3, 4, 4),
    7: (3, 3, 4),
}
quests[8] = quests[9] = quests[10] = (4, 4, 5)

def wait():
    input()

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def make_role_list(n, used_roles):
    if "merlin" in used_roles or "snape" in used_roles:
        used_roles.append("assassin")
    good, evil = composition[n]
    good -= sum(x in good_roles for x in used_roles)
    evil -= sum(x in evil_roles for x in used_roles)
    assert good >= 0, "too many good roles"
    assert evil >= 0, "too many evil roles"
    return used_roles + ["good"] * good + ["evil"] * evil

def main(player_list, used_roles):
    role_list = make_role_list(len(player_list), used_roles)
    random.shuffle(role_list)
    roles = {player:role for player, role in zip(player_list, role_list)}
    for player, role in zip(player_list, role_list):
        clear()
        print("Hand computer to {}".format(player))
        wait()
        clear()
        print("{}, you are {}".format(player, role))
        for descriptor, to_reveal in reveals[role]:
            players_to_reveal = [p for p in player_list if roles[p] in to_reveal]
            print("{} are {}".format(descriptor, ", ".join(players_to_reveal)))
        wait()
    clear()
    random.shuffle(player_list)
    print("Three largest quests: {} / {} / {}".format(*quests[len(player_list)]))
    print("Random permutation of players\n{}".format("\n".join(player_list)))

if __name__ == '__main__':
    player_list = sys.argv[1].split(",")
    used_roles = sys.argv[2].split(",")
    assert all(x in good_roles or x in evil_roles for x in used_roles)
    main(player_list, used_roles)
