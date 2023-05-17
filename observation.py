from collections import namedtuple

EntityInfo = namedtuple('EntityInfo', 'x, y, z, yaw, pitch, name, colour, variation, quantity, life')
EntityInfo.__new__.__defaults__ = (0, 0, 0, 0, 0, "", "", "", 1, 1)
BlockInfo = namedtuple('BlockInfo', 'x, y, z, type, colour')
BlockInfo.__new__.__defaults__ = (0, 0, 0, "", "")

def getEntitiesInfo(observations):
    # get builder 1 and 2 position
    if "entities" in observations:
        entities = [EntityInfo(k["x"], k["y"], k["z"], k["yaw"], k["pitch"], k["name"]) for k in observations["entities"]]
    # order entities by name
    return sorted(entities, key=lambda x: x.name)

def updateChatLog(observations, chat_log):
    if "Chat" in observations:
        if len(chat_log) == 0 or chat_log[-1] != observations["Chat"]:
            chat_log.append(observations["Chat"])
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

def verfiyGridEntegrity(grid, gridFound, cords, side_size, xzToCenter):
    # grid is a dictionry of BlockInfo with x y z and type
    # gridFound is a 3d array with key x y z and value BlockInfo
    change = False
    for key, block in list(grid.items()):
        if gridFound[(block.x + xzToCenter) % side_size][(block.y - 227) % side_size][(block.z + xzToCenter) % side_size] == None:
            grid.pop(key)
            change = True
    # check for missing blocks
    for cord in cords:
        key = "block" + str(cord[0]) + "_" + str(cord[1]) + "_" + str(cord[2])
        if key not in grid:
            typeGrid = gridFound[(cord[0] + xzToCenter) % side_size][(cord[1] - 227) % side_size][(cord[2] + xzToCenter) % side_size]
            grid[key] = BlockInfo(cord[0], cord[1], cord[2], typeGrid)
            change = True
    return change

def updateGrid(observation, grid, side_size, gridTypes):
    # get blocks using ObservationFromGrid absolute position
    if "floor" in observation and u"LineOfSight" in observation:
        floor = observation["floor"]
        los = observation["LineOfSight"]
        # transform the grid to a 3d array
        # floor is of area_side_size^3
        gridSize = side_size
        xzToCenter = (side_size - 1) // 2
        gridFound = [[[None for k in range(gridSize)] for j in range(gridSize)] for i in range(gridSize)]
        cords= []
        for i, block_type in enumerate(floor):
            x = i % gridSize
            z = (i // gridSize) % gridSize
            y = (i // gridSize // gridSize) % gridSize
            # add world position to block
            xa = x - xzToCenter
            ya = y + 227
            za = z - xzToCenter
            # if block is the type wanted gridtype is a set of block types
            if block_type in gridTypes:
                gridFound[x][y][z] = block_type
                cords.append([xa, ya, za])
            # add color to block
            if los[u'hitType'] == "block" and los[u'inRange'] and los[u'type'] == "wool":
                blockGrid = BlockInfo(xa, ya, za, block_type, "")
                blockLos = BlockInfo(los[u'x'], los[u'y'], los[u'z'], los[u'type'], los[u'colour'])
                block = BlockInfo(xa, ya, za, block_type, blockLos.colour)
                
                # make a unique key for the block
                key = "block" + str(block.x) + "_" + str(block.y) + "_" + str(block.z)

                # if not already a similar blockInfo in grid then add it
                if key not in grid and compareBlock(blockGrid, blockLos):
                    grid[key] = block
                    return True
        # check all blocks in grid are in the observation  
        return verfiyGridEntegrity(grid, gridFound, cords, side_size, xzToCenter)