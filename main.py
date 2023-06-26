from __future__ import print_function
from __future__ import division

# multi-agent missions - two agents human in a flat environment.
from builtins import range
import sys
import uuid
import time
import json
from malmoutils import MalmoPython, get_xml, safe_start_mission, safe_wait_for_start, update_client_pool, config
from observation import update_entities_info, update_chat_log, get_inventory_info, update_grid, same_position, update_builder_mode
from register import save_world_state
import threading
import queue

# Create one agent host for parsing:
agent_hosts = [MalmoPython.AgentHost()]

# Parse the command-line options:
agent_hosts[0].addOptionalFlag( "debug,d", "Display debug information.")
agent_hosts[0].addOptionalIntArgument("agents,n", "Number of agents to use, including observer.", 3)


try:
    agent_hosts[0].parse( sys.argv )
except RuntimeError as e:
    print('ERROR:',e)
    print(agent_hosts[0].getUsage())
    exit(1)
if agent_hosts[0].receivedArgument("help"):
    print(agent_hosts[0].getUsage())
    exit(0)

DEBUG = agent_hosts[0].receivedArgument("debug")
INTEGRATION_TEST_MODE = agent_hosts[0].receivedArgument("test")
agents_requested = agent_hosts[0].getIntArgument("agents")
num_distant_agents = config["agents"]["num_distant_agents"]
# remove the ADMIN(observer) from the number of agents and the number of distant agents
NUM_AGENTS = agents_requested - 1 - num_distant_agents

# Create the rest of the agent hosts - one for each human agent and one to control the observer for now one local and other waiting for connection:
agent_hosts += [MalmoPython.AgentHost() for _ in range(1, NUM_AGENTS + 1) ]

# Set up debug output:
for ah in agent_hosts:
    ah.setDebugOutput(DEBUG)    # Turn client-pool connection messages on/off.

if sys.version_info[0] == 2:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
else:
    import functools
    print = functools.partial(print, flush=True)

# Set up a client pool.
# The IP address used in the client pool will be broadcast to other agents who
# are attempting to find the server
client_pool_array = []
for x in range(10000, 10000 + NUM_AGENTS + 1):
    client_pool_array.append([config['server']['ip'], x])

# A log of all chats in the game
chat_log = []

# get the types of blocks to track
grid_types = set()
for agent in list(config['inventory'].keys()):
    for item in config['inventory'][agent]:
        grid_types.add(item['type'])
    

#get the number of missions to run
num_missions = config['mission']['num_missions']

size = (config['mission']['area_side_size']) / 2

for mission_no in range(0, num_missions + 1):
    print("Running mission #" + str(mission_no))
    print(agent_hosts)
    # force reset mission 0
    tempForceReset = config['mission']['force_reset']
    if mission_no == 0:
        config['mission']['force_reset'] = 1
    # Create mission xml - use force reset if this is the first mission.
    my_mission = MalmoPython.MissionSpec(get_xml(NUM_AGENTS, config), True)
    # set the force reset back to the original value
    config['mission']['force_reset'] = tempForceReset

    # Generate an experiment ID for this mission.
    # This is used to make sure the right clients join the right servers -
    # if the experiment IDs don't match, the startMission request will be rejected.
    # ID would probably suffice, though changing the ID on each mission also catches
    # potential problems with clients and servers getting out of step.
    experimentID = str(uuid.uuid4())

    # redefine the client pool
    client_pool = MalmoPython.ClientPool()
    for id, port in client_pool_array:
        client_pool.add(MalmoPython.ClientInfo(id, port))

    ## visualize the clients connecting to the server    
    #print("client_pool " + str(client_pool))

    # Attempt to start the mission:
    for i in range(len(agent_hosts)):
        agent_hosts[i].setObservationsPolicy(MalmoPython.ObservationsPolicy.LATEST_OBSERVATION_ONLY)
        agent_hosts[i].setVideoPolicy(MalmoPython.VideoPolicy.LATEST_FRAME_ONLY)
        safe_start_mission(agent_hosts[i], my_mission, client_pool, MalmoPython.MissionRecordSpec(), i, experimentID)

    safe_wait_for_start(agent_hosts)

    time.sleep(1)

    # running is true if at least one agent is still running the mission
    running = True
    # the last entities seen by the agents
    last_entity = None
    # the last grid seen by the agents
    grid = {}
    
    names = []
    for j in range(NUM_AGENTS):
        names.append(config['agents']['builder_' + str(j + 1)]['name'])
    # Disable feedback from the agents for all agents
    agent_hosts[0].sendCommand("chat /gamerule sendCommandFeedback false")
    # Admin make builder able to destroy blocks in one hit
    agent_hosts[0].sendCommand("chat /effect @a[name=" + names[0] + "] haste 1000000 255 true")
    # make architect in adventure mode
    agent_hosts[0].sendCommand("chat /gamemode adventure @a[name=" + names[1] + "]")
    
    lock = threading.Lock()
    
    # check grid change variable
    grid_change = threading.Event()
    
    # builder mode 
    builder_mode = 1
    
    # add indication that a mission has started in the chat log
    chat_log.append("Mission " + str(mission_no) + " started")
    running = True
    
    precision = config['collect']['agents_position']['precision']
    angle_precision = config['collect']['agents_position']['angle_precision']
    
    while running:
        #waiting to get all players connected if not all connected
        if NUM_AGENTS < 2:
            last_num_agents = NUM_AGENTS
            print("Waiting for players to connect...", end="")
            while NUM_AGENTS < 2:
                NUM_AGENTS = update_client_pool(client_pool_array,config, NUM_AGENTS)
                if NUM_AGENTS == 2:
                    print("All players connected!")
                    # make the players quit the game to restart the mission
                    for i in range(len(agent_hosts)):
                        agent_hosts[i].sendCommand("quit")
                    # add new agent_hosts
                    agent_hosts += [MalmoPython.AgentHost() for _ in range(last_num_agents + 1, NUM_AGENTS + 1)]
                    # Set up debug output:
                    for i in range(last_num_agents + 1, NUM_AGENTS + 1):
                        agent_hosts[i].setDebugOutput(DEBUG)
                #wait for 1 second
                time.sleep(1)
        
        running = False
        queue_entities = queue.Queue()
        for i in range(1, len(agent_hosts)):
            world_state = agent_hosts[i].peekWorldState()
            if world_state.is_mission_running:
                running = True             
                # get the number of observations since last state
                obs_num = world_state.number_of_observations_since_last_state

                ## to print the number of observations since last state 
                #print("Got " + str(obs_num) + " observations since last state.")

                if obs_num > 0:
                    # get the last observation
                    msg = world_state.observations[-1].text
                    ob = json.loads(msg)

                    # get timestamp
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

                    # get agents information's
                    threading.Thread(target=update_entities_info, args=(ob, queue_entities, last_entity)).start()
                    entities = queue_entities.get()
                    
                    # if los and its the obs of builder
                    if i == 1 and u"LineOfSight" in ob:
                        # if the agent is looking outside the grid make him unable to destroy or place blocks
                        los = ob.get(u"LineOfSight")
                        builder_mode = update_builder_mode(agent_hosts[0], los, names, builder_mode, size, grid_types)
                    
                    if config['collect']['chat_history']:
                        # update chat log and get true if a new message has been added
                        change = update_chat_log(ob, chat_log, config)
                    else:
                        chat_log = None
                        change = False

                    # if not needed don't collect inventory
                    if not config['collect']['agents_inventory']:
                        inventory = None
                    else:
                        # get builders inventory
                        inventory = get_inventory_info(ob , entities)
                    
                    # update grid and get true if a new block has been added
                    if config['collect']['blocks_in_grid']:
                        threading.Thread(target=update_grid, args=(ob, grid, config['mission']['area_side_size'], grid_types, grid_change)).start()
                        change = grid_change.is_set() or change
                        if grid_change.is_set():
                            grid_change.clear()
                    else:
                        grid = None
                    
                    # print to console - if no change since last observation at the precision level, don't bother printing again.
                    if (same_position(entities, last_entity, precision, angle_precision) and not change):
                        # no change since last observation - don't bother printing again.
                        last_entity = entities
                        continue
                    
                    # update lastEntities for next observation
                    last_entity = entities

                    # clear entities position if not needed
                    if not config['collect']['agents_position']['save']:
                        entities = None

                    # open a new process to save the data and screenshot and print to console since it is not important to wait for it
                    if config['collect']['log']['txt'] or config['collect']['log']['json'] or config['collect']['log']['console'] or config['collect']['screenshot']["save"]:
                        # create a new thread to save the data
                        # thread-safe write to file
                        p = threading.Thread(target=save_world_state, args=(lock, agent_hosts[0], config, experimentID, timestamp, entities, chat_log, inventory, grid))
                        # dont wait for the process to finish
                        p.start()
                        
        time.sleep(0.05)       
    print()

    print("Waiting for mission to end ", end=' ')
    # Mission should have ended already, but we want to wait until all the various agent hosts
    # have had a chance to respond to their mission ended message.
    hasEnded = False
    while not hasEnded:
        hasEnded = True # assume all good
        print(".", end="")
        time.sleep(0.1)
        for ah in agent_hosts:
            world_state = ah.getWorldState()
            if world_state.is_mission_running:
                hasEnded = False # all not good
    # add indication that a mission has ended in the chat log
    chat_log.append("Mission " + str(mission_no) + " ended")
    print()
    print("Mission ended")
    # Mission has ended.

    time.sleep(2)