import time

#definition of the method to measure time
current_milli_time = lambda: int(round(time.time() * 1000))
# The time limit set to avoid timeout
TIMEOUT_PROTECTION = 1700
# The map of the current game
game_map = 0
# The current turn number
nb_turn = 0
# State of the game
game = 0
# The list of some game's element that we use for processing
enemy_ship = []
enemy_planets = []
my_planets = []
