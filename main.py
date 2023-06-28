from __future__ import print_function
from __future__ import division

# multi-agent missions - two agents human in a flat environment.
from builtins import range
import sys
from malmoutils import MalmoPython, config
from mission import Mission

# enure that print statements flush immediately and are not buffered
if sys.version_info[0] == 2:
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)  # flush print output immediately
else:
    import functools
    print = functools.partial(print, flush=True)
            
class Main:
    def __init__(self):
        # Create one agent host for parsing:
        self.agent_hosts = [MalmoPython.AgentHost()]

        # Parse the command-line options:
        self.agent_hosts[0].addOptionalFlag( "debug,d", "Display debug information.")
        self.agent_hosts[0].addOptionalIntArgument("agents,n", "Number of agents to use, including observer.", 3)
        try:
            self.agent_hosts[0].parse( sys.argv )
        except RuntimeError as e:
            print('ERROR:',e)
            print(self.agent_hosts[0].getUsage())
            exit(1)
        if self.agent_hosts[0].receivedArgument("help"):
            print(self.agent_hosts[0].getUsage())
            exit(0)

        # Set up debug output:
        self.DEBUG = self.agent_hosts[0].receivedArgument("debug")
        self.INTEGRATION_TEST_MODE = self.agent_hosts[0].receivedArgument("test")
        self.agents_requested = self.agent_hosts[0].getIntArgument("agents")
        self.num_distant_agents = config["agents"]["num_distant_agents"]
        # remove the ADMIN(observer) from the number of agents and the number of distant agents
        self.NUM_AGENTS = self.agents_requested - 1 - self.num_distant_agents

        # Create the rest of the agent hosts - one for each human agent and one to control the observer for now one local and other waiting for connection:
        self.agent_hosts += [MalmoPython.AgentHost() for _ in range(1, self.NUM_AGENTS + 1) ]

        # Set up debug output:
        for ah in self.agent_hosts:
            ah.setDebugOutput(self.DEBUG)    # Turn client-pool connection messages on/off.

        # Set up a client pool.
        # The IP address used in the client pool will be broadcast to other agents who
        # are attempting to find the server
        self.client_pool_array = []
        for x in range(10000, 10000 + self.NUM_AGENTS + 1):
            self.client_pool_array.append([config['server']['ip'], x])

        # A log of all chats in the game
        self.chat_log = [] 

        #get the number of missions to run
        self.num_missions = config['mission']['num_missions']

    def run(self):
        # Create and run the missions:
        for mission_no in range(0, self.num_missions + 1):
            mission = Mission(config, self.agent_hosts, mission_no, self.client_pool_array, self.NUM_AGENTS, self.chat_log)
            mission.start()
            mission.run(debug=self.DEBUG)           
            mission.end()

if __name__ == '__main__':
    game = Main()
    game.run()

