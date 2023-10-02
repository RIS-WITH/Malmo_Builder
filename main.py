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
        self.mission = None
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
        print("playing with ", self.num_distant_agents, " distant agents")
        # remove the ADMIN(observer) from the number of agents and the number of distant agents
        self.num_local_agents = self.agents_requested - 1 - self.num_distant_agents
        print("number of agents is ", self.num_local_agents)

        # Create the rest of the agent hosts - one for each human agent and one to control the observer for now one local and 
        # other waiting for connection:
        self.agent_hosts += [MalmoPython.AgentHost() for _ in range(1, self.num_local_agents + 2) ]
        print("agent host is ", self.agent_hosts)

        # Set up debug output:
        for ah in self.agent_hosts:
            ah.setDebugOutput(self.DEBUG)    # Turn client-pool connection messages on/off.

        # Set up a client pool.
        # The IP address used in the client pool will be broadcast to other agents who
        # are attempting to find the server
        print("agents requested is ", self.agents_requested)
        self.client_pool_array = []
        for x in range(10000, 10000 + self.num_local_agents + 2):
            self.client_pool_array.append([config['server']['ip'], x])
        for x in range(1, self.num_distant_agents + 1):
            dist_ip = config["agents"]["builder_" + str(x)]["ip"]
            self.client_pool_array.append([dist_ip, 10000])
        print("client pool ", self.client_pool_array)

        # A log of all chats in the game
        self.chat_log = [] 

        #get the number of missions to run
        self.num_missions = config['mission']['num_missions']

    def run(self):
        # Create and run the missions:
        for mission_no in range(0, self.num_missions + 1):
            if(mission_no != 0):
                if([config['server']['ip'], 10001] in self.client_pool_array):
                    self.client_pool_array.remove([config['server']['ip'], 10001])
                    self.agent_hosts.remove(self.agent_hosts[1])
            self.mission = Mission(config, self.agent_hosts, mission_no, self.client_pool_array, self.agents_requested - 1, self.num_distant_agents, self.chat_log)
            self.mission.start()
            self.mission.run(debug=self.DEBUG)           
            self.chat_log, self.client_pool_array, self.agent_hosts, self.num_local_agents = self.mission.end()

if __name__ == '__main__':
    game = Main()
    game.run()

