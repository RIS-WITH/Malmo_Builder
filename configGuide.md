# how to use config.json file
## config.json file is used to set the parameters of the malmo builder
the parameters are:
## mission
### name
the name of the mission
### summary
the summary of the mission
### num_missions
the number of missions
### ms_per_tick
the number of milliseconds per tick
### time_of_day
the time of day of minecraft ranging from 0 to 24000
| sunrise | noon | sunset | midnight |
| 1       | 6000 | 12000  | 18000    |
### allow_time_passage
whether allow time passage
### flat_world_generator_str
the string of flat world generator
we can use this website to generate the string: https://www.chunkbase.com/apps/superflat-generator
### time_limit
the time limit of the mission
### quit_from_time_up_description
the description of the mission when time up
### force_reset
whether force reset the mission .. if true, the mission will be reseted after the time limit which mean changing the port of the mission which will cause the agent to be disconnected breifly
### area_side_size
the side size of the area since it is a square area
### weather
the weather of the mission
| clear | rain | thunder | snow |

## agents
### num_distant_agents
the number of players who play in distant machines
### name
the name of the agent
### placement
the placement of the agent
| random | [x, z] |

## inventory
*cururently, we only support wool*
### slot
the slot of the inventory
### type
the type of the inventory
### quantity
the quantity of the inventory
### color
the color of the inventory

## server
*not employed yet (only localy)*
### ip
the ip of the server

## collect
### agents_position
whether collect the agents' position
#### save
whether save the data
#### precision
the precision of the position
#### angle_precision
the angle precision of the position

### agents_inventory
whether collect the agents' inventory
### chat_history
whether collect the chat history
### blocks_in_grid
whether collect the blocks in the grid
### screenshot
whether collect the screenshot
#### save
whether save the data
#### interval
the interval of the screenshot
| every_n_seconds | every_n_minute |  every_move | every_second | every_minute | every_hour | 
note that the interval is a secondry condition, the primary condition is the agent's movement

### log
whether collect the log
#### txt
whether collect the txt log
#### json
whether collect the json log
#### console
whether to print the log in the console


