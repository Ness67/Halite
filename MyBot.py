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
import random
import time
import hlt
from function import utils

current_milli_time = lambda: int(round(time.time() * 1000))

# define
TIMEOUT_PROTECTION = 1600
# define

# GAME START
# Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.
game = hlt.Game("ColoNessV7")
# Then we print our start message to the logs
# logging.info("Starting my ColoNess bot!")
# Initializing Turn counter
nb_turn = 0

nb_ship_docked = 0


def select_target_3(ship_, game_map_):
    """
    :type ship_: the updated value of the ship with the target
    """

    # logging.info("Select target for ship :%s", ship_.id)
    shortest_distance = 3000
    to_destroy=0

    # We check if the ship already has a target
    if ship_.id in game.ship_planet_target:
        if game.ship_planet_target[ship_.id].free_dock() > game.ship_planet_target[ship_.id].targeted:
            ship_.target_planet = game.ship_planet_target[ship_.id]
            ship_.target_planet.targeted += 1
            return ship
    if ship_.id in game.ship_ship_target:
        if game.ship_ship_target[ship_.id] in enemy_ship:
            ship_.target_ship = game.ship_ship_target[ship_.id]
            return ship

    # For each planet in the game (only non-destroyed planets are included)
    for planet in game_map_.all_planets():
        # If the planet is owned
        if planet.is_owned():
            # logging.info("The planet n°%s is owned by : %s , I am : %s", planet.id, planet.owner.id,
            #              game_map_.get_me().id)
            if planet.owner.id != game_map_.get_me().id:
                to_destroy = planet
                # logging.info("Planet to attack : %s", to_destroy)
                continue
        if planet.targeted >= planet.free_dock():
            # skip this planet
            continue
        dist = ship_.calculate_distance_between(planet)
        if shortest_distance >= dist:
            shortest_distance = dist
            ship_.target_planet = planet
            game.ship_planet_target[ship_.id] = ship_.target_planet
            # ship_.target_planet = game_map.get_planet(1)
            # logging.info("Ship = %s Distance : %s Planete = %s", ship_.id, dist, planet.id)

    if not ship_.target_planet:
        # Attack an enemy planet
        if to_destroy:
            ship_.target_planet = to_destroy
            ship_.attack = "planet"
            # logging.info("Attack target planet: %s", ship_.target_planet)
            return ship
        # If there is no more Planet start to attack other ship
        else:
            ship.target_ship = random.choice(enemy_ship)[0]
            # logging.info("Attack target ship: %s", ship_.target_ship)
            game.ship_ship_target[ship_.id] = ship_.target_ship
            ship_.attack = "ship"
            return ship

    ship_.target_planet.targeted += 1
    return ship


# Start of the early game stratégie
while nb_ship_docked < 3:
    nb_turn += 1
    game_map = game.update_map()
    command_queue = []
    nb_ship_docked = 0

    # logging.info("Early Game Turn n° %d", nb_turn)

    for ship in game_map.get_me().all_ships():
        # If the ship is docked
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip this ship
            nb_ship_docked += 1
            continue

        ship = utils.select_target(ship, game_map)
        navigate_command = utils.decide_navigation(ship, game_map)
        # logging.info("Navigation Command = %s", navigate_command)
        command_queue.append(navigate_command)
    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END

# EARLY GAME END


while True:
    # TURN START
    # Update the map for the new turn and get the latest version
    game_map = game.update_map()
    start_time = current_milli_time()
    nb_turn += 1

    # logging.info("End Game Turn n° %d", nb_turn)

    # Here we define the set of commands to be sent to the Halite engine at the end of the turn
    command_queue = []

    # List all enemy ship
    enemy_ship = []
    for player in game_map.all_players():
        if player != game_map.get_me():
            enemy_ship.append(player.all_ships())


    # For every ship that I control
    for planet in game_map.all_planets():
        planet.targeted = 0
    for ship in game_map.get_me().all_ships():
        # logging.info("Start Working on ship : %s", ship)
        # If the ship is docked
        if current_milli_time()-start_time >= TIMEOUT_PROTECTION:
            # if time is running out send command
            logging.info("turn lasted : %s ms : Going to break", current_milli_time() - start_time)
            break
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip this ship
            # logging.info("Docked")
            continue
        start_time_select = current_milli_time()
        ship = select_target_3(ship, game_map)
        logging.info("Select target lasted : %s ms", current_milli_time() - start_time_select)
        if not ship.attack:
            navigate_command = utils.decide_navigation(ship, game_map, True)
            # logging.info("Navigation Command = %s", navigate_command)
        elif ship.attack == "planet":
            navigate_command=utils.attack(ship, game_map)
            # logging.info("Attack Command = %s", navigate_command)
        elif ship.attack == "ship":
            navigate_command = utils.attack_ship(ship, game_map)
            # logging.info("Attack Command = %s", navigate_command)

        if navigate_command:
            command_queue.append(navigate_command)

    logging.info("turn lasted : %s ms", current_milli_time()-start_time)
    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END


# GAME END
