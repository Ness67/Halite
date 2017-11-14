import hlt
import logging
def select_target(ship,game_map):
    shortest_distance = ship.calculate_distance_between(game_map.get_planet(1))
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
            ship.target = planet
            # ship.target = game_map.get_planet(1)
            logging.info("Ship = %s Distance : %s Planete = %s", ship.id, dist, planet.id)
    ship.target.targeted += 1
    return ship

