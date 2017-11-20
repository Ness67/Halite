import hlt
import logging
import time
import hlt
import random
from function import common

current_milli_time = lambda: int(round(time.time() * 1000))


def turn_init():
    common.enemy_ship = []
    common.enemy_planets = []
    common.my_planets = []
    # List all enemy ship
    for player in common.game_map.all_players():
        if player != common.game_map.get_me():
            for ship in player.all_ships():
                common.enemy_ship.append(ship)
    neutral_planets = []
    # list of planets
    for planet in common.game_map.all_planets():
        if planet.is_owned():
            if planet.owner == common.game_map.get_me():
                common.my_planets.append(planet)
            else:
                common.enemy_planets.append(planet)
        else:
            neutral_planets.append(planet)
    # Rest the target counter for the planet
    for planet in common.game_map.all_planets():
        planet.targeted = 0
    n = 0
    x = 0
    y = 0
    for planet in common.my_planets:
        n =+1
        x =+ planet.x
        y =+ planet.y
    common.barycenter.x=x/n
    common.barycenter.y=y/n


# Take a ship and find the closest planet
def select_target(ship, game_map):
    shortest_distance = 3000
    # For each planet in the game (only non-destroyed planets are included)
    for planet in game_map.all_planets():
        # If the planet is owned
        if planet.is_owned():
            # Skip this planet
            continue
        if planet.targeted != 0:
            # skip this planet
            continue
        dist = ship.calculate_distance_between(planet)
        if shortest_distance >= dist:
            shortest_distance = dist
            ship.target_planet = planet
            # ship.target_planet = game_map.get_planet(1)
            # logging.info("Ship = %s Distance : %s Planete = %s", ship.id, dist, planet.id)
    ship.target_planet.targeted += 1
    return ship


# def select_target_bis(ship, game_map):
#     shortest_distance = 30000
#     # For each planet in the game (only non-destroyed planets are included)
#     for planet in game_map.all_planets():
#         # If the planet is owned
#         if planet.is_owned():
#             if planet.owner.id != game_map.get_me().id:
#                 continue
#         if planet.targeted >= planet.num_docking_spots:
#             # skip this planet
#             continue
#         dist = ship.calculate_distance_between(planet)
#         if shortest_distance >= dist:
#             shortest_distance = dist
#             ship.target_planet = planet
#             # ship.target_planet = game_map.get_planet(1)
#             # logging.info("Ship = %s Distance : %s Planete = %s", ship.id, dist, planet.id)
#     if not ship.target_planet:
#         ship.target_planet = game_map.get_planet(1)
#     # logging.info("Ship = %s Choosen Planete = %s", ship.id, ship.target_planet.id)
#     ship.target_planet.targeted += 1
#     return ship


def decide_navigation(ship, game_map, avoid_ship=False, correction=10):
    start_time_measure = current_milli_time()
    # If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
    if ship.can_dock(ship.target_planet):
        # We add the command by appending it to the command_queue
        navigate_command = ship.dock(ship.target_planet)
    elif ship.near_planet(ship.target_planet):
        navigate_command = ship.navigate(
            ship.closest_point_to(ship.target_planet),
            game_map,
            max_corrections=200,
            angular_step=5,
            speed=int(hlt.constants.MAX_SPEED / 2),
            ignore_ships=False)
        logging.info("Precision Navigation lasted : %s ms", current_milli_time() - start_time_measure)
    else:
        # If we can't dock, we move towards the closest empty point near this ship.target_planet (by using closest_point_to)
        # with constant speed. Don't worry about pathfinding for now, as the command will do it for you.
        # We run this navigate command each turn until we arrive to get the latest move.
        # Here we move at half our maximum speed to better control the ships
        # In order to execute faster we also choose to ignore ship collision calculations during navigation.
        # This will mean that you have a higher probability of crashing into ships, but it also means you will
        # make move decisions much quicker. As your skill progresses and your moves turn more optimal you may
        # wish to turn that option off.
        navigate_command = ship.navigate(
            ship.closest_point_to(ship.target_planet),
            game_map,
            angular_step=5,
            max_corrections=correction,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=avoid_ship)
        # logging.info("Normal Navigation lasted : %s ms", current_milli_time() - start_time_measure)
        # If the move is possible, add it to the command_queue (if there are too many obstacles on the way
        # or we are trapped (or we reached our destination!), navigate_command will return null;
        # don't fret though, we can run the command again the next turn)
        # logging.info("Normal navigation command : %s",navigate_command)
        if not navigate_command:
            start_time_measure_special = current_milli_time()
            # logging.info("I went in None")
            navigate_command = ship.navigate(
                ship.closest_point_to(ship.target_planet),
                game_map,
                angular_step=20,
                max_corrections=18,
                speed=int(hlt.constants.MAX_SPEED / 2),
                ignore_ships=avoid_ship)
            logging.info("Advanced Navigation lasted : %s ms", current_milli_time() - start_time_measure_special)
            # if not navigate_command:
            #     # logging.info("I went in deep None")
            #     navigate_command = ship.navigate(
            #         ship.closest_point_to(ship.target_planet),
            #         game_map,
            #         max_corrections=360,
            #         speed=int(hlt.constants.MAX_SPEED / 2),
            #         ignore_ships=True)
    logging.info("Navigation lasted : %s ms", current_milli_time() - start_time_measure)
    if navigate_command:
        return navigate_command


def attack(ship, game_map, ):
    start_time_measure = current_milli_time()
    # If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
    if ship.can_suicide(ship.target_planet):
        # We add the command by appending it to the command_queue
        navigate_command = ship.navigate(
            ship.target_planet,
            game_map,
            speed=int(hlt.constants.MAX_SPEED),
            max_corrections=5,
            avoid_obstacles=False,
            ignore_ships=True,
            ignore_planets=True)
    else:
        # If we can't dock, we move towards the closest empty point near this ship.target_planet (by using closest_point_to)
        # with constant speed. Don't worry about pathfinding for now, as the command will do it for you.
        # We run this navigate command each turn until we arrive to get the latest move.
        # Here we move at half our maximum speed to better control the ships
        # In order to execute faster we also choose to ignore ship collision calculations during navigation.
        # This will mean that you have a higher probability of crashing into ships, but it also means you will
        # make move decisions much quicker. As your skill progresses and your moves turn more optimal you may
        # wish to turn that option off.
        navigate_command = ship.navigate(
            ship.closest_point_to(ship.target_planet),
            game_map,
            angular_step=5,
            max_corrections=10,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=False)
        logging.info("Normal Planet Attack lasted : %s ms", current_milli_time() - start_time_measure)
        # If the move is possible, add it to the command_queue (if there are too many obstacles on the way
        # or we are trapped (or we reached our destination!), navigate_command will return null;
        # don't fret though, we can run the command again the next turn)
    # logging.info("Normal navigation command : %s",navigate_command)
    if not navigate_command:
        start_time_measure_special = current_milli_time()
        # logging.info("I went in None")
        navigate_command = ship.navigate(
            ship.closest_point_to(ship.target_planet),
            game_map,
            max_corrections=18,
            angular_step=20,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=False)
        logging.info("Special Planet Attack lasted : %s ms", current_milli_time() - start_time_measure_special)
    # if not navigate_command:
    #     # logging.info("I went in deep None")
    #     navigate_command = ship.navigate(
    #         ship.closest_point_to(ship.target_planet),
    #         game_map,
    #         max_corrections=360,
    #         speed=int(hlt.constants.MAX_SPEED / 2),
    #         ignore_ships=True)
    logging.info("Planet Attack lasted : %s ms", current_milli_time() - start_time_measure)
    if navigate_command:
        return navigate_command


# We use this navigation tool to attack a other ship (suicide on him)
def attack_ship(ship, game_map, ):
    start_time_measure = current_milli_time()
    # If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
    # logging.info("The targeted ship is : %s", ship.target_ship)
    if ship.can_kill(ship.target_ship):
        # We add the command by appending it to the command_queue
        navigate_command = ship.navigate(
            ship.target_ship,
            game_map,
            max_corrections=10,
            speed=int(hlt.constants.MAX_SPEED),
            avoid_obstacles=False,
            ignore_ships=True,
            ignore_planets=True)
    else:
        # If we can't dock, we move towards the closest empty point near this ship.target_ship (by using closest_point_to)
        # with constant speed. Don't worry about pathfinding for now, as the command will do it for you.
        # We run this navigate command each turn until we arrive to get the latest move.
        # Here we move at half our maximum speed to better control the ships
        # In order to execute faster we also choose to ignore ship collision calculations during navigation.
        # This will mean that you have a higher probability of crashing into ships, but it also means you will
        # make move decisions much quicker. As your skill progresses and your moves turn more optimal you may
        # wish to turn that option off.
        navigate_command = ship.navigate(
            ship.closest_point_to(ship.target_ship),
            game_map,
            angular_step=5,
            max_corrections=10,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=False)
        logging.info("Normal Ship Attack lasted : %s ms", current_milli_time() - start_time_measure)
        # If the move is possible, add it to the command_queue (if there are too many obstacles on the way
        # or we are trapped (or we reached our destination!), navigate_command will return null;
        # don't fret though, we can run the command again the next turn)
    # logging.info("Normal navigation command : %s",navigate_command)
    if not navigate_command:
        start_time_measure_special = current_milli_time()
        # logging.info("I went in None")
        navigate_command = ship.navigate(
            ship.closest_point_to(ship.target_ship),
            game_map,
            max_corrections=18,
            angular_step=20,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=False)
        logging.info("Special Ship Attack lasted : %s ms", current_milli_time() - start_time_measure_special)
    # if not navigate_command:
    #     # logging.info("I went in deep None")
    #     navigate_command = ship.navigate(
    #         ship.closest_point_to(ship.target_ship),
    #         game_map,
    #         max_corrections=360,
    #         speed=int(hlt.constants.MAX_SPEED / 2),
    #         ignore_ships=True)
    logging.info("Ship Attack lasted : %s ms", current_milli_time() - start_time_measure)
    if navigate_command:
        return navigate_command


def select_target_3(ship, game_map):
    """
    :param ship: the ship that need a target
    :param game_map: the state of the map this turn
    :type ship: the updated value of the ship with the target
    """

    # logging.info("Select target for ship :%s", ship.id)
    shortest_distance = 3000
    destroy_planet = False

    # We check if the ship already has a target
    if ship.id in common.game.ship_planet_target:
        if common.game.ship_planet_target[ship.id].free_dock() > common.game.ship_planet_target[ship.id].targeted:
            ship.target_planet = common.game.ship_planet_target[ship.id]
            ship.target_planet.targeted += 1
            return ship
    if ship.id in common.game.ship_ship_target:
        if common.game.ship_ship_target[ship.id] in common.enemy_ship:
            ship.target_ship = common.game.ship_ship_target[ship.id]
            return ship

    # For each planet in the common.game (only non-destroyed planets are included)
    for planet in game_map.all_planets():
        # If the planet is owned
        if planet.is_owned():
            # logging.info("The planet n°%s is owned by : %s , I am : %s", planet.id, planet.owner.id,
            #              game_map.get_me().id)
            if planet.owner.id != game_map.get_me().id:
                # If it's a enemy planet continue
                destroy_planet=True
                continue
        if planet.targeted >= planet.free_dock():
            # if the planet is full or if there is too much ship going skip this planet
            continue
        dist = ship.calculate_distance_between(planet)
        if shortest_distance >= dist:
            shortest_distance = dist
            ship.target_planet = planet
            common.game.ship_planet_target[ship.id] = ship.target_planet
            # ship.target_planet = game_map.get_planet(1)
            # logging.info("Ship = %s Distance : %s Planete = %s", ship.id, dist, planet.id)

    if not ship.target_planet:
        # Attack an enemy planet
        if destroy_planet:
            ship.target_planet = choose_enemy_planet()
            ship.attack = "planet"
            # logging.info("Attack target planet: %s", ship.target_planet)
            return ship
        # If there is no more Planet start to attack other ship
        else:
            logging.info("The first ship is : %s", common.enemy_ship[0])
            logging.info("The table is : %s, the list is %d long", common.enemy_ship, len(common.enemy_ship))
            ship.target_ship = common.enemy_ship[random.randint(0,len(common.enemy_ship)-1)]
            # logging.info("Attack target ship: %s", ship.target_ship)
            common.game.ship_ship_target[ship.id] = ship.target_ship
            ship.attack = "ship"
            return ship

    ship.target_planet.targeted += 1
    return ship


def choose_enemy_planet():
    closest_distance = 3000
    if not common.enemy_planets:
        return
    for planet in common.enemy_planets:
        dist = planet.calculate_distance_between(common.barycenter)
        if dist < closest_distance:
            closest_distance = dist
            closest_enemy_planet = planet
    return closest_enemy_planet

