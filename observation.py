from collections import namedtuple

EntityInfo = namedtuple('EntityInfo', 'x, y, z, yaw, pitch, name, colour, variation, quantity, life')
EntityInfo.__new__.__defaults__ = (0, 0, 0, 0, 0, "", "", "", 1, 1)
BlockInfo = namedtuple('BlockInfo', 'x, y, z, type, colour')
BlockInfo.__new__.__defaults__ = (0, 0, 0, "", "")

def getEntitiesInfo(observations, lastEntities=None, names=[]):
    # get builder 1 and 2 position
    if "entities" in observations:
        entities = [EntityInfo(k["x"], k["y"], k["z"], k["yaw"], k["pitch"], k["name"]) for k in observations["entities"]]
    # get rid of block types and other unwanted entities
    entities = [e for e in entities if e.name in names]
    # order entities by name
    if lastEntities is not None and len(entities) < len(lastEntities):
        for e in lastEntities:
            # if un entity is missing, add it
            if e.name not in [k.name for k in entities]:
                entities.append(e)
    return sorted(entities, key=lambda x: x.name)

def updateChatLog(observations, chat_log, config):
    if "Chat" in observations:
        return readObservationChatLog(observations, chat_log)
    else:
        return readServerChatLog(chat_log, config)
    
def readServerChatLog(chat_log, config):
    # read config file log path
    with open(config['server']['log_path']) as log_file:
        # if the log file contains two lines
        if len(log_file.readlines()) > 1:
            # just read the last two lines
            lines = log_file.readlines()[-2:]
            for line in lines:
                # if it has chat in it
                if "]: [CHAT]" in line and (config["agents"]["builder_1"]["name"] in line or config["agents"]["builder_2"]["name"] in line) and "ADMIN" not in line:
                    # get the chat message
                    message = line.split("]: [CHAT] ")[1]
                    # remove the \n
                    message = message[:-1]
                    if (len(chat_log) < 3 and message not in chat_log) or message not in chat_log[-3:]:
                        chat_log.append(message)
                        return True
        return False
    
    
def readObservationChatLog(observations, chat_log):
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

def getInventoryInfo(observation, entities):
    inventory = {}
    if "inventory" in observation:
        if len(inventory) == 0:
            for e in entities:
                inventory[e.name] = observation["inventory"]
        else:
            inventory[observation["Name"]] = observation["inventory"]
    return inventory

def samePosition(ents1, ents2, precision=0.1, anglePrecision=400):
    # compare the position of the agents
    if ents1 == ents2:
        return True
    if ents1 == None or ents2 == None:
        return False
    if len(ents1) != len(ents2):
        return False
    # compare each entity position and orientation using the precision
    for i in range(len(ents1)):
        e1 = ents1[i]
        e2 = ents2[i]
        if e1.name != e2.name:
            return False
        if abs(e1.yaw - e2.yaw) > anglePrecision * 2:
            return False
        if abs(e1.pitch - e2.pitch) > anglePrecision/12:
            return False
        if abs(e1.x - e2.x) > precision:
            return False
        if abs(e1.y - e2.y) > precision:
            return False
        if abs(e1.z - e2.z) > precision:
            return False
    return True

def getBlockCoordinates(i, gridSize, xzToCenter):
    x = i % gridSize
    y = i // gridSize // gridSize
    z = (i // gridSize) % gridSize
    return (x - xzToCenter), (y + 227), (z - xzToCenter)

def getBlock1dCoordinates(x, y, z, gridSize, xzToCenter):
    # do the inverse of getBlockCoordinates
    return (x + xzToCenter) + (y - 227) * gridSize * gridSize + (z + xzToCenter) * gridSize

def compareBlock(blockorg, blockhit):
    precision = 1.49
    if abs(blockorg.x - blockhit.x) > precision or abs(blockorg.y - blockhit.y) > precision or abs(blockorg.z - blockhit.z) > precision:
        return False
    # compare the type of the block
    if blockorg.type != blockhit.type:
        return False
    return True

def updateGrid(observation, grid, side_size, gridTypes):
    # get blocks using ObservationFromGrid absolute position
    change = False
    if "floor" in observation:
        floor = observation["floor"]
        # xzToCenter is the distance from the center of the grid to the edge
        xzToCenter = (side_size - 1) // 2
        
        # grid size is the side size of the area we are looking at
        gridSize = side_size
        if u"LineOfSight" in observation:
            los = observation["LineOfSight"]

            
            # check if there is a change in the grid
            change = gridCheck(grid, los, floor, gridSize, xzToCenter, gridTypes)
        # check all blocks we are not loking at are in grid are in the observation  
        change = checkGridIntegrity(grid, floor, gridSize, xzToCenter, gridTypes) or change
    return change

def gridCheck(grid, los, floor, gridSize, xzToCenter, gridTypes):
    # check all blocks in line of sight are in grid and then check all blocks we are not loking at are in grid are in the observation
    cords = getlosblocks(los, gridTypes)
    if cords == []:
        return False
    
    # array for missing blocks
    missingBlocks = []
    
    # transform thes 3d coordinates to 1d
    index = [int(getBlock1dCoordinates(x, y, z, gridSize, xzToCenter)) for x, y, z in cords]
    for i in index:
        # see if the index i in the 1d array floor
        if i < len(floor):
            # get the block type
            block_type = floor[i]
            # get the 3d coordinates of the block
            x, y, z = getBlockCoordinates(i, gridSize, xzToCenter)
            # create a blockInfo using floor info
            blockGrid = BlockInfo(x, y, z, block_type, "")
            
            # make a unique key for the block
            key = "block" + str(blockGrid.x) + "_" + str(blockGrid.y) + "_" + str(blockGrid.z)
                
            check = blockCheck(grid, los, blockGrid, key, gridTypes)
            
            # if blockCheck is -1 then the block is not in the grid and not in line of sight
            if check == -1:
                # add the block to missingBlocks
                missingBlocks.append((x, y, z, block_type))
            elif isinstance(check, bool):
                return check

def getlosblocks(los, gridTypes):
    cords = []
    if los[u'hitType'] == "block" and los[u'inRange'] and los[u'type'] in gridTypes:
        # get the possible absolute coordinates of the blocks in line of sight
        losx = los[u'x']
        losy = los[u'y']
        losz = los[u'z']
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    x = int(losx + i - 1)
                    y = int(losy + j - 1)
                    z = int(losz + k - 1)
                    cords.append((x, y, z))
        # remove duplicates
        cords = list(set(cords))          
    return cords
    

def blockCheck(grid, los, blockGrid, key, gridTypes):
    # if block is the one we are looking for and it is not in the grid
    if blockGrid.type in gridTypes and key not in grid:
        # check if the block is in line of sight
        if los[u'hitType'] == "block" and los[u'inRange'] and los[u'type'] == blockGrid.type:
            # create a blockInfo using los info
            blockLos = BlockInfo(los[u'x'], los[u'y'], los[u'z'], los[u'type'], los[u'colour'])

            # if they are the same add the block to the grid
            if compareBlock(blockGrid, blockLos):
                grid[key] = BlockInfo(blockGrid.x, blockGrid.y, blockGrid.z, blockGrid.type, blockLos.colour)
                return True
            else:
                return False
        else:
            # if the block is not in line of sight add it to missingBlocks
            return -1

    elif key in grid and blockGrid.type not in gridTypes:
        grid.pop(key)
        return True 
    return

def checkGridIntegrity(grid, floor, gridSize, xzToCenter, gridTypes):
    # check if all grids are in the floor
    for key in grid:
        block = grid[key]
        # get the index of the block in the floor
        index = getBlock1dCoordinates(block.x, block.y, block.z, gridSize, xzToCenter)
        # if the block is not in the floor remove it from the grid
        if index >= len(floor) or floor[index] != block.type or block.type not in gridTypes:
            grid.pop(key)
            # maybe check the rest before returning ?
            return True

def fillMissing(grid, missingBlocks):
    # check for missing blocks (in case player is placing blocks too fast and the server is not updating fast enough)
    change = False
    for cord in missingBlocks:
        key = "block" + str(cord[0]) + "_" + str(cord[1]) + "_" + str(cord[2])
        typeGrid = cord[3]
        # get the color of the last grid
        color = getNearestColor(grid, cord)
        grid[key] = BlockInfo(cord[0], cord[1], cord[2], typeGrid, color)
        change = True
    return change

def getNearestColor(grid, cord):
    color = ""
    block = None
    if grid != {}:
        # loop through the grid in a reverse order and find the nearest color about 3 blocks max
        cout = 0
        for b in reversed(list(grid.keys())):
            if block == None:
                block = grid[b]
            # check wich block is closer to the cord
            elif abs(block.x - cord[0]) + abs(block.y - cord[1]) + abs(block.z - cord[2]) > abs(grid[b].x - cord[0]) + abs(grid[b].y - cord[1]) + abs(grid[b].z - cord[2]):
                block = grid[b]
            cout += 1
            if cout > 3:
                break
    if block != None:
        color = block.colour
    return color