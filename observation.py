from collections import namedtuple

EntityInfo = namedtuple('EntityInfo', 'x, y, z, yaw, pitch, name, colour, variation, quantity, life')
EntityInfo.__new__.__defaults__ = (0, 0, 0, 0, 0, "", "", "", 1, 1)
BlockInfo = namedtuple('BlockInfo', 'x, y, z, type, colour')
BlockInfo.__new__.__defaults__ = (0, 0, 0, "", "")

def getEntitiesInfo(observations, lastEntities=None):
    # get builder 1 and 2 position
    if "entities" in observations:
        entities = [EntityInfo(k["x"], k["y"], k["z"], k["yaw"], k["pitch"], k["name"]) for k in observations["entities"]]
    # order entities by name
    if lastEntities is not None and len(entities) < len(lastEntities):
        for e in lastEntities:
            if e.name not in [k.name for k in entities]:
                entities.append(e)
    return sorted(entities, key=lambda x: x.name)

def updateChatLog(observations, chat_log):
    if "Chat" in observations:
        if len(chat_log) == 0 or chat_log[-1] != observations["Chat"]:
            if "ADMIN" not in observations["Chat"]:
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
            # get the color of the last grid
            color = getNearestColor(grid, cord)
            grid[key] = BlockInfo(cord[0], cord[1], cord[2], typeGrid, color)
            change = True
    return change

def getNearestColor(grid, cord):
    color = ""
    block = None
    if grid != {}:
        # color = grid[list(grid.keys())[-1]].colour
        # loop through the grid in a reverse order and find the nearest color about 5 blocks max
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

                blockGrid = BlockInfo(xa, ya, za, block_type, "")
                
                # make a unique key for the block
                key = "block" + str(blockGrid.x) + "_" + str(blockGrid.y) + "_" + str(blockGrid.z)

                # add color to block
                if key not in grid:
                    if los[u'hitType'] == "block" and los[u'inRange'] and los[u'type'] == block_type:
                        blockLos = BlockInfo(los[u'x'], los[u'y'], los[u'z'], los[u'type'], los[u'colour'])
                        block = BlockInfo(xa, ya, za, block_type, blockLos.colour)

                        # if not already a similar blockInfo in grid then add it
                        if compareBlock(blockGrid, blockLos):
                            grid[key] = block
                            return True
                        else:
                            return False

        # check all blocks in grid are in the observation  
        return verfiyGridEntegrity(grid, gridFound, cords, side_size, xzToCenter)
    
def getMissingBlocksColors(inventory, initInventory):
    # get the missing blocks colors
    missingBlocks = {}

    for block in initInventory:
        if block["quantity"] > 0:
            missingBlocks[block["color"]] = abs(block["quantity"]) * 2

    for agent in inventory:
        for block2 in inventory[agent]:
            if block2["colour"].lower() in missingBlocks:
                missingBlocks[block2["colour"].lower()] -= abs(block2["quantity"])

    return missingBlocks
    
def getMissingBlocksFromGrid(grid, missingBlocksColors):
    missingBlocks = {}
    for key, block in list(grid.items()):
        if block.colour in missingBlocksColors:
            if missingBlocksColors[block.colour] > 0:
                missingBlocksColors[block.colour] -= 1
                if missingBlocksColors[block.colour] == 0:
                    missingBlocksColors.pop(key)
    return missingBlocks

