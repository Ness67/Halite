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
        self.TIMEOUT_PROTECTION = 120
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
        self.barycenter_planet = entity.Position(0, 0)
        self.start_time = 0
        self.ship_planet_target = dict()
        self.ship_planet_colonise = dict()
        self.ship_ship_crash = dict()
        self.ship_planet_attack = dict()
        self.ship_planet_defend = dict()
        self.cant_move_ship = dict()
        self.ship_planet_destroy = dict()

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
        # Calculate the barycenter of all planet
        if self.my_planets:
            n = 0
            x = 0
            y = 0
            for planet in self.my_planets:
                n += 1
                x += planet.x
                y += planet.y
            self.barycenter_planet.x = x / n
            self.barycenter_planet.y = y / n
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

        for ship in self.my_undocked_ships:
            if ship.id in self.ship_planet_colonise:
                if self.ship_planet_colonise[ship.id].free_dock() > self.ship_planet_colonise[ship.id].targeted:
                    ship.target = self.ship_planet_colonise[ship.id]
                    ship.target.targeted += 1
                    ship.action = "colonise"

    def select_target_3(self, ship: entity.Ship, max_ship_planet: int = 100, distance_to_look: int = 3000, early=0) \
            -> entity.Ship:
        """
        :param early: If we are in early game or not
        :param max_ship_planet: the max number of ship / planet
        :param distance_to_look:  the max distance to look for a planet to colonise
        :param ship: the ship that need a target
        :type ship: the updated value of the ship with the target
        :return ship: the amended ship with a target and an action
        """

        # We check if the ship already has a target
        if ship.id in self.ship_planet_colonise:
            if self.ship_planet_colonise[ship.id].free_dock() >= self.ship_planet_colonise[ship.id].targeted:
                ship.target = self.ship_planet_colonise[ship.id]
                ship.action = "colonise"
                logging.info("Ship: %d going to colonise planet : %d", ship.id, ship.target.id)
                return ship
            else:
                logging.info("planet %d is crowded with %d", self.ship_planet_colonise[ship.id].id, self.ship_planet_colonise[ship.id].targeted)
                ship.action = "no target"
        if ship.id in self.ship_ship_crash:
            if self.ship_ship_crash[ship.id] in self.enemy_ship:
                ship.target = self.ship_ship_crash[ship.id]
                ship.action = "ship crash"
                return ship
            else:
                ship.action = "no target"
        if ship.id in self.ship_planet_defend:
            if self.ship_planet_defend[ship.id] in self.my_planets:
                # If the planet is still to me going to defend
                ship.target = self.defend_planet(self.ship_planet_defend[ship.id])
                if ship.target:
                    # There is a ship near the planet, so we will attack
                    ship.action = "crash ship"
                    return ship
                else:
                    ship.action = "defend"
                    ship.target = None
                    return ship
            else:
                ship.action = "no target"
        if ship.id in self.ship_planet_destroy:
            if self.ship_planet_attack[ship.id] in self.enemy_planets:
                ship.target = self.ship_planet_destroy[ship.id]
                ship.action = "destroy planet"
                return ship
            else:
                ship.action = "no target"
        if ship.id in self.ship_planet_attack:
            if self.ship_planet_attack[ship.id] in self.enemy_planets:
                ship.target = self.ship_planet_defend[ship.id]
                ship.action = "attack docked"
            return ship
        else:
            ship.action = "no target"

        # For each planet in the self.game (only non-destroyed planets are included) Only used for early game
        if early:
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
            if ship.target:
                ship.target.targeted += 1
            else:
                ship = self.select_target_3(ship)
            return ship

        # If the previous target is now invalid
        if ship.action == "no target":
            # Attack an enemy planet
            if self.enemy_planets:
                # If there are still enemy planets
                invaded_planet = self.nearest_target_planet(ship, Genre.enemyPlanet)
                # Check if all the ship of the planet are already targeted
                for bad_ship in invaded_planet.all_docked_ships():
                    if not bad_ship.targeted:
                        ship.target = bad_ship
                        ship.target.targeted += 1
                        self.ship_ship_crash[ship.id] = ship.target
                        ship.action = "attack docked"
                        return ship

        if ship.action == "no target":
            # Attack a random ship
            ship.target = random.choice(self.enemy_ship)
            self.ship_ship_crash[ship.id] = ship.target
            ship.action = "crash ship"
            # If there is no more Planet start to attack other ship
            return ship

        if not ship.action:
            # First time we choose a task for this ship
            origin_planet = self.nearest_target_planet(ship, Genre.myPlanet)
            if origin_planet.defended < 3:
                ship.target = entity.Position(ship.x, ship.y)
                ship.action = "defend"
                origin_planet.defended += 1
                self.ship_planet_defend[ship.id] = origin_planet
                return ship
            else:
                ship.action = "no target"
                ship = self.select_target_3(ship)  # We redo the process to find the appropriate target for the ship
                return ship

    def normal_navigation(self, ship, avoid_ship, correction=10, angular=5, avoid=True):
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
            avoid_obstacles=avoid,
            max_corrections=correction,
            speed=int(hlt.constants.MAX_SPEED),
            ignore_ships=avoid_ship)
        # logging.info("Finished Normal navigation for ship %d with %s order", ship.id, navigate_command)
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
                avoid_obstacles=avoid,
                angular_step=20,
                max_corrections=18,
                speed=int(hlt.constants.MAX_SPEED),
                ignore_ships=avoid_ship)
            # logging.info("Finished Advanced navigation for ship %d with %s order", ship.id, navigate_command)
            # logging.info("Advanced Navigation lasted : %s ms", current_milli_time() - start_time_measure_special)
        if navigate_command:
            return navigate_command

    def decide_navigation(self, ship, ignore_ship=False, correction=18, angular=10):
        # logging.info("Enter Navigation for ship : %d, ship action is : %s", ship.id, ship.action)
        navigate_command = 0
        avoid = True
        if ship.id in self.cant_move_ship and self.cant_move_ship[ship.id] >= 2:
            # Force to avoid other ship if can't find a other way
            logging.info("to mush try, going to ignore other ship. ship : %d", ship.id)
            ignore_ship = True
            avoid = False  # Will disable obstacle avoidance
            self.cant_move_ship.pop(ship.id)

        # start_time_measure = self.current_milli_time()
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
                    avoid_obstacles=avoid,
                    angular_step=2,
                    speed=int(hlt.constants.MAX_SPEED / 2),
                    ignore_ships=False)
                # logging.info("Finished Precision navigation for ship %d with %s order", ship.id, navigate_command)
                # logging.info("Precision Navigation lasted : %s ms", self.current_milli_time() - start_time_measure)
            else:
                navigate_command = self.normal_navigation(ship, ignore_ship, correction, angular, avoid)

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
                # logging.info("Finished destroy planet procedure for ship %d with %s order", ship.id, navigate_command)
            else:
                navigate_command = self.normal_navigation(ship, ignore_ship, correction, angular, avoid)

        elif ship.action == "attack docked":
            if ship.can_suicide(ship.target):
                # We add the command by appending it to the command_queue
                navigate_command = ship.navigate(
                    ship.closest_point_to(ship.target, min_distance=2),
                    self.map_of_game,
                    speed=int(hlt.constants.MAX_SPEED),
                    avoid_obstacles=avoid,
                    max_corrections=15,
                    ignore_ships=False,
                    ignore_planets=False)
                # logging.info("Finished destroy planet procedure for ship %d with %s order", ship.id, navigate_command)
            else:
                navigate_command = self.normal_navigation(ship, ignore_ship, correction, angular, avoid)

        elif ship.action == "defend":
            if ship.can_suicide(ship.target):
                # We add the command by appending it to the command_queue
                navigate_command = ship.navigate(
                    ship.target,
                    self.map_of_game,
                    speed=int(hlt.constants.MAX_SPEED),
                    avoid_obstacles=avoid,
                    max_corrections=15,
                    ignore_ships=False,
                    ignore_planets=False)
                # logging.info("Finished defend planet procedure for ship %d with %s order", ship.id, navigate_command)
            else:
                navigate_command = self.normal_navigation(ship, ignore_ship, correction, angular, avoid)

        # If the flag ship is raise we attack a ship
        elif ship.action == "crash ship":
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
                # logging.info("Finished Attack ship procedure for ship %d with %s order", ship.id, navigate_command)
            else:
                navigate_command = self.normal_navigation(ship, ignore_ship, correction, angular, avoid)

        if ignore_ship:
            logging.info("Target: %d  Action: %s  Nav: %s", ship.target.id, ship.action, navigate_command)
        if navigate_command:
            return navigate_command
        elif ship.id in self.cant_move_ship:
            self.cant_move_ship[ship.id] += 1
        else:
            self.cant_move_ship[ship.id] = 1

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

            if self.nb_turn < 60:
                ship = self.select_target_3(ship, max_ship_planet=2, early=1)
            else:
                ship = self.select_target_3(ship, early=1)
            # logging.info("Select target lasted : %s ms", self.current_milli_time() - start_time_select)
            navigate_command = self.decide_navigation(ship)

            # logging.info("Ship %d has %s move Command", ship.id, navigate_command)
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
            start_time_select = self.current_milli_time()
            ship = self.select_target_3(ship)
            # logging.info("Select target for ship %d lasted : %s ms", ship.id, self.current_milli_time() - start_time_select)
            # logging.info("Ship %d has %s on %d target", ship.id, ship.action, ship.target.id)
            start_time_nav = self.current_milli_time()
            navigate_command = self.decide_navigation(ship)
            if self.current_milli_time() - start_time_nav > 5:
                logging.info("ship %d : Navigation for %d to %s lasted : %s ms", ship.id, ship.target.id, ship.action, self.current_milli_time() - start_time_nav)

            # logging.info("Ship %d has %s move Command", ship.id, navigate_command)
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

    def nearest_target_ship(self, origin: entity.Entity, target_type: Genre = Genre.neutralPlanet, retarget=False) -> entity.Ship:
        short_dist = 3000
        closest = 0
        if target_type == Genre.enemyShip and self.enemy_ship:
            for enemyShip in self.enemy_ship:
                if enemyShip.targeted and not retarget:
                    # If the ship already have a order skip it
                    continue
                dist = enemyShip.calculate_distance_between(origin)
                if dist < short_dist:
                    short_dist = dist
                    closest = enemyShip
            return closest
        elif target_type == Genre.myShip and self.my_undocked_ships:
            for myShip in self.my_undocked_ships:
                if myShip.action and not retarget and myShip.action != "no target":
                    # If the ship already have a order skip it
                    continue
                dist = myShip.calculate_distance_between(origin)
                if dist < short_dist:
                    short_dist = dist
                    closest = myShip
            return closest

    def go_colonise(self, planet: entity.Planet, max_target=100) -> None:
        nearest_ship = 1
        while planet.targeted < planet.free_dock() and nearest_ship and planet.targeted < max_target:
            # logging.info("Il y a %d slot libre sur la planet %d, %d vaiseaux y vont", planet.free_dock(), planet.id, planet.targeted)
            nearest_ship = self.nearest_target_ship(planet, Genre.myShip, retarget=False)
            # logging.info("Le vaisseau le plus proche est : %s", nearest_ship)
            if nearest_ship:
                self.ship_planet_colonise[nearest_ship.id] = planet
                logging.info("ship: %d go to planet: %s", nearest_ship.id, self.ship_planet_colonise[nearest_ship.id])
                planet.targeted += 1
                nearest_ship.target = planet
                nearest_ship.action = "colonise"

    def defend_planet(self, planet: entity.Planet) -> entity.Ship:
        closest_enemy_ship = self.nearest_target_ship(planet, Genre.enemyShip, True)
        if closest_enemy_ship and planet.calculate_distance_between(closest_enemy_ship) < 15:
            return closest_enemy_ship
