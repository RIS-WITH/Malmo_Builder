from __future__ import print_function
from __future__ import division

# multi-agent missions - two agents human in a flat environment.
from builtins import range
import sys
from malmoutils import MalmoPython, config
from mission import Mission

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

#get the number of missions to run
num_missions = config['mission']['num_missions']

for mission_no in range(0, num_missions + 1):
    mission = Mission(config, agent_hosts, mission_no, DEBUG, client_pool_array, NUM_AGENTS, chat_log)
    mission.start()
    mission.run()
    mission.end()