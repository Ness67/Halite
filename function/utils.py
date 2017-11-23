import hlt
import logging
import time
import hlt
import random
from function import common

current_milli_time = lambda: int(round(time.time() * 1000))


def turn_init():

    # Initializing the turn variable
    common.enemy_ship = []
    common.enemy_planets = []
    common.my_planets = []
    # Here we define the set of commands to be sent to the Halite engine at the end of the turn
    common.command_queue = []

    # List all enemy ship
    for player in common.game_map.all_players():
        if player != common.game_map.get_me():
            common.enemy_ship.extend(player.all_ships())
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
    if common.game_map.get_me().all_ships():
        n = 0
        x = 0
        y = 0
        for ship in common.game_map.get_me().all_ships():
            n = +1
            x = +ship.x
            y = +ship.y
        common.barycenter.x = x/n
        common.barycenter.y = y/n


# # Take a ship and find the closest planet
# def select_target(ship, game_map):
#     shortest_distance = 3000
#     # For each planet in the game (only non-destroyed planets are included)
#     for planet in game_map.all_planets():
#         # If the planet is owned
#         if planet.is_owned():
#             # Skip this planet
#             continue
#         if planet.targeted != 0:
#             # skip this planet
#             continue
#         dist = ship.calculate_distance_between(planet)
#         if shortest_distance >= dist:
#             shortest_distance = dist
#             ship.target = planet
#             ship.action = "colonise"
#             # ship.target_planet = game_map.get_planet(1)
#             # logging.info("Ship = %s Distance : %s Planete = %s", ship.id, dist, planet.id)
#     if ship.target:
#         ship.target.targeted += 1
#     else:
#         ship.target = random.choice(common.my_planets)
#         ship.target.targeted += 1
#     return ship


def select_target_3(ship, game_map, max_ship_planet=100, distance_to_look=3000):
    """
    :param max_ship_planet: the max number of ship / planet
    :param distance_to_look:  the max distance to look for a planet to colonise
    :param ship: the ship that need a target
    :param game_map: the state of the map this turn
    :type ship: the updated value of the ship with the target
    :return ship: the amended ship with a target and an action
    """

    # logging.info("Select target for ship :%s", ship.id)
    destroy_planet = False
    logging.info("Start targeting for ship %d",ship.id)
    # We check if the ship already has a target
    if ship.id in common.game.ship_planet_target:
        # logging.info("ship %d had already a planet target : %d", ship.id, common.game.ship_planet_target[ship.id].id)
        if common.game.ship_planet_target[ship.id].free_dock() > common.game.ship_planet_target[ship.id].targeted:
            ship.target = common.game.ship_planet_target[ship.id]
            ship.target.targeted += 1
            ship.action = "colonise"
            # logging.info("Keep this target")
            return ship
    if ship.id in common.game.ship_ship_target:
        logging.info("ship %d had already a ship target : %d", ship.id, common.game.ship_ship_target[ship.id].id)
        if common.game.ship_ship_target[ship.id] in common.enemy_ship:
            ship.target = common.game.ship_ship_target[ship.id]
            ship.action = "ship"
            # logging.info("Keep this target")
            return ship

    # For each planet in the common.game (only non-destroyed planets are included)
    for planet in game_map.all_planets():
        # If the planet is owned
        if planet.is_owned():
            # logging.info("The planet n°%s is owned by : %s , I am : %s", planet.id, planet.owner.id,
            #              game_map.get_me().id)
            if planet.owner.id != game_map.get_me().id:
                # If it's a enemy planet continue
                destroy_planet = True
                continue
        if planet.targeted >= planet.free_dock() or planet.targeted >= max_ship_planet:
            # if the planet is full or if there is too much ship going skip this planet
            continue
        dist = ship.calculate_distance_between(planet)
        if distance_to_look >= dist:
            distance_to_look = dist
            ship.target = planet
            common.game.ship_planet_target[ship.id] = ship.target
            ship.action = "colonise"
            # ship.target = game_map.get_planet(1)
            # logging.info("Ship = %s Distance : %s Planete = %s", ship.id, dist, planet.id)

    if ship.action != "colonise":
        # Attack an enemy planet
        if destroy_planet:
            ship.target = choose_enemy_planet()
            ship.action = "planet"
            # logging.info("Attack target planet: %s", ship.target)
            return ship
        # If there is no more Planet start to attack other ship
        else:
            ship.target = random.choice(common.enemy_ship)
            logging.info("The targeted ship is : %s", ship.target)
            common.game.ship_ship_target[ship.id] = ship.target
            ship.action = "ship"
            return ship

    ship.target.targeted += 1
    return ship


def normal_navigation(ship, avoid_ship, correction=10, angular=5):
    # If we can't dock, we move towards the closest empty point near this ship.target (by using closest_point_to)
    # with constant speed. Don't worry about pathfinding for now, as the command will do it for you.
    # We run this navigate command each turn until we arrive to get the latest move.
    # Here we move at half our maximum speed to better control the ships
    # In order to execute faster we also choose to ignore ship collision calculations during navigation.
    # This will mean that you have a higher probability of crashing into ships, but it also means you will
    # make move decisions much quicker. As your skill progresses and your moves turn more optimal you may
    # wish to turn that option off.
    navigate_command = ship.navigate(
        ship.closest_point_to(ship.target),
        common.game_map,
        angular_step=angular,
        max_corrections=correction,
        speed=int(hlt.constants.MAX_SPEED),
        ignore_ships=avoid_ship)
    logging.info("Finished Normal navigation for ship %d with %s order", ship.id, navigate_command)
    # logging.info("Normal Navigation lasted : %s ms", current_milli_time() - start_time_measure)
    # If the move is possible, add it to the command_queue (if there are too many obstacles on the way
    # or we are trapped (or we reached our destination!), navigate_command will return null;
    # don't fret though, we can run the command again the next turn)
    # logging.info("Normal navigation command : %s",navigate_command)
    if not navigate_command:
        start_time_measure_special = current_milli_time()
        # logging.info("I went in None")
        navigate_command = ship.navigate(
            ship.closest_point_to(ship.target),
            common.game_map,
            angular_step=20,
            max_corrections=18,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=avoid_ship)
        logging.info("Finished Advanced navigation for ship %d with %s order", ship.id, navigate_command)
        # logging.info("Advanced Navigation lasted : %s ms", current_milli_time() - start_time_measure_special)
    if navigate_command:
        return navigate_command


def decide_navigation(ship, avoid_ship=False, correction=10, angular=5):
    logging.info("Enter Navigation for ship : %d, ship action is : %s", ship.id, ship.action)
    navigate_command = 0
    start_time_measure = current_milli_time()
    # If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
    if ship.action == "colonise":
        if ship.can_dock(ship.target):
            # We add the command by appending it to the command_queue
            navigate_command = ship.dock(ship.target)
        elif ship.near_planet(ship.target):
            navigate_command = ship.navigate(
                ship.closest_point_to(ship.target),
                common.game_map,
                max_corrections=180,
                angular_step=2,
                speed=int(hlt.constants.MAX_SPEED / 2),
                ignore_ships=False)
            logging.info("Finished Precision navigation for ship %d with %s order", ship.id, navigate_command)
            logging.info("Precision Navigation lasted : %s ms", current_milli_time() - start_time_measure)
        else:
            navigate_command = normal_navigation(ship, avoid_ship, correction, angular)
    
    # If the flag "planet" is raise we attack the planet
    elif ship.action == "planet":
        if ship.can_suicide(ship.target):
            # We add the command by appending it to the command_queue
            navigate_command = ship.navigate(
                ship.target,
                common.game_map,
                speed=int(hlt.constants.MAX_SPEED),
                max_corrections=5,
                avoid_obstacles=False,
                ignore_ships=True,
                ignore_planets=True)
            logging.info("Finished Attack planet procedure for ship %d with %s order", ship.id, navigate_command)
        else:
            navigate_command = normal_navigation(ship, avoid_ship, correction, angular)
    
    # If the flag ship is raise we attack a ship
    elif ship.action == "ship":
        if ship.can_kill(ship.target):
            # We add the command by appending it to the command_queue
            navigate_command = ship.navigate(
                ship.target,
                common.game_map,
                max_corrections=10,
                speed=int(hlt.constants.MAX_SPEED),
                avoid_obstacles=False,
                ignore_ships=True,
                ignore_planets=True)
            logging.info("Finished Attack ship procedure for ship %d with %s order", ship.id, navigate_command)
        else:
            navigate_command = normal_navigation(ship, avoid_ship, correction, angular)

    if navigate_command:
        return navigate_command


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


def strategy_end_game():
    # For every ship that I control
    for ship in common.game_map.get_me().all_ships():
        # logging.info("Start Working on ship : %s", ship)
        if common.current_milli_time()-common.start_time >= common.TIMEOUT_PROTECTION:
            # if time is running out send command
            logging.info("turn %d lasted : %s ms : Going to break", common.nb_turn, common.current_milli_time() - common.start_time)
            break
        # If the ship is dockedgit
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip this ship
            # logging.info("Ship %d Docked", ship.id)
            continue
        ship = select_target_3(ship, common.game_map)
        # logging.info("Select target lasted : %s ms", common.current_milli_time() - start_time_select)
        navigate_command = decide_navigation(ship)

        logging.info("Ship %d has %s move Command", ship.id, navigate_command)
        if navigate_command:
            common.command_queue.append(navigate_command)


def strategy_early_game():
    # For every ship that I control
    for ship in common.game_map.get_me().all_ships():
        # logging.info("Start Working on ship : %s", ship)
        if common.current_milli_time()-common.start_time >= common.TIMEOUT_PROTECTION:
            # if time is running out send command
            logging.info("turn %d lasted : %s ms : Going to break", common.nb_turn, common.current_milli_time() - common.start_time)
            break
        # If the ship is dockedgit
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip this ship
            # logging.info("Ship %d Docked", ship.id)
            continue
        ship = select_target_3(ship, common.game_map,max_ship_planet=2)
        # logging.info("Select target lasted : %s ms", common.current_milli_time() - start_time_select)
        navigate_command = decide_navigation(ship)

        logging.info("Ship %d has %s move Command", ship.id, navigate_command)
        if navigate_command:
            common.command_queue.append(navigate_command)