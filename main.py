from __future__ import print_function
from __future__ import division

# Test of multi-agent missions - two agents human in a flat environment.

from builtins import range
import sys
import uuid
from malmoutils import *
from observation import *
from register import *

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
NUM_AGENTS = agents_requested - 1

# Create the rest of the agent hosts - one for each human agent and one to control the observer:
agent_hosts += [MalmoPython.AgentHost() for x in range(1, NUM_AGENTS + 1) ]

# Set up debug output:
for ah in agent_hosts:
    ah.setDebugOutput(DEBUG)    # Turn client-pool connection messages on/off.

if sys.version_info[0] == 2:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
else:
    import functools
    print = functools.partial(print, flush=True)

# Set up a client pool.
# IMPORTANT: If ANY of the clients will be on a different machine, then you MUST
# make sure that any client which can be the server has an IP address that is
# reachable from other machines - ie DO NOT SIMPLY USE 127.0.0.1!!!!
# The IP address used in the client pool will be broadcast to other agents who
# are attempting to find the server - so this will fail for any agents on a
# different machine.
# redifine the client pool each mission
client_pool_array = []
for x in range(10000, 10000 + NUM_AGENTS + 1):
    client_pool_array.append([config['server']['ip'], x])

chat_log = []
num_of_connected_clients = 0
grid_types = set()
for item in config['inventory']:
    grid_types.add(item['type'])
num_missions = config['mission']['num_missions']
for mission_no in range(1, num_missions + 1):
    print("Running mission #" + str(mission_no))
    # Create mission xml - use forcereset if this is the first mission.
    # can add if mission_no == 1 else "false" to prevent reset after first mission
    my_mission = MalmoPython.MissionSpec(getXML(NUM_AGENTS, config), True)

    # Generate an experiment ID for this mission.
    # This is used to make sure the right clients join the right servers -
    # if the experiment IDs don't match, the startMission request will be rejected.
    # In practice, if the client pool is only being used by one researcher, there
    # should be little danger of clients joining the wrong experiments, so a static
    # ID would probably suffice, though changing the ID on each mission also catches
    # potential problems with clients and servers getting out of step.
    experimentID = str(uuid.uuid4())

    # redifine the client pool
    client_pool = MalmoPython.ClientPool()
    for id, port in client_pool_array:
        client_pool.add(MalmoPython.ClientInfo(id, port))

    for i in range(len(agent_hosts)):
        agent_hosts[i].setObservationsPolicy(MalmoPython.ObservationsPolicy.LATEST_OBSERVATION_ONLY)
        agent_hosts[i].setVideoPolicy(MalmoPython.VideoPolicy.LATEST_FRAME_ONLY)
        safeStartMission(agent_hosts[i], my_mission, client_pool, MalmoPython.MissionRecordSpec(), i, experimentID, config, client_pool_array)

    safeWaitForStart(agent_hosts)

    time.sleep(1)
    running = True
    lastEntities = None
    grid = {}
    pressed = False
    # /effect @p haste 1000000 255 true 
    agent_hosts[0].sendCommand("chat /effect @a haste 1000000 255 true")
    # clear any block above the ground
    area_side_size = config['mission']['area_side_size']
    agent_hosts[0].sendCommand("chat /fill -" + str(area_side_size) + " 1 -" + str(area_side_size) + " " + str(area_side_size) + " 100 " + str(area_side_size) + " air")
    while running:
        # TODO : if a new player joins, cick one of the two players and replace it with the new one
        # TODO : if a player leaves, replace it with a new one
        # # waiting to get all players connected
        # if num_of_connected_clients < NUM_AGENTS - 1:
        #     print("Waiting for players to connect...", end="")
        #     while num_of_connected_clients < NUM_AGENTS - 1:
        #         num_of_connected_clients += update_client_pool(client_pool_array,config)
        #         if num_of_connected_clients == NUM_AGENTS - 1:
        #             hasEnded = True
        #             print("All players connected!")
            
        running = False
        for i in range(len(agent_hosts)):
            world_state = agent_hosts[i].peekWorldState()
            if world_state.is_mission_running:
                running = True
                obsv_num = world_state.number_of_observations_since_last_state
                #print("Got " + str(obsv_num) + " observations since last state.")
                if obsv_num > 0:
                    msg = world_state.observations[-1].text
                    ob = json.loads(msg)

                    # get timestamp
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

                    # get agents informations
                    entities = getEntitiesInfo(ob)

                    
                    if config['collect']['chat_history']:
                        # update chat log and get true if a new message has been added
                        change = updateChatLog(ob, chat_log)
                    else:
                        chaty_log = None
                        change = False
                    
                    if config['collect']['agents_inventory']:
                        # get builders inventory
                        inventory = getInventoryInfo(ob , entities)
                    else:
                        inventory = None
                    
                    # update grid and get true if a new block has been added
                    if config['collect']['blocks_in_grid']:
                        change = updateGrid(ob, grid, config['mission']['area_side_size'], grid_types) or change
                    else:
                        grid = None
                    
                    precision = config['collect']['agents_position']['precision']
                    angle_precision = config['collect']['agents_position']['angle_precision']
                    # print to console - if no change since last observation at the precision level, don't bother printing again.
                    if samePosition(entities, lastEntities, precision, angle_precision) and not change:
                        # no change since last observation - don't bother printing again.
                        continue
                    
                    # update lastEntities for next observation
                    lastEntities = entities

                    # clear entities position if not needed
                    if not config['collect']['agents_position']['save']:
                        entities = None

                    # get screenshot path and save screenshot
                    imagePath = None
                    if config['collect']['screenshot']["save"]:
                        folderPath = config['collect']['screenshot']["path"]
                        interval = config['collect']['screenshot']["interval"]
                        imagePath = saveScreenShot(agent_hosts[2], experimentID, timestamp, folderPath, interval)

                    # print to console
                    if config['collect']['log']['console']:
                        printWorldState(timestamp, entities, chat_log, inventory, grid, imagePath)

                    saveTxt = config['collect']['log']['txt']
                    saveJson = config['collect']['log']['json']
                    if saveTxt or saveJson:
                        #make a directory for the mission
                        pathLog = config['collect']['log']['path'] + "/" + str(experimentID) + "-Builder"
                        if not os.path.exists(pathLog):
                            os.makedirs(pathLog)
                        # save those info in txt and json files
                        if saveTxt:
                            writeWorldStateTxt(pathLog, timestamp, entities, chat_log, inventory, grid, imagePath)
                        if saveJson:
                            writeWorldStateJson(pathLog, timestamp, entities, chat_log, inventory, grid, imagePath)
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

    print()
    print("Mission ended")
    # Mission has ended.

    time.sleep(2)