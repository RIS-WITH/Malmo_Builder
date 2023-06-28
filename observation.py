from collections import namedtuple

EntityInfo = namedtuple('EntityInfo', 'x, y, z, yaw, pitch, name, color, variation, quantity, life')
EntityInfo.__new__.__defaults__ = (0, 0, 0, 0, 0, "", "", "", 1, 1)
BlockInfo = namedtuple('BlockInfo', 'x, y, z, type, color')
BlockInfo.__new__.__defaults__ = (0, 0, 0, "", "")

def update_entities_info(observations, queue_entities, last_entities=None):
    # get either builder or architect position one at a time and use the last one for the missing one
    if "Name" in observations:
        entities = [EntityInfo(observations["XPos"], observations["YPos"], observations["ZPos"], observations["Yaw"], observations["Pitch"], observations["Name"])]
    if last_entities is not None:
        for e in last_entities:
            # if un entity is missing, add it
            if e.name not in [k.name for k in entities]:
                entities.append(e)
    queue_entities.put(sorted(entities, key=lambda x: x.name))

def update_chat_log(observations, chat_log, config):
    if "Chat" in observations:
        return read_observation_chat_log(observations, chat_log)
    else:
        return read_server_chat_log(chat_log, config)
    
def read_server_chat_log(chat_log, config):
    # read config file log path
    with open(config['server']['log_path'], encoding='utf-8', errors='ignore') as log_file:
        # if the log file contains two lines
        if len(log_file.readlines()) > 1:
            # just read the last two lines
            lines = log_file.readlines()[-2:]
            for line in lines:
                # if it has chat in it
                if "]: [CHAT]" in line and (config["agents"]["builder_1"]["name"] in line or config["agents"]["builder_2"]["name"] in line) and "ADMIN" not in line :
                    # get the chat message
                    message = line.split("]: [CHAT] ")[1]
                    # remove the \n
                    message = message[:-1]
                    if (len(chat_log) < 3 and message not in chat_log) or message not in chat_log[-3:]:
                        chat_log.append(message)
                        return True
        return False
    
    
def read_observation_chat_log(observations, chat_log):
    if "Chat" in observations:
        chats = observations["Chat"]
        # transform to list if it is not
        if type(chats) is not list:
            chats = [chats]
        for chat in chats:
            # ignore ADMIN messages
            if "ADMIN" not in chat and (len(chat_log) == 0 or chat_log[-1] != chat):
                chat_log.append(chat)
                return True
    return False

def get_inventory_info(observation, entities):
    inventory = {}
    if "inventory" in observation:
        if len(inventory) == 0:
            for e in entities:
                inventory[e.name] = observation["inventory"]
        else:
            inventory[observation["Name"]] = observation["inventory"]
    return inventory

def same_position(entities1, entities2, precision=0.1, angle_precision=400):
    # if the length equals 1 then return true since we need two agents
    if len(entities1) == 1:
        return True
    # compare the position of the agents from two observations
    if entities1 == entities2:
        return True
    if entities1 == None or entities2 == None:
        return False
    if len(entities1) != len(entities2):
        return False
    # compare each entity position and orientation using the precision
    for i in range(len(entities1)):
        if not same_position_entity(entities1[i], entities2[i], precision, angle_precision):
            return False
    return True

def same_position_entity(entity1, entity2, precision, angle_precision):
    if entity1.name != entity2.name:
        return False
    if abs(entity1.yaw - entity2.yaw) > angle_precision * 2:
        return False
    if abs(entity1.pitch - entity2.pitch) > angle_precision/11:
        return False
    if abs(entity1.x - entity2.x) > precision:
        return False
    if abs(entity1.y - entity2.y) > precision:
        return False
    if abs(entity1.z - entity2.z) > precision:
        return False
    return True

def get_block_coordinates(i, grid_size, radius):
    x = i % grid_size
    y = i // grid_size // grid_size
    z = (i // grid_size) % grid_size
    return (x - radius), (y + 227), (z - radius)

def get_block_1d_coordinates(x, y, z, grid_size, radius):
    # do the inverse of getBlockCoordinates
    return (x + radius) + (y - 227) * grid_size * grid_size + (z + radius) * grid_size

def compare_block(block_original, block_hit):
    precision = 1.49
    if abs(block_original.x - block_hit.x) > precision or abs(block_original.y - block_hit.y) > precision or abs(block_original.z - block_hit.z) > precision:
        return False
    # compare the type of the block
    if block_original.type != block_hit.type:
        return False
    return True

def update_grid(observation, grid, side_size, grid_types, change_event):
    change = False
    # get blocks using ObservationFromGrid absolute position
    if "floor" in observation:
        floor = observation["floor"]
        # xzToCenter is the distance from the center of the grid to the edge
        radius = (side_size - 1) // 2
        
        # grid size is the side size of the area we are looking at
        grid_size = side_size
        if u"LineOfSight" in observation:
            los = observation["LineOfSight"]
            # check if there is a change in the grid
            change = grid_check(grid, los, floor, grid_size, radius, grid_types)
        # check all blocks we are not looking at are in grid are in the observation  
        change = check_grid_integrity(grid, floor, grid_size, radius, grid_types) or change
    if change:
        change_event.set()

def grid_check(grid, los, floor, grid_size, radius, grid_types):
    # check all blocks in line of sight are in grid and then check all blocks we are not looking at are in grid are in the observation
    cords = get_los_blocks(los, grid_types)
    if cords == []:
        return False
    
    # transform these 3d coordinates to 1d
    index = [int(get_block_1d_coordinates(x, y, z, grid_size, radius)) for x, y, z in cords]
    for i in index:
        # see if the index i in the 1d array floor
        if i < len(floor):
            # get the block type
            block_type = floor[i]
            # get the 3d coordinates of the block
            x, y, z = get_block_coordinates(i, grid_size, radius)
            # create a blockInfo using floor info
            block_grid = BlockInfo(x, y, z, block_type, "")
            
            # make a unique key for the block
            key = "block" + str(block_grid.x) + "_" + str(block_grid.y) + "_" + str(block_grid.z)
                
            check = block_check(grid, los, block_grid, key, grid_types)
            
            # if blockCheck is -1 then the block is not in the grid and not in line of sight
            if check == -1:
                return False
            elif isinstance(check, bool) and check == True:
                return check
    return False

def get_los_blocks(los, grid_types):
    cords = []
    if los[u'hitType'] == "block" and los[u'inRange'] and los[u'type'] in grid_types:
        # get the possible absolute coordinates of the blocks in line of sight
        los_x = los[u'x']
        los_y = los[u'y']
        los_z = los[u'z']
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    x = int(los_x + i - 1)
                    y = int(los_y + j - 1)
                    z = int(los_z + k - 1)
                    cords.append((x, y, z))
        # remove duplicates
        cords = list(set(cords))          
    return cords
    

def block_check(grid, los, block_grid, key, grid_types):
    # if block is the one we are looking for and it is not in the grid
    if block_grid.type in grid_types and key not in grid:
        # check if the block is in line of sight
        if los[u'hitType'] == "block" and los[u'inRange'] and los[u'type'] == block_grid.type:
            # create a blockInfo using los info
            block_los = BlockInfo(los[u'x'], los[u'y'], los[u'z'], los[u'type'], los[u'colour'])

            # if they are the same add the block to the grid
            if compare_block(block_grid, block_los):
                grid[key] = BlockInfo(block_grid.x, block_grid.y, block_grid.z, block_grid.type, block_los.color)
                return True
            else:
                return False
        else:
            # if the block is not in line of sight add it to missingBlocks
            return -1

    elif key in grid and block_grid.type not in grid_types:
        grid.pop(key)
        return True 

def check_grid_integrity(grid, floor, grid_size, radius, grid_types):
    # check if all grids are in the floor
    for key in grid:
        block = grid[key]
        # get the index of the block in the floor
        index = get_block_1d_coordinates(block.x, block.y, block.z, grid_size, radius)
        # if the block is not in the floor remove it from the grid
        if index >= len(floor) or floor[index] != block.type or block.type not in grid_types:
            grid.pop(key)
            # maybe check the rest before returning ?
            return True
        
    
def update_builder_mode(agent_host, los, name, builder_mode, size, grid_types):
    if builder_mode and u"inRange" in los and los[u"inRange"] and u"hitType" in los:
        # check if the agent is looking at a block in the grid or outside the grid
        if los.get(u"hitType") == "block":
            # get the block position
            x = int(los[u"x"])
            z = int(los[u"z"])
            type_block = los[u"type"]
            # if the agent is looking outside the grid make him unable to destroy or place blocks
            if abs(x) > size or abs(z) > size or  type_block not in (list(grid_types) + ["barrier"] + ["air"]):
                # make builder in adventure mode
                agent_host.sendCommand("chat /gamemode 2 @a[name=" + name + "]")
                builder_mode = 0
        # destroy blocks that are not in the grid
        TWO = 2
        for x1, z1, x2, z2 in [(-size - TWO, size + 1, size+ TWO, size + TWO), (-size, -size - TWO, -size - TWO, size + TWO), (size + 1, -size - TWO, size + TWO, size + TWO), (-size - TWO, -size, size + TWO, -size - TWO)]:
            agent_host.sendCommand(f"chat /fill {x1} 227 {z1} {x2} 254 {z2} minecraft:air")
    elif abs(los['x']) <= size and abs(los['z']) <= size:
        # make architect in survival mode
        agent_host.sendCommand("chat /gamemode 0 @a[name=" + name + "]")
        builder_mode = 1
    return builder_mode