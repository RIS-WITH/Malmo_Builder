from __future__ import print_function
from __future__ import division

# Test of multi-agent missions - two agents human in a flat environment.

from builtins import range
from past.utils import old_div
import MalmoPython
from PIL import Image
import config
import json
import os
import random
import sys
import time
import uuid
import xml.etree.ElementTree as ET
from collections import namedtuple
from operator import add


EntityInfo = namedtuple('EntityInfo', 'x, y, z, yaw, pitch, name, colour, variation, quantity, life')
EntityInfo.__new__.__defaults__ = (0, 0, 0, 0, 0, "", "", "", 1, 1)
BlockInfo = namedtuple('BlockInfo', 'x, y, z, type, colour')
BlockInfo.__new__.__defaults__ = (0, 0, 0, "", "")

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
NUM_ITEMS = NUM_AGENTS * 10

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

def agentName(i):
    return "Agent_" + str(i + 1)

def safeStartMission(agent_host, my_mission, my_client_pool, my_mission_record, role, expId):
    used_attempts = 0
    max_attempts = 5
    print("Calling startMission for role", role)
    while True:
        try:
            # Attempt start:
            agent_host.startMission(my_mission, my_client_pool, my_mission_record, role, expId)
            break
        except MalmoPython.MissionException as e:
            errorCode = e.details.errorCode
            if errorCode == MalmoPython.MissionErrorCode.MISSION_SERVER_WARMING_UP:
                print("Server not quite ready yet - waiting...")
                time.sleep(2)
            elif errorCode == MalmoPython.MissionErrorCode.MISSION_INSUFFICIENT_CLIENTS_AVAILABLE:
                print("Not enough available Minecraft instances running.")
                used_attempts += 1
                if used_attempts < max_attempts:
                    print("Will wait in case they are starting up.", max_attempts - used_attempts, "attempts left.")
                    time.sleep(2)
            elif errorCode == MalmoPython.MissionErrorCode.MISSION_SERVER_NOT_FOUND:
                print("Server not found - has the mission with role 0 been started yet?")
                used_attempts += 1
                if used_attempts < max_attempts:
                    print("Will wait and retry.", max_attempts - used_attempts, "attempts left.")
                    time.sleep(2)
            else:
                print("Other error:", e.message)
                print("Waiting will not help here - bailing immediately.")
                exit(1)
        if used_attempts == max_attempts:
            print("All chances used up - bailing now.")
            exit(1)
    print("startMission called okay.")

def safeWaitForStart(agent_hosts):
    print("Waiting for the mission to start", end=' ')
    start_flags = [False for a in agent_hosts]
    start_time = time.time()
    time_out = 120  # Allow a two minute timeout.
    while not all(start_flags) and time.time() - start_time < time_out:
        states = [a.peekWorldState() for a in agent_hosts]
        start_flags = [w.has_mission_begun for w in states]
        errors = [e for w in states for e in w.errors]
        if len(errors) > 0:
            print("Errors waiting for mission start:")
            for e in errors:
                print(e.text)
            print("Bailing now.")
            exit(1)
        time.sleep(0.1)
        print(".", end=' ')
    if time.time() - start_time >= time_out:
        print("Timed out while waiting for mission to start - bailing.")
        exit(1)
    print()
    print("Mission has started.")

def getXML(reset, generatorString):
    x = z = 10
    # Set up the Mission XML:
    xml = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
    <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
      <About>
        <Summary/>
      </About>
      <ModSettings>
        <MsPerTick>50</MsPerTick>
      </ModSettings>
      <ServerSection>
        <ServerInitialConditions>
          <Time>
            <StartTime>9000</StartTime>
            <AllowPassageOfTime>false</AllowPassageOfTime>
          </Time>
        </ServerInitialConditions>
        <ServerHandlers>
          <FlatWorldGenerator forceReset="'''+reset+'''" generatorString="'''+generatorString+'''" seed=""/>
          <DrawingDecorator>
            <DrawCuboid x1="-'''+str(x)+'''" y1="200" z1="-'''+str(z)+'''" x2="'''+str(x)+'''" y2="226" z2="'''+str(z)+'''" type="dirt"/>
            <DrawBlock x="0" y="236" z="-20" type="fence"/>
          </DrawingDecorator>
          <ServerQuitFromTimeUp description="" timeLimitMs="500000"/>
        </ServerHandlers>
      </ServerSection>
    '''

    # Add an agent section for each robot. Robots run in survival mode.
    # Give each one a wooden pickaxe for protection...

    for i in range(NUM_AGENTS):
      xml += '''<AgentSection mode="Survival">
        <Name>''' + agentName(i) + '''</Name>
        <AgentStart>
          <Placement x="''' + str(random.randint(-x+3,x-3)) + '''" y="228" z="''' + str(random.randint(-z+3,z-3)) + '''"/>
          <Inventory>
            <InventoryObject type="wooden_pickaxe" slot="0" quantity="1"/>
            <InventoryItem slot="1" type="wool" quantity="20" colour="WHITE"/>
            <InventoryItem slot="2" type="wool" quantity="20" colour="RED"/>
            <InventoryItem slot="3" type="wool" quantity="20" colour="GREEN"/>
            <InventoryItem slot="4" type="wool" quantity="20" colour="BLUE"/>
            <InventoryItem slot="5" type="wool" quantity="20" colour="YELLOW"/>
            <InventoryItem slot="6" type="wool" quantity="20" colour="ORANGE"/>
            <InventoryItem slot="7" type="wool" quantity="20" colour="PINK"/>
            <InventoryItem slot="8" type="wool" quantity="20" colour="MAGENTA"/>
            <InventoryItem slot="9" type="wool" quantity="20" colour="CYAN"/>
            <InventoryItem slot="10" type="wool" quantity="20" colour="BROWN"/>
            <InventoryItem slot="11" type="wool" quantity="20" colour="BLACK"/>
            <InventoryItem slot="12" type="wool" quantity="20" colour="GRAY"/>
          </Inventory>
        </AgentStart>
        <AgentHandlers>
          <ContinuousMovementCommands turnSpeedDegs="360"/>
          <ChatCommands/>
          <MissionQuitCommands/>
          <ObservationFromFullStats/>
          <ObservationFromChat/>
          <ObservationFromGrid>
            <Grid name="floor" absoluteCoords="true">
                <min x="'''+str(-x)+'''" y="227" z="'''+str(-z)+'''"/>
                <max x="'''+str(x)+'''" y="248" z="'''+str(z)+'''"/>
            </Grid>
          </ObservationFromGrid>
          <ObservationFromFullInventory flat="false"/>
          <ObservationFromNearbyEntities>
            <Range name="entities" xrange="'''+str(x*3)+'''" yrange="2" zrange="'''+str(z*3)+'''"/>
          </ObservationFromNearbyEntities>
          <ObservationFromRay/>
        </AgentHandlers>
      </AgentSection>'''


    # Add a section for the observer. Observer runs in creative mode.
    # the watcher look 25 degrees down
    xml += '''<AgentSection mode="Creative">
        <Name>TheWatcher</Name>
        <AgentStart>
          <Placement x="0.5" y="238" z="-19.5" pitch="45"/>
        </AgentStart>
        <AgentHandlers>
          <ContinuousMovementCommands turnSpeedDegs="360"/>
          <MissionQuitCommands/>
          <VideoProducer>
            <Width>640</Width>
            <Height>640</Height>
          </VideoProducer>
        </AgentHandlers>
      </AgentSection>'''

    xml += '</Mission>'
    return xml

def samePosition(ents1, ents2, precision=0.1, anglePrecision=30):
    if ents1 == ents2:
        return True
    if ents1 == None or ents2 == None:
        return False
    if len(ents1) != len(ents2):
        return False
    for i in range(len(ents1)):
        e1 = ents1[i]
        e2 = ents2[i]
        if e1.name != e2.name:
            return False
        if abs(e1.yaw - e2.yaw) > anglePrecision:
            return False
        if abs(e1.pitch - e2.pitch) > anglePrecision/5:
            return False
        if abs(e1.x - e2.x) > precision:
            return False
        if abs(e1.y - e2.y) > precision:
            return False
        if abs(e1.z - e2.z) > precision:
            return False
    return True

def compareBlock(blockorg, blockhit):
    # verify is the x y z diffrene is less than 0.6 from the center of the block
    precision = 0.5
    if abs(blockorg.x + 0.5 - blockhit.x) > precision:
        return False
    if abs(blockorg.y + 0.5 - blockhit.y) > precision:
        return False
    if abs(blockorg.z + 0.5 - blockhit.z) > precision:
        return False
    if blockorg.type != blockhit.type:
        return False
    return True

def verfiyGridEntegrity(grid, gridFound, cords):
    # grid is a dictionry of BlockInfo with x y z and type
    # gridFound is a 3d array with key x y z and value BlockInfo
    for key, block in list(grid.items()):
        if gridFound[(block.x + 10) % 21][(block.y - 227) % 21][(block.z + 10) % 21] == None:
            grid.pop(key)
    # check for missing blocks
    for cord in cords:
        key = "block" + str(cord[0]) + "_" + str(cord[1]) + "_" + str(cord[2])
        if key not in grid:
            grid[key] = BlockInfo(cord[0], cord[1], cord[2], "wool")

def removeLastComma(file):
    file.seek(file.tell() - 2, os.SEEK_SET)
    file.truncate()

# Set up a client pool.
# IMPORTANT: If ANY of the clients will be on a different machine, then you MUST
# make sure that any client which can be the server has an IP address that is
# reachable from other machines - ie DO NOT SIMPLY USE 127.0.0.1!!!!
# The IP address used in the client pool will be broadcast to other agents who
# are attempting to find the server - so this will fail for any agents on a
# different machine.
# TODO - make it possible to separate the client pool and server on different machines...
client_pool = MalmoPython.ClientPool()
for x in range(10000, 10000 + NUM_AGENTS + 1):
    client_pool.add( MalmoPython.ClientInfo('127.0.0.1', x) )

chat_log = []
num_missions = 3
for mission_no in range(1, num_missions + 1):
    print("Running mission #" + str(mission_no))
    # Create mission xml - use forcereset if this is the first mission.
    # generate a simple world
    generatorStr = "3;7,220*1,5*3,2;3;,biome_1"
    my_mission = MalmoPython.MissionSpec(getXML("true" if mission_no == 1 else "false", generatorStr), True)

    # Generate an experiment ID for this mission.
    # This is used to make sure the right clients join the right servers -
    # if the experiment IDs don't match, the startMission request will be rejected.
    # In practice, if the client pool is only being used by one researcher, there
    # should be little danger of clients joining the wrong experiments, so a static
    # ID would probably suffice, though changing the ID on each mission also catches
    # potential problems with clients and servers getting out of step.

    # Note that, in this sample, the same process is responsible for all calls to startMission,
    # so passing the experiment ID like this is a simple matter. If the agentHosts are distributed
    # across different threads, processes, or machines, a different approach will be required.
    # (Eg generate the IDs procedurally, in a way that is guaranteed to produce the same results
    # for each agentHost independently.)
    # TODO : make this more robust.
    experimentID = str(uuid.uuid4())

    for i in range(len(agent_hosts)):
        agent_hosts[i].setObservationsPolicy(MalmoPython.ObservationsPolicy.LATEST_OBSERVATION_ONLY)
        agent_hosts[i].setVideoPolicy(MalmoPython.VideoPolicy.LATEST_FRAME_ONLY)
        safeStartMission(agent_hosts[i], my_mission, client_pool, MalmoPython.MissionRecordSpec(), i, experimentID)

    safeWaitForStart(agent_hosts)
    time.sleep(1)
    running = True
    lastEntities = None
    grid = {}
    inventory = {}
    pressed = False
    while running:
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
                    """ Generate a txt file for each timestamp :
                    --------------------
                    [Timestamp] 2018-03-30 18:47:02
                    [Builder Position] (x, y, z): (-3.97713906986, 1.0, -1.8846418295) (yaw, pitch): (2.9999986, 38.249992)
                    [Screenshot Path] 116313-Builder-putdown.png

                    [Chat Log]
                        <Builder> Mission has started.
                        <Builder> hello. what are we building this time?
                        <Architect> hello builder, i will tell you this. it appears we are creating a belltower. but first i will start with step by step instructions. we will start with green blocks
                        <Architect> please start with 8 green blocks extending straight up. this will need to be placed as far right as you can, preferably centered along the other axis
                        <Builder> here?

                    [Blocks In Grid]
                        Type: cwc_minecraft_green_rn  Absolute (x, y, z): (-5, 1, 0)  Perspective (x, y, z): -0.893957672349, 1.26889164072, 1.60958183519)

                    --------------------"""
                    # get timestamp
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                    # get builder 1 and 2 position
                    if "entities" in ob:
                        entities = [EntityInfo(k["x"], k["y"], k["z"], k["yaw"], k["pitch"], k["name"]) for k in ob["entities"]]
                    # order entities by name
                    entities = sorted(entities, key=lambda x: x.name)
                    # get chat log
                    added = False
                    if "Chat" in ob:
                        if len(chat_log) == 0 or chat_log[-1] != ob["Chat"]:
                            chat_log.append(ob["Chat"])
                            added = True
                    
                    # get builder inventory
                    if "inventory" in ob:
                        if len(inventory) == 0:
                            for e in entities:
                                inventory[e.name] = ob["inventory"]
                        else:
                            inventory[ob["Name"]] = ob["inventory"]
                    
                    # method two point one :
                    # get blocks using ObservationFromGrid absolute position
                    if "floor" in ob and u"LineOfSight" in ob:
                        floor = ob["floor"]
                        los = ob["LineOfSight"]

                        # transform the grid to a 3d array
                        # floor is of 21x21x21
                        gridSize = 21
                        gridFound = [[[None for k in range(gridSize)] for j in range(gridSize)] for i in range(gridSize)]
                        cords= []
                        for i, block_type in enumerate(floor):
                            x = i % gridSize
                            z = (i // gridSize) % gridSize
                            y = (i // gridSize // gridSize) % gridSize
                            xa = x - 10
                            ya = y + 227
                            za = z - 10
                            if block_type == "wool":
                                gridFound[x][y][z] = block_type
                                cords.append([xa, ya, za])
                            # add color to block
                            if los[u'hitType'] == "block" and los[u'inRange'] and los[u'type'] == "wool":
                                blockGrid = BlockInfo(xa, ya, za, block_type, "")
                                blockLos = BlockInfo(los[u'x'], los[u'y'], los[u'z'], los[u'type'], los[u'colour'])
                                block = BlockInfo(xa, ya, za, block_type, blockLos.colour)
                                key = "block" + str(block.x) + "_" + str(block.y) + "_" + str(block.z)
                                # if not already a similar blockInfo in grid then add it
                                if key not in grid and compareBlock(blockGrid, blockLos):
                                    grid[key] = block
                                    added = True
                        verfiyGridEntegrity(grid, gridFound, cords)
                    
                    # TODO : add a RecordHumanCommand to track put and destroy commands
                    # print to console - if no change since last observation at the precision level, don't bother printing again.
                    if samePosition(entities, lastEntities) and not added:
                        # no change since last observation - don't bother printing again.
                        continue
                    lastEntities = entities
                    # get screenshot path
                    observer = agent_hosts[2].getWorldState()
                    if observer.number_of_video_frames_since_last_state > 0:
                        frame = observer.video_frames[-1]
                        image = Image.frombytes('RGB', (frame.width, frame.height), bytes(frame.pixels) )
                        # remove unwanted charecters from timestamp
                        timestring = str(timestamp).replace(":", "-")
                        timeString = timestring.replace(" ", "_")
                        #make a directory for the mission
                        if not os.path.exists("./screenshots"):
                            os.makedirs("./screenshots")
                        imagePrePath = "./screenshots/" + str(experimentID) + "-Builder"
                        if not os.path.exists(imagePrePath):
                            os.makedirs(imagePrePath)
                        imagePath = imagePrePath + "/" + str(timestamp) + "-Builder.png"
                        image.save(str(imagePath))

                    print("--------------------")
                    print("[Timestamp] " + str(timestamp))
                    print("[Builder Position] ")
                    for entity in entities:
                        print("\t" + str(entity.name) + " (x, y, z): (" + str(entity.x) + ", " + str(entity.y) + ", " + str(entity.z) + ") (yaw, pitch): (" + str(entity.yaw) + ", " + str(entity.pitch) + ")"  )
                    print("[Screenshot Path] " + imagePath)
                    print("[Chat Log]")
                    for chat in chat_log:
                        print("\t" + str(chat))
                    print("[Blocks In Inventory] " + str(inventory))
                    print("[Blocks In Grid] " + str(grid))


                    # save those info in txt and json files
                    #make a directory for the mission
                    pathLog = "./log/" + str(experimentID) + "-Builder"
                    if not os.path.exists(pathLog):
                        os.makedirs(pathLog)
                    # open a file in append mode in texts folder named with mission id
                    file = open(pathLog + "/missionLog-Builder.txt", "a")
                    # write the data to file
                    file.write("--------------------\n")
                    file.write("[Timestamp] " + str(timestamp) + "\n")
                    file.write("[Builder Position] \n")
                    for entity in entities:
                        file.write("\t" + str(entity.name) + " (x, y, z): (" + str(entity.x) + ", " + str(entity.y) + ", " + str(entity.z) + ") (yaw, pitch): (" + str(entity.yaw) + ", " + str(entity.pitch) + ")\n"  )
                    file.write("[Screenshot Path] " + imagePath + "\n")
                    file.write("[Chat Log]\n")
                    for chat in chat_log:
                        file.write("\t" + str(chat) + "\n")
                    file.write("[Builders Inventory] \n")
                    for agent_name, items in list(inventory.items()):
                        file.write("\t" + str(agent_name) + "\n")
                        for item in items:
                            file.write("\t\t" + str(item) + "\n")
                    file.write("[Blocks In Grid] \n")
                    for key, block in list(grid.items()):
                        file.write("\t" + str(block) + "\n")
                    # close the file
                    file.close()

                    #JSON file
                    # open a file in append mode in texts folder named with mission id and read it
                    file = open(pathLog +"/missionLog-Builder.json" , "a")
                    # write the data to file
                    file.write("{\n")
                    file.write("\t\"timestamp\": \"" + str(timestamp) + "\",\n")
                    file.write("\t\"builder_position\": [\n")
                    for entity in entities:
                        file.write("\t\t{\n")
                        file.write("\t\t\t\"name\": \"" + str(entity.name) + "\",\n")
                        file.write("\t\t\t\"x\": " + str(entity.x) + ",\n")
                        file.write("\t\t\t\"y\": " + str(entity.y) + ",\n")
                        file.write("\t\t\t\"z\": " + str(entity.z) + ",\n")
                        file.write("\t\t\t\"yaw\": " + str(entity.yaw) + ",\n")
                        file.write("\t\t\t\"pitch\": " + str(entity.pitch) + "\n")
                        file.write("\t\t},\n")
                    if len(entities) > 0:
                        removeLastComma(file)
                    file.write("\t],\n")
                    file.write("\t\"screenshot_path\": \"" + imagePath + "\",\n")
                    file.write("\t\"chat_log\": [\n")
                    for chat in chat_log:
                        file.write("\t\t\"" + str(chat) + "\",\n")
                    if len(chat_log) > 0:
                        removeLastComma(file)
                    file.write("\t],\n")
                    file.write("\t\"builders_inventory\": [\n")
                    for agent_name, items in list(inventory.items()):
                        file.write("\t\t{\n")
                        file.write("\t\t\t\"name\": \"" + str(agent_name) + "\",\n")
                        file.write("\t\t\t\"items\": [\n")
                        for item in items:
                            file.write("\t\t\t\t\"" + str(item) + "\",\n")
                        if len(items) > 0:
                            removeLastComma(file)
                        file.write("\t\t\t]\n")
                        file.write("\t\t},\n")
                    if len(inventory) > 0:
                        removeLastComma(file)
                    file.write("\t],\n")
                    file.write("\t\"blocks_in_grid\": [\n")
                    for key, block in list(grid.items()):
                        file.write("\t\t{\n")
                        file.write("\t\t\t\"name\": \"" + str(block.colour) + " " + str(block.type) + "\",\n")
                        file.write("\t\t\t\"x\": " + str(block.x) + ",\n")
                        file.write("\t\t\t\"y\": " + str(block.y) + ",\n")
                        file.write("\t\t\t\"z\": " + str(block.z) + "\n")
                        file.write("\t\t},\n")
                    if len(grid) > 0:
                        removeLastComma(file)
                    file.write("\t]\n")
                    file.write("}\n")
                    # close the file
                    file.close()


                    file = open(pathLog + "/missionLog-v2-Builder.json", "a")
                    # if empty, write the first line
                    if os.stat(pathLog + "/missionLog-v2-Builder.json").st_size == 0:
                        file.write("{\n")
                        file.write("\t\"WorldStates\": [\n")
                    # write the world state
                    file.write("\t\t{\n")
                    # use entites position
                    for ent in entities:
                        file.write("\t\t\t\""+ ent.name + "Position\": {\n")
                        file.write("\t\t\t\t\"X\": " + str(ent.x) + ",\n")
                        file.write("\t\t\t\t\"Y\": " + str(ent.y) + ",\n")
                        file.write("\t\t\t\t\"Z\": " + str(ent.z) + ",\n")
                        file.write("\t\t\t\t\"Yaw\": " + str(ent.yaw) + ",\n")
                        file.write("\t\t\t\t\"Pitch\": " + str(ent.pitch) + "\n")
                        file.write("\t\t\t},\n")
                    # write the chat history
                    file.write("\t\t\t\"ChatHistory\": [\n")
                    for chat in chat_log:
                        file.write("\t\t\t\t\"" + str(chat) + "\",\n")
                    # remove the last comma if there is at - 2
                    if len(chat_log) > 0:
                        removeLastComma(file)
                    file.write("\n")
                    file.write("\t\t\t],\n")
                    # write the timestamp
                    file.write("\t\t\t\"Timestamp\": \"" + str(timestamp) + "\",\n")
                    # write the blocks in grid
                    file.write("\t\t\t\"BlocksInGrid\": [\n")
                    for key, block in list(grid.items()):
                        file.write("\t\t\t\t{\n")
                        file.write("\t\t\t\t\t\"X\": " + str(block.x) + ",\n")
                        file.write("\t\t\t\t\t\"Y\": " + str(block.y) + ",\n")
                        file.write("\t\t\t\t\t\"Z\": " + str(block.z) + ",\n")
                        file.write("\t\t\t\t\t\"Type\": \"" + block.type + "\",\n")
                        file.write("\t\t\t\t\t\"Colour\": \"" + block.colour + "\"\n")
                        file.write("\t\t\t\t},\n")
                    # remove the last comma
                    if len(grid) > 0:
                        removeLastComma(file)
                    file.write("\n")
                    file.write("\t\t\t],\n")
                    # write the builder inventory
                    file.write("\t\t\t\"BuilderInventory\": [\n")
                    for key, items in list(inventory.items()):
                        file.write("\t\t\t\t{\n")
                        file.write("\t\t\t\t\t\"Name\": \"" + key + "\",\n")
                        file.write("\t\t\t\t\t\"Items\": [\n")
                        for item in items:
                            # write the item index type colour and quantity
                            file.write("\t\t\t\t\t\t{\n")
                            file.write("\t\t\t\t\t\t\t\"Index\": " + str(item['index']) + ",\n")
                            file.write("\t\t\t\t\t\t\t\"Type\": \"" + item['type'] + "\",\n")
                            if 'colour' in item:
                                file.write("\t\t\t\t\t\t\t\"Colour\": \"" + str(item['colour']) + "\",\n")
                            file.write("\t\t\t\t\t\t\t\"Quantity\": " + str(item['quantity']) + "\n")
                            file.write("\t\t\t\t\t\t},\n")
                        # remove the last comma
                        if (len(items) > 0):
                            removeLastComma(file)
                        file.write("\t\t\t\t\t]\n")
                        file.write("\t\t\t\t},\n")
                    # remove the last comma
                    if len(inventory) > 0:
                        removeLastComma(file)
                    file.write("\t\t\t],\n")
                    # write the screenshots
                    file.write("\t\t\t\"Screenshots\": {\n")
                    file.write("\t\t\t\t\"Path\": \"" + str(imagePath) + "\",\n")
                    file.write("\t\t\t\t\"Timestamp\": \"" + str(timestamp) + "\"\n")
                    file.write("\t\t\t}\n")
                    file.write("\t\t},\n")
                    # close the file
                    file.close()
        time.sleep(0.05)       
    # end the json file
    file = open(pathLog + "/missionLog-v2-Builder.json", "a")
    # remove the last comma
    removeLastComma(file)
    # end the json file
    file.write("\n")
    file.write("\t]\n")
    file.write("}\n")
    # close the file
    file.close()

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
