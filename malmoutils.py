import MalmoPython
import time
import random
import json
# read config file
with open('config.json') as config_file:
    config = json.load(config_file)

def agentName(i):
    agents = config["agents"]
    i += 1
    return agents["builder_" + str(i)]["name"]

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

def getXML(reset, generatorString, NUM_AGENTS):
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
            <DrawCuboid x1="-'''+str(x)+'''" y1="200" z1="-'''+str(z)+'''" x2="'''+str(x)+'''" y2="226" z2="'''+str(z)+'''" type="bedrock"/>
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
            <InventoryItem slot="0" type="wool" quantity="20" colour="GRAY"/>
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
          </Inventory>
        </AgentStart>
        <AgentHandlers>
          <ContinuousMovementCommands turnSpeedDegs="360"/>
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
          <ChatCommands/>
          <MissionQuitCommands/>
          <VideoProducer>
            <Width>640</Width>
            <Height>640</Height>
          </VideoProducer>
        </AgentHandlers>
      </AgentSection>'''

    xml += '</Mission>'
    return xml