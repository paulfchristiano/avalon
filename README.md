Avalon Usage: `python avalon.py player1,player2,...,playerN role1,role2,...,roleM`

Example: `python avalon.py alice,bob,charlie,denise,eve,frank,george merlin,percival,morgana`

Player names can be whatever.

Roles can be `merlin`, `mordred`, `percival`, `morgana`, `snape`.
One evil player will be given the role `assassin` if snape or merlin is in the game.

The code is hopefully self-explanatory.

ONUW Usage: `python onuw.py player1,player2,...,playerN role1,role2,...,role(N+3) [slack]`

Example: `python onuw.py alice,bob,charlie werewolf,alphawolf,PI,seer,doppelganger,villageidiot`

List players in order going around the table (or village idiot will rotate strangely).

This randomizes all of the night actions.
I don't think this changes the game much, but YMMV.
The substantive assumptions are spelled out in onuw.py
(for example, village idiot does nothing 20% of the time,
witch gives themself a suspicious role 50% of the time).
Feel free to change those assumptions.

Include `slack` as the final argument if you want to broadcast night observations via slack.
Otherwise you will be asked to pass around the computer.
(To set up a slackbot in your workspace, you need to follow the instructions in `slack.py`.) 
