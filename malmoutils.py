import os
import MalmoPython
import time
import random
import json
# read config file
with open('config.json') as config_file:
  config = json.load(config_file)

connected_users_ips = {}

def find_nfs_file(path):
   # search for the hidden file starting with .nfs and return the latest one
  files = []
  for root, dirs, files in os.walk(path):
      for file in files:
          if file.startswith(".nfs"):
              files.append(os.path.join(root, file))
  if len(files) > 0:
    return files[-1]
  else:
    return None
  
def latest_file(path):
  # find latest.log
  file_name = "latest.log"
  return os.path.join(path, file_name)

def get_connected_agents_ips(log_file_path):
  """
    [11:38:00] [Client thread/INFO]: [CHAT] §l281...
    [11:38:01] [Server thread/INFO]: Player703[/140.93.7.238:56370] logged in with entity id 313 at (-25.5, 227.0, 1075.5)
    [11:38:01] [Server thread/INFO]: Player703 joined the game
    [11:38:01] [Client thread/INFO]: [CHAT] Player703 joined the game
  """
  with open(log_file_path) as log_file:
    # just read the last two lines
    lines = log_file.readlines()[-10:]
    for line in lines:
      # if "joined the game" in line:
      #   print("line: ", line) 
      #   username = line.split("]: ")[1].split(" joined")[0]
      #   if username == config['agents']['builder_1']['name'] or username == config['agents']['builder_2']['name'] or username == config['agents']['builder_3']['name']:
      #     return 1  
      if "logged in with entity id" in line and "ADMIN" not in line:
        line = line.split("]: ")[1]
        #print("line: ", line)
        username = line.split("[/")[0]
        ip, port = line.split("[/")[1].split("]")[0].split(":")
        if config["server"]["ip"] != ip:
          connected_users_ips[username] = [ip, int(port)]
          print("player logged: ", username)
      if "left the game" in line:
        username = line.split("]: ")[1].split(" left")[0]
        if username in connected_users_ips:
          del connected_users_ips[username]
    return connected_users_ips
  
def update_client_pool(client_pool_array, config):
  num_connected_users = 0
  # find .nfs file at server['path'] and save its name
  # log file path
  log_file_path = latest_file(config['server']['log_path'])

  # get the ips of the other users
  agents = get_connected_agents_ips(log_file_path)

  # if agents == 1:
  #   return 1

  for key, value in agents.items():
    ## uncomment this if you want the port that was given by log file
    #temp = [value[0], value[1]]
    # to fix not adding the new player to the client pool
    print("key: ", key, "value: ", value)
    temp = [value[0], 10000]
    if temp not in client_pool_array:
      client_pool_array.pop(1)
      client_pool_array.append(temp)
      num_connected_users += 1
      config['agents']['builder_' + str(num_connected_users)]['name'] = key
      print ("adding player to the client pool: ", key)
  return num_connected_users

def agentName(i, config=config):
    agents = config["agents"]
    i += 1
    return agents["builder_" + str(i)]["name"]

def safeStartMission(agent_host, my_mission, my_client_pool, my_mission_record, role, expId, config, client_pool_array):
    used_attempts = 0
    max_attempts = 100
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
                    # #search for new clients
                    # if update_client_pool(client_pool_array, config):
                    #   print("New clients found, will retry now.")
                    #   # update my_client_pool
                    #   my_client_pool = MalmoPython.ClientPool()
                    #   for client in client_pool_array:
                    #     my_client_pool.add(MalmoPython.ClientInfo(client[0], client[1]))
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

def getXML(NUM_AGENTS, config):
    # Set up the Mission XML:
    mission = config["mission"]
    x = z = (mission["area_side_size"] -1) // 2
    y = 226
    zdelta = 10
    reset = "true" if mission["force_reset"] else "false"
    xml = '''<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
    <Mission xmlns="http://ProjectMalmo.microsoft.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
      <About>
        <Summary>'''+ mission["name"] +': '+ mission["summary"] + '''</Summary>
      </About>
      <ModSettings>
        <MsPerTick>'''+str(mission['ms_per_tick'])+'''</MsPerTick>
      </ModSettings>
      <ServerSection>
        <ServerInitialConditions>
          <Time>
            <StartTime>''' + str(mission['time_of_day']) + '''</StartTime>
            <AllowPassageOfTime>''' + str(bool(mission['allow_time_passage'])).lower() + '''</AllowPassageOfTime>
          </Time>
          <Weather>''' + str(mission['weather']) + '''</Weather>
        </ServerInitialConditions>
        <ServerHandlers>
          <FlatWorldGenerator forceReset="'''+reset+'''" generatorString="'''+mission['flat_world_generator_str']+'''" seed=""/>
          <DrawingDecorator>
            <DrawCuboid x1="-'''+str(x)+'''" y1="200" z1="-'''+str(z)+'''" x2="'''+str(x)+'''" y2="226" z2="'''+str(z)+'''" type="bedrock"/>
            <DrawBlock x="0" y="'''+str(y + x)+'''" z="'''+str(-z - zdelta)+'''" type="fence"/>
          </DrawingDecorator>
          <ServerQuitFromTimeUp description="'''+ str(mission['quit_from_time_up_description']) +''''" timeLimitMs="'''+ str(mission['time_limit']) +'''"/>
        </ServerHandlers>
      </ServerSection>
    '''

    # Add a section for the observer. Observer runs in creative mode.
    # the watcher look 25 degrees down
    xml += '''<AgentSection mode="Creative">
        <Name>ADMIN</Name>
        <AgentStart>
          <Placement x="0.5" y="'''+str(y + x + 2)+'''" z="'''+str(-z - zdelta + 0.5)+'''" pitch="45"/>
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
    
    # inventory 
    inventory_text = ""
    for item in config['inventory']:
        inventory_text += "\n"
        inventory_text += "\t" * 6           
        inventory_text += "<InventoryItem slot=\"" + str(item["slot"]) + "\" type=\"" + item["type"] + "\" quantity=\"" + str(item["quantity"]) + "\""
        if "color" in item:
          inventory_text += " colour=\"" + item["color"].upper() + "\""
        inventory_text += "/>"

    # Add an agent section for each robot. Robots run in survival mode.
    # Give each one a wooden pickaxe for protection...

    agent = config["agents"]
    for i in range(NUM_AGENTS):
      xml += '''<AgentSection mode="Survival">
        <Name>''' + agentName(i, config) + '''</Name>
        <AgentStart>'''
      if(agent['builder_'+ str(i+1)]['placement'] == 'random'):
        xml += '''<Placement x="''' + str(random.randint(-x+3,x-3)) + '''" y="228" z="''' + str(random.randint(-z+3,z-3)) + '''"/>'''
      else:
        xml += '''<Placement x="''' + str(agent['builder_' + str(i+1)]['placement'][0]) + '''" y="228" z="''' + str(agent['builder_'+ str(i+1)]['placement'][1]) + '''"/>'''
      xml += '''
          <Inventory>''' + inventory_text + '''
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
                <max x="'''+str(x)+'''" y="'''+str(277 + mission["area_side_size"])+'''" z="'''+str(z)+'''"/>
            </Grid>
          </ObservationFromGrid>
          <ObservationFromFullInventory flat="false"/>
          <ObservationFromNearbyEntities>
            <Range name="entities" xrange="'''+str(x*3)+'''" yrange="2" zrange="'''+str(z*3)+'''"/>
          </ObservationFromNearbyEntities>
          <ObservationFromRay/>
        </AgentHandlers>
      </AgentSection>'''

    xml += '</Mission>'
    return xml