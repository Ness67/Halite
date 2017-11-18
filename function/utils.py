import hlt
import logging


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

def select_target_bis(ship, game_map):
    shortest_distance = 30000
    # For each planet in the game (only non-destroyed planets are included)
    for planet in game_map.all_planets():
        # If the planet is owned
        if planet.is_owned():
            if planet.owner.id != game_map.get_me().id:
                continue
        if planet.targeted >= planet.num_docking_spots:
            # skip this planet
            continue
        dist = ship.calculate_distance_between(planet)
        if shortest_distance >= dist:
            shortest_distance = dist
            ship.target_planet = planet
            # ship.target_planet = game_map.get_planet(1)
            # logging.info("Ship = %s Distance : %s Planete = %s", ship.id, dist, planet.id)
    if not ship.target_planet:
        ship.target_planet = game_map.get_planet(1)
    # logging.info("Ship = %s Choosen Planete = %s", ship.id, ship.target_planet.id)
    ship.target_planet.targeted += 1
    return ship


def decide_navigation(ship, game_map, avoid_ship=False, correction=90):
    # If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
    if ship.can_dock(ship.target_planet):
        # We add the command by appending it to the command_queue
        navigate_command = ship.dock(ship.target_planet)
    elif ship.near_planet(ship.target_planet):
        navigate_command = ship.navigate(
            ship.closest_point_to(ship.target_planet),
            game_map,
            max_corrections=360,
            speed=int(hlt.constants.MAX_SPEED/3),
            ignore_ships=False)
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
            max_corrections=correction,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=avoid_ship)
        # If the move is possible, add it to the command_queue (if there are too many obstacles on the way
        # or we are trapped (or we reached our destination!), navigate_command will return null;
        # don't fret though, we can run the command again the next turn)
        # logging.info("Normal navigation command : %s",navigate_command)
        if not navigate_command:
            # logging.info("I went in None")
            navigate_command = ship.navigate(
            ship.closest_point_to(ship.target_planet),
            game_map,
            max_corrections=360,
            speed=int(hlt.constants.MAX_SPEED/2),
            ignore_ships=avoid_ship)
        if not navigate_command:
            # logging.info("I went in deep None")
            navigate_command = ship.navigate(
                ship.closest_point_to(ship.target_planet),
                game_map,
                max_corrections=360,
                speed=int(hlt.constants.MAX_SPEED / 2),
                ignore_ships=True)
    if navigate_command:
        return navigate_command


def attack(ship, game_map,):
    # If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
    if ship.can_suicide(ship.target_planet):
        # We add the command by appending it to the command_queue
        navigate_command = ship.navigate(
            ship.target_planet,
            game_map,
            speed=int(hlt.constants.MAX_SPEED),
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
            max_corrections=90,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=False)
        # If the move is possible, add it to the command_queue (if there are too many obstacles on the way
        # or we are trapped (or we reached our destination!), navigate_command will return null;
        # don't fret though, we can run the command again the next turn)
    # logging.info("Normal navigation command : %s",navigate_command)
    if not navigate_command:
        # logging.info("I went in None")
        navigate_command = ship.navigate(
        ship.closest_point_to(ship.target_planet),
        game_map,
        max_corrections=360,
        speed=int(hlt.constants.MAX_SPEED),
        ignore_ships=False)
    if not navigate_command:
        # logging.info("I went in deep None")
        navigate_command = ship.navigate(
            ship.closest_point_to(ship.target_planet),
            game_map,
            max_corrections=360,
            speed=int(hlt.constants.MAX_SPEED / 2),
            ignore_ships=True)
    if navigate_command:
        return navigate_command


# We use this navigation tool to attack a other ship (suicide on him)
def attack_ship(ship, game_map,):
    # If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
    # logging.info("The targeted ship is : %s", ship.target_ship)
    if ship.can_kill(ship.target_ship):
        # We add the command by appending it to the command_queue
        navigate_command = ship.navigate(
            ship.target_ship,
            game_map,
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
            max_corrections=90,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=False)
        # If the move is possible, add it to the command_queue (if there are too many obstacles on the way
        # or we are trapped (or we reached our destination!), navigate_command will return null;
        # don't fret though, we can run the command again the next turn)
    # logging.info("Normal navigation command : %s",navigate_command)
    if not navigate_command:
        # logging.info("I went in None")
        navigate_command = ship.navigate(
        ship.closest_point_to(ship.target_ship),
        game_map,
        max_corrections=360,
        speed=int(hlt.constants.MAX_SPEED),
        ignore_ships=False)
    if not navigate_command:
        # logging.info("I went in deep None")
        navigate_command = ship.navigate(
            ship.closest_point_to(ship.target_ship),
            game_map,
            max_corrections=360,
            speed=int(hlt.constants.MAX_SPEED / 2),
            ignore_ships=True)
    if navigate_command:
        return navigate_command