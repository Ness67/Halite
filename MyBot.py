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
from function import common
from function import utils


# GAME START
# Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.
common.game = hlt.Game("ColoNessV9")
# Then we print our start message to the logs
logging.info("Starting my ColoNess bot!")

nb_ship_docked = 0

# Start of the early game strategy
while 0:
    common.nb_turn += 1
    common.game_map = common.game.update_map()
    command_queue = []
    utils.turn_init()
    nb_ship_docked = 0

    # logging.info("Early Game Turn n° %d", nb_turn)

    for ship in common.game_map.get_me().all_ships():
        # If the ship is docked
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip this ship
            nb_ship_docked += 1
            continue

        ship = utils.select_target(ship, common.game_map)
        navigate_command = utils.decide_navigation(ship, common.game_map)
        logging.info("Move Command = %s", navigate_command)
        # logging.info("Navigation Command = %s", navigate_command)
        command_queue.append(navigate_command)
    # Send our set of commands to the Halite engine for this turn
    common.game.send_command_queue(command_queue)
    # TURN END

# EARLY GAME END


while True:
    # TURN START
    # Update the map for the new turn and get the latest version
    common.game_map = common.game.update_map()
    common.start_time = common.current_milli_time()
    common.nb_turn += 1

    # Init of the things that will be use this turn
    utils.turn_init()

    if common.nb_turn <= 30:
        utils.strategy_early_game()
    else:
        utils.strategy_end_game()

    logging.info("turn %d lasted : %s ms", common.nb_turn, common.current_milli_time()-common.start_time)
    # Send our set of commands to the Halite engine for this turn
    common.game.send_command_queue(common.command_queue)
    # TURN END


# GAME END
