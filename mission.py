import time
import threading
import json
import queue
import uuid
from malmoutils import MalmoPython, get_xml, safe_start_mission, safe_wait_for_start, check_connected_players
from observation import update_entities_info, update_chat_log, get_inventory_info, update_grid, same_position, update_builder_mode
from register import save_world_state

class Mission:
    def __init__(self, config, agent_hosts, mission_no, debug, client_pool_array, num_agents, chat_log):
        self.config = config
        self.agent_hosts = agent_hosts
        self.debug = debug
        self.client_pool_array = client_pool_array
        self.mission_no = mission_no
        self.experiment_id = None
        self.grid_types = set()
        self.chat_log = chat_log
        self.num_agents = num_agents
        self.running = True
        self.precision = config['collect']['agents_position']['precision']
        self.angle_precision = config['collect']['agents_position']['angle_precision']
        self.grid_change = threading.Event()
        self.names = []
        self.grid = {}
        self.last_entity = None
        self.inventory = None
        self.entities = None
        self.builder_mode = 1
        self.architect_mode = 0
        self.queue_entities = queue.Queue()
        self.allow_architect_builder = False
        self.lock = threading.Lock()
        self.size = None
        
        # get the types of blocks to track
        for agent in list(config['inventory'].keys()):
            for item in config['inventory'][agent]:
                self.grid_types.add(item['type'])
                
        #names of the agents
        for j in range(2):
            self.names.append(self.config['agents']['builder_' + str(j + 1)]['name'])
        
        self.size = (config['mission']['area_side_size']) / 2
    
    def start(self):
        print("Running mission #" + str(self.mission_no))
        print(self.agent_hosts)
        # force reset mission 0
        temp_force_reset = self.config['mission']['force_reset']
        if self.mission_no == 0:
            self.config['mission']['force_reset'] = 1
        # Create mission xml - use force reset if this is the first mission.
        my_mission = MalmoPython.MissionSpec(get_xml(self.num_agents, self.config), True)
        # set the force reset back to the original value
        self.config['mission']['force_reset'] = temp_force_reset

        # Generate an experiment ID for this mission.
        # This is used to make sure the right clients join the right servers -
        # if the experiment IDs don't match, the startMission request will be rejected.
        self.experiment_id = str(uuid.uuid4())

        # redefine the client pool
        client_pool = MalmoPython.ClientPool()
        for id, port in self.client_pool_array:
            client_pool.add(MalmoPython.ClientInfo(id, port))

        # Attempt to start the mission:
        for i in range(len(self.agent_hosts)):
            self.agent_hosts[i].setObservationsPolicy(MalmoPython.ObservationsPolicy.LATEST_OBSERVATION_ONLY)
            self.agent_hosts[i].setVideoPolicy(MalmoPython.VideoPolicy.LATEST_FRAME_ONLY)
            safe_start_mission(self.agent_hosts[i], my_mission, client_pool, MalmoPython.MissionRecordSpec(), i, self.experiment_id)

        safe_wait_for_start(self.agent_hosts)

        time.sleep(1)
            
        # Disable feedback from the agents for all agents
        self.agent_hosts[0].sendCommand("chat /gamerule sendCommandFeedback false")
        # Admin make builder able to destroy blocks in one hit
        self.agent_hosts[0].sendCommand("chat /effect @a haste 1000000 255 true")

        self.allow_architect_builder = self.config['agents']['allow_architect_building']
        
    def run(self):
        while self.running:
            # check if all agents are connected
            self.num_agents, self.agent_hosts = check_connected_players(self.num_agents, self.client_pool_array, self.config, self.agent_hosts, self.debug)
            self.running = False
            # observe the world state for each agent
            for i in range(1, len(self.agent_hosts)):
                world_state = self.agent_hosts[i].peekWorldState()
                if world_state.is_mission_running:
                    self.running = True
                    self.handle_world_state(i, world_state)
            time.sleep(0.05)
        print()
        
    def handle_world_state(self, i, world_state):
        obs_num = world_state.number_of_observations_since_last_state
        if obs_num > 0:
            # read last observation
            msg = world_state.observations[-1].text
            ob = json.loads(msg)
            # collect and filter data
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
            threading.Thread(target=update_entities_info, args=(ob, self.queue_entities, self.last_entity)).start()
            self.entities = self.queue_entities.get()
            self.handle_player_rights(i, ob)
            change = self.handle_chat_log(ob)
            self.handle_inventory(ob)
            change = self.handle_grid(ob) or change
            self.handle_entity_position()
            # print to console - if no change since last observation at the precision level, don't bother printing again.
            if (not same_position(self.entities, self.last_entity, self.precision, self.angle_precision) or change):
                self.handle_data_logging(timestamp)
            self.last_entity = self.entities

    def handle_player_rights(self, i, ob):
        # depending on his sight, the player can build or not
        if u"LineOfSight" in ob:
            los = ob.get(u"LineOfSight")
            if i == 1:
                self.builder_mode = update_builder_mode(self.agent_hosts[0], los, self.names[0], self.builder_mode, self.size, self.grid_types)
            if i == 2 and self.allow_architect_builder:
                self.architect_mode  = update_builder_mode(self.agent_hosts[0], los, self.names[1], self.architect_mode, self.size, self.grid_types)

    def handle_chat_log(self, ob):
        if self.config['collect']['chat_history']:
            return update_chat_log(ob, self.chat_log, self.config)
        else:
            self.chat_log = None
            return False

    def handle_inventory(self, ob):
        if not self.config['collect']['agents_inventory']:
            self.inventory = None
        else:
            self.inventory = get_inventory_info(ob , self.entities)

    def handle_grid(self, ob):
        if self.config['collect']['blocks_in_grid']:
            threading.Thread(target=update_grid, args=(ob, self.grid, self.config['mission']['area_side_size'], self.grid_types, self.grid_change)).start()
            change = self.grid_change.is_set()
            if self.grid_change.is_set():
                self.grid_change.clear()
            return change
        else:
            self.grid = None
            return False

    def handle_entity_position(self):
        if not self.config['collect']['agents_position']['save']:
            self.entities = None

    def handle_data_logging(self, timestamp):
        if self.config['collect']['log']['txt'] or self.config['collect']['log']['json'] or self.config['collect']['log']['console'] or self.config['collect']['screenshot']["save"]:
            p = threading.Thread(target=save_world_state, args=(self.lock, self.agent_hosts[0], self.config, self.experiment_id, timestamp, self.entities, self.chat_log, self.inventory, self.grid))
            p.start()

    def end(self):
        print("Waiting for mission to end ", end=' ')
        # Mission should have ended already, but we want to wait until all the various agent hosts
        # have had a chance to respond to their mission ended message.
        has_ended = False
        while not has_ended:
            has_ended = True # assume all good
            print(".", end="")
            time.sleep(0.1)
            for ah in self.agent_hosts:
                world_state = ah.getWorldState()
                if world_state.is_mission_running:
                    has_ended = False # all not good
        # add indication that a mission has ended in the chat log
        self.chat_log.append("Mission " + str(self.mission_no) + " ended")
        print()
        print("Mission ended")
        # Mission has ended.
        time.sleep(2)
