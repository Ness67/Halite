"""
Welcome to your first Halite-II bot!

This bot's name is Settler. It's purpose is simple (don't expect it to win complex games :) ):
1. Initialize game
2. If a ship is not docked and there are unowned planets
2.a. Try to Dock in the planet if close enough
2.b If not, go towards the planet

Note: Please do not place print statements here as they are used to communicate with the Halite engine. If you need
to log anything use the logging module.
"""

# Importing the Halite Starter Kit so we can interface with the Halite engine
# Importing local library
# Importing the logging module so we can print out information
import logging
import hlt
from function import myclass

# GAME START
# Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.
bot = myclass.Bot(hlt.Game("ColoNessV12"))
# Then we print our start message to the logs
logging.info("Starting my ColoNess bot!")

nb_ship_docked = 0

while True:
    # TURN START
    # Update the map for the new turn and get the latest version
    bot.map_update()
    bot.start_time = bot.current_milli_time()
    bot.nb_turn += 1

    # Init of the things that will be use this turn
    bot.turn_init()

    if bot.nb_turn <= 60:
        # Start of the early game strategy
        bot.strategy_early_game()
    else:
        # Start of the late game strategy
        bot.strategy_end_game()

    logging.info("turn %d lasted : %s ms", bot.nb_turn, bot.current_milli_time()-bot.start_time)
    # Send our set of commands to the Halite engine for this turn
    bot.game.send_command_queue(bot.command_queue)
    # TURN END
# GAME END
