import hlt
import logging
import time
from hlt import *
import random
from enum import Enum
import math


class Genre(Enum):
    allPlanet = 1
    myPlanet = 2
    enemyPlanet = 3
    neutralPlanet = 4
    enemyShip = 5
    myShip = 6


class Bot:
    """
        Bot that will take the decision for the game

        :ivar game: The game data
        """
    
    def __init__(self, game):
        """
        :param game: The game data
        """
        self.TIMEOUT_PROTECTION = 1700
        self.game = game
        self.enemy_ship = []
        self.enemy_planets = []
        self.my_planets = []
        self.neutral_planets = []
        self.my_undocked_ships = []
        self.my_docked_ships = []
        # Here we define the set of commands to be sent to the Halite engine at the end of the turn
        self.command_queue = []
        self.map_of_game = game_map.Map(0, 0, 0)
        self.nb_turn = 0
        self.barycenter_ship = entity.Position(0, 0)
        self.start_time = 0
        self.ship_planet_target = dict()
        self.ship_planet_colonise = dict()
        self.ship_ship_target = dict()
        self.ship_planet_attack = dict()
        self.ship_planet_defend = dict()

    @staticmethod
    def current_milli_time():
        return int(round(time.time() * 1000))

    def map_update(self):
        self.map_of_game = self.game.update_map()

    def turn_init(self):
        # Initializing the turn variable
        self.enemy_ship = []
        self.enemy_planets = []
        self.my_planets = []
        self.neutral_planets = []
        self.my_undocked_ships = []
        self.my_docked_ships = []
        # Here we define the set of commands to be sent to the Halite engine at the end of the turn
        self.command_queue = []

        # List all enemy ship
        for player in self.map_of_game.all_players():
            if player != self.map_of_game.get_me():
                self.enemy_ship.extend(player.all_ships())
        # List all my ship
        for ship in self.map_of_game.get_me().all_ships():
            if ship.docking_status != ship.DockingStatus.UNDOCKED:
                # logging.info("Ship %d Docked", ship.id)
                self.my_docked_ships.append(ship)
            else:
                self.my_undocked_ships.append(ship)

        # list of planets
        for planet in self.map_of_game.all_planets():
            planet.targeted = 0  # Reset the target counter for the planet
            planet.defended = 0  # Reset the defend counter for the planet
            if planet.is_owned():
                if planet.owner == self.map_of_game.get_me():
                    self.my_planets.append(planet)
                else:
                    self.enemy_planets.append(planet)
            else:
                self.neutral_planets.append(planet)
        # Calculate the barycenter of all ship
        if self.map_of_game.get_me().all_ships():
            n = 0
            x = 0
            y = 0
            for ship in self.map_of_game.get_me().all_ships():
                n += 1
                x += ship.x
                y += ship.y
            self.barycenter_ship.x = x / n
            self.barycenter_ship.y = y / n

    def select_target_3(self, ship: entity.Ship, max_ship_planet: int = 100, distance_to_look: int = 3000) \
            -> entity.Ship:
        """
        :param max_ship_planet: the max number of ship / planet
        :param distance_to_look:  the max distance to look for a planet to colonise
        :param ship: the ship that need a target
        :type ship: the updated value of the ship with the target
        :return ship: the amended ship with a target and an action
        """

        # logging.info("Select target for ship :%s", ship.id)
        logging.info("Start targeting for ship %d", ship.id)
        # We check if the ship already has a target
        if ship.id in self.ship_planet_colonise:
            if self.ship_planet_colonise[ship.id].free_dock() > self.ship_planet_colonise[ship.id].targeted:
                ship.target = self.ship_planet_colonise[ship.id]
                ship.target.targeted += 1
                ship.action = "colonise"
                # logging.info("Keep this target")
                return ship
        if ship.id in self.ship_ship_target:
            logging.info("ship %d had already a ship target : %d", ship.id, self.ship_ship_target[ship.id].id)
            if self.ship_ship_target[ship.id] in self.enemy_ship:
                ship.target = self.ship_ship_target[ship.id]
                ship.action = "attack docked"
                # logging.info("Keep this target")
                return ship
        if ship.id in self.ship_planet_defend:
            logging.info("ship %d had already a defense target : %s", ship.id, self.ship_planet_defend[ship.id])
            ship.target = self.ship_planet_defend[ship.id]
            ship.target.linked_planet.defended += 1
            ship.action = "defend"
            # logging.info("Keep this target")
            return ship

        # For each planet in the self.game (only non-destroyed planets are included)
        for planet in self.neutral_planets + self.my_planets:
            if planet.targeted >= planet.free_dock() or planet.targeted >= max_ship_planet:
                # if the planet is full or if there is too much ship going skip this planet
                continue
            dist = ship.calculate_distance_between(planet)
            if distance_to_look >= dist:
                distance_to_look = dist
                ship.target = planet
                self.ship_planet_colonise[ship.id] = ship.target
                ship.action = "colonise"
                # ship.target = map_of_game.get_planet(1)
                # logging.info("Ship = %s Distance : %s Planete = %s", ship.id, dist, planet.id)

        if ship.action != "colonise":
            # Attack an enemy planet
            if self.enemy_planets:
                invaded_planet = self.nearest_target_planet(ship, Genre.enemyPlanet)
                # Check if all the ship of the planet are already targeted
                for bad_ship in invaded_planet.all_docked_ships():
                    if not bad_ship.targeted:
                        ship.target = bad_ship
                        ship.target.targeted += 1
                        self.ship_ship_target[ship.id] = ship.target
                        ship.action = "attack docked"
                        break
                if ship.action != "attack docked":
                    # All the of the planet ship are already targeted going to defend
                    planet_to_defend = self.nearest_target_planet(ship, Genre.myPlanet)
                    if planet_to_defend.defended < 5:
                        # If there is less than 5 ship defending the planet
                        ship.target = self.defend_planet(planet_to_defend)
                        ship.target.linked_planet = planet_to_defend
                        self.ship_planet_defend[ship.id] = ship.target
                        ship.action = "defend"
                    else:
                        # Otherwise attack a random ship
                        ship.target = random.choice(self.enemy_ship)
                        self.ship_ship_target[ship.id] = ship.target
                        ship.action = "ship"
                # logging.info("Attack target planet: %s", ship.target)
                return ship
            # If there is no more Planet start to attack other ship
            else:
                ship.target = random.choice(self.enemy_ship)
                logging.info("The targeted ship is : %s", ship.target)
                self.ship_ship_target[ship.id] = ship.target
                ship.action = "ship"
                return ship

        ship.target.targeted += 1
        return ship

    def normal_navigation(self, ship, avoid_ship, correction=10, angular=5):
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
            self.map_of_game,
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
            # start_time_measure_special = current_milli_time()
            # logging.info("I went in None")
            navigate_command = ship.navigate(
                ship.closest_point_to(ship.target),
                self.map_of_game,
                angular_step=20,
                max_corrections=18,
                speed=int(hlt.constants.MAX_SPEED),
                ignore_ships=avoid_ship)
            logging.info("Finished Advanced navigation for ship %d with %s order", ship.id, navigate_command)
            # logging.info("Advanced Navigation lasted : %s ms", current_milli_time() - start_time_measure_special)
        if navigate_command:
            return navigate_command

    def decide_navigation(self, ship, avoid_ship=False, correction=10, angular=5):
        logging.info("Enter Navigation for ship : %d, ship action is : %s", ship.id, ship.action)
        navigate_command = 0
        start_time_measure = self.current_milli_time()
        # If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
        if ship.action == "colonise":
            if ship.can_dock(ship.target):
                # We add the command by appending it to the command_queue
                navigate_command = ship.dock(ship.target)
            elif ship.near_planet(ship.target):
                navigate_command = ship.navigate(
                    ship.closest_point_to(ship.target),
                    self.map_of_game,
                    max_corrections=180,
                    angular_step=2,
                    speed=int(hlt.constants.MAX_SPEED / 2),
                    ignore_ships=False)
                logging.info("Finished Precision navigation for ship %d with %s order", ship.id, navigate_command)
                logging.info("Precision Navigation lasted : %s ms", self.current_milli_time() - start_time_measure)
            else:
                navigate_command = self.normal_navigation(ship, avoid_ship, correction, angular)

        # If the flag "planet" is raise we attack the planet
        elif ship.action == "destroy planet":
            if ship.can_suicide(ship.target):
                # We add the command by appending it to the command_queue
                navigate_command = ship.navigate(
                    ship.target,
                    self.map_of_game,
                    speed=int(hlt.constants.MAX_SPEED),
                    max_corrections=5,
                    avoid_obstacles=False,
                    ignore_ships=True,
                    ignore_planets=True)
                logging.info("Finished destroy planet procedure for ship %d with %s order", ship.id, navigate_command)
            else:
                navigate_command = self.normal_navigation(ship, avoid_ship, correction, angular)

        elif ship.action == "attack docked":
            if ship.can_suicide(ship.target):
                # We add the command by appending it to the command_queue
                navigate_command = ship.navigate(
                    ship.closest_point_to(ship.target, min_distance=2),
                    self.map_of_game,
                    speed=int(hlt.constants.MAX_SPEED),
                    max_corrections=15,
                    ignore_ships=False,
                    ignore_planets=False)
                logging.info("Finished destroy planet procedure for ship %d with %s order", ship.id, navigate_command)
            else:
                navigate_command = self.normal_navigation(ship, avoid_ship, correction, angular)

        elif ship.action == "defend":
            if ship.can_suicide(ship.target):
                # We add the command by appending it to the command_queue
                navigate_command = ship.navigate(
                    ship.target,
                    self.map_of_game,
                    speed=int(hlt.constants.MAX_SPEED),
                    max_corrections=15,
                    ignore_ships=False,
                    ignore_planets=False)
                logging.info("Finished destroy planet procedure for ship %d with %s order", ship.id, navigate_command)
            else:
                navigate_command = self.normal_navigation(ship, avoid_ship, correction, angular)

        # If the flag ship is raise we attack a ship
        elif ship.action == "ship":
            if ship.can_kill(ship.target):
                # We add the command by appending it to the command_queue
                navigate_command = ship.navigate(
                    ship.target,
                    self.map_of_game,
                    max_corrections=10,
                    speed=int(hlt.constants.MAX_SPEED),
                    avoid_obstacles=False,
                    ignore_ships=True,
                    ignore_planets=True)
                logging.info("Finished Attack ship procedure for ship %d with %s order", ship.id, navigate_command)
            else:
                navigate_command = self.normal_navigation(ship, avoid_ship, correction, angular)

        if navigate_command:
            return navigate_command

    def strategy_early_game(self):
        # For every ship that I control
        for ship in self.map_of_game.get_me().all_ships():
            # logging.info("Start Working on ship : %s", ship)
            if self.current_milli_time() - self.start_time >= self.TIMEOUT_PROTECTION:
                # if time is running out send command
                logging.info("turn %d lasted : %s ms : Going to break", self.nb_turn, self.current_milli_time()
                             - self.start_time)
                break
            # If the ship is docked
            if ship.docking_status != ship.DockingStatus.UNDOCKED:
                # Skip this ship
                # logging.info("Ship %d Docked", ship.id)
                continue

            ship = self.select_target_3(ship, max_ship_planet=2)
            # logging.info("Select target lasted : %s ms", self.current_milli_time() - start_time_select)
            navigate_command = self.decide_navigation(ship)

            logging.info("Ship %d has %s move Command", ship.id, navigate_command)
            if navigate_command:
                self.command_queue.append(navigate_command)

    def strategy_end_game(self):
        # Will assign nearest ship to a planet to colonise
        for planet in self.neutral_planets + self.my_planets:
            if planet.targeted >= planet.free_dock():
                # if the planet is full or if there is too much ship going skip this planet
                continue
            else:
                self.go_colonise(planet)

        # For every ship that I control
        for ship in self.my_undocked_ships:
            # logging.info("Start Working on ship : %s", ship)
            if self.current_milli_time() - self.start_time >= self.TIMEOUT_PROTECTION:
                # if time is running out send command
                logging.info("turn %d lasted : %s ms : Going to break", self.nb_turn, self.current_milli_time()
                             - self.start_time)
                break
            ship = self.select_target_3(ship)
            # logging.info("Select target lasted : %s ms", self.current_milli_time() - start_time_select)
            navigate_command = self.decide_navigation(ship)

            logging.info("Ship %d has %s move Command", ship.id, navigate_command)
            if navigate_command:
                self.command_queue.append(navigate_command)

    def nearest_target_planet(self, origin: entity.Entity, target_type: object = Genre.neutralPlanet) -> entity.Planet:
        short_dist = 3000
        closest = 0
        if target_type == Genre.allPlanet:
            for planet in self.map_of_game.all_planets():
                dist = planet.calculate_distance_between(origin)
                if dist < short_dist:
                    short_dist = dist
                    closest = planet
            return closest
        elif target_type == Genre.myPlanet and self.my_planets:
            for planet in self.my_planets:
                dist = planet.calculate_distance_between(origin)
                if dist < short_dist:
                    short_dist = dist
                    closest = planet
            return closest
        elif target_type == Genre.enemyPlanet and self.enemy_planets:
            for planet in self.enemy_planets:
                dist = planet.calculate_distance_between(origin)
                if dist < short_dist:
                    short_dist = dist
                    closest = planet
            return closest
        elif target_type == Genre.neutralPlanet and self.neutral_planets:
            for planet in self.neutral_planets:
                dist = planet.calculate_distance_between(origin)
                if dist < short_dist:
                    short_dist = dist
                    closest = planet
            return closest

    def nearest_target_ship(self, origin: entity.Entity, target_type: Genre = Genre.neutralPlanet, retarget=0) -> entity.Ship:
        short_dist = 3000
        closest = 0
        if target_type == Genre.enemyShip and self.enemy_ship:
            for enemyShip in self.enemy_ship:
                dist = enemyShip.calculate_distance_between(origin)
                if dist < short_dist:
                    short_dist = dist
                    closest = enemyShip
            return closest
        elif target_type == Genre.myShip and self.my_undocked_ships:
            for myShip in self.my_undocked_ships:
                if myShip.action or not retarget:
                    # If the ship already have a order skip it
                    continue
                dist = myShip.calculate_distance_between(origin)
                if dist < short_dist:
                    short_dist = dist
                    closest = myShip
            return closest

    def go_colonise(self, planet: entity.Planet) -> None:
        nearest_ship = 1
        while planet.targeted < planet.free_dock() and nearest_ship:
            logging.info("Il y a %d slot libre sur la planet %d, %d vaiseaux y vont", planet.id, planet.free_dock(), planet.targeted)
            nearest_ship = self.nearest_target_ship(planet, Genre.myShip)
            if nearest_ship:
                nearest_ship.target = planet
                self.ship_planet_colonise[nearest_ship.id] = nearest_ship.target
                nearest_ship.action = "colonise"
                planet.targeted += 1

    @staticmethod
    def defend_planet(planet: entity.Planet) -> entity.Position:
        angle = random.randint(1, 360)
        target_dx = math.cos(math.radians(angle)) * 10
        target_dy = math.sin(math.radians(angle)) * 10
        return entity.Position(planet.x + target_dx, planet.y + target_dy)
