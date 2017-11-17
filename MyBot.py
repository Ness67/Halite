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
from function import utils

# define
timeout_protection = 100
# define

# GAME START
# Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.
game = hlt.Game("ColoNessV2")
# Then we print our start message to the logs
logging.info("Starting my ColoNess bot!")

nb_ship_docked = 0

def select_target_3(ship, game_map):
    """
    :type ship: the updated value of the ship with the target
    """
    shortest_distance = 3000
    # For each planet in the game (only non-destroyed planets are included)
    if ship.id in game.ship_planet_target:
        if not game.ship_planet_target[ship.id].is_full():
            ship.target = game.ship_planet_target[ship.id]
            ship.target.targeted += 1
            return ship
    for planet in game_map.all_planets():
        # If the planet is owned
        if planet.is_owned():
            if planet.owner.id != game_map.get_me().id:
                to_destroy = planet
                continue
        if planet.is_full():
            # skip this planet
            continue
        dist = ship.calculate_distance_between(planet)
        if shortest_distance >= dist:
            shortest_distance = dist
            ship.target = planet
            game.ship_planet_target[ship.id] = planet
            # ship.target = game_map.get_planet(1)
            logging.info("Ship = %s Distance : %s Planete = %s", ship.id, dist, planet.id)
    if not ship.target:
        ship.target = to_destroy
        ship.attack = 1
        logging.info("Attack target : %s",ship.target)

    ship.target.targeted += 1
    return ship


# Start of the early game stratégie
while nb_ship_docked < 3:
    game_map = game.update_map()
    command_queue = []
    nb_ship_docked = 0

    for ship in game_map.get_me().all_ships():
        # If the ship is docked
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip this ship
            nb_ship_docked += 1
            continue

        ship = utils.select_target(ship, game_map)
        navigate_command = utils.decide_navigation(ship, game_map)
        logging.info("Navigation Command = %s", navigate_command)
        command_queue.append(navigate_command)
    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END

# EARLY GAME END

while nb_ship_docked < 12:
    game_map = game.update_map()
    command_queue = []
    nb_ship_docked = 0

    for ship in game_map.get_me().all_ships():
        # If the ship is docked
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip this ship
            nb_ship_docked += 1
            continue

        ship = utils.select_target_bis(ship, game_map)
        navigate_command = utils.decide_navigation(ship, game_map, 180)
        logging.info("Navigation Command = %s", navigate_command)
        command_queue.append(navigate_command)
    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END

# Mid GAME END

while True:
    # TURN START
    # Update the map for the new turn and get the latest version
    game_map = game.update_map()

    # Here we define the set of commands to be sent to the Halite engine at the end of the turn
    command_queue = []

    # set the count of ship to 0
    ship_count = 0
    # For every ship that I control
    for ship in game_map.get_me().all_ships():
        # If the ship is docked
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip this ship
            continue
        if ship_count > timeout_protection:
            # if the number of ship to manage is to high stop to the timeout_protection limite
            break
        ship_count += 1
        ship = select_target_3(ship, game_map)
        if not ship.attak:
            navigate_command = utils.decide_navigation(ship, game_map, True)
        else:
            utils.attack(ship, game_map)
        logging.info("Navigation Command = %s", navigate_command, )
        command_queue.append(navigate_command)

    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END


# GAME END
