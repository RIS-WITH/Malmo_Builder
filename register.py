import os
from PIL import Image

def saveScreenShot(agent, experimentID, timestamp):
    observer = agent.getWorldState()
    if observer.number_of_video_frames_since_last_state > 0:
        frame = observer.video_frames[-1]
        image = Image.frombytes('RGB', (frame.width, frame.height), bytes(frame.pixels) )
        # remove unwanted charecters from timestamp
        timestring = str(timestamp).replace(":", "-")
        timeString = timestring.replace(" ", "_")
        #make a directory for the mission
        if not os.path.exists("./screenshots"):
            os.makedirs("./screenshots")
        imagePrePath = "./screenshots/" + str(experimentID) + "-Builder"
        if not os.path.exists(imagePrePath):
            os.makedirs(imagePrePath)
        imagePath = imagePrePath + "/" + str(timestamp) + "-Builder.png"
        image.save(str(imagePath))
        return imagePath
    return ""

def printWorldState(timestamp, entities, chat_log, inventory, grid, imagePath):
     # print to console
    print("--------------------")
    print("[Timestamp] " + str(timestamp))
    print("[Builder Position] ")
    for entity in entities:
        print("\t" + str(entity.name) + " (x, y, z): (" + str(entity.x) + ", " + str(entity.y) + ", " + str(entity.z) + ") (yaw, pitch): (" + str(entity.yaw) + ", " + str(entity.pitch) + ")"  )
    print("[Screenshot Path] " + imagePath)
    print("[Chat Log]")
    for chat in chat_log:
        print("\t" + str(chat))
    print("[Blocks In Inventory] " + str(inventory))
    print("[Blocks In Grid] " + str(grid))

def writeWorldStateTxt(pathLog, timestamp, entities, chat_log, inventory, grid, imagePath):
    # open a file in append mode in texts folder named with mission id
    file = open(pathLog + "/missionLog-Builder.txt", "a")
    # write the data to file
    file.write("--------------------\n")
    file.write("[Timestamp] " + str(timestamp) + "\n")
    file.write("[Builder Position] \n")
    for entity in entities:
        file.write("\t" + str(entity.name) + " (x, y, z): (" + str(entity.x) + ", " + str(entity.y) + ", " + str(entity.z) + ") (yaw, pitch): (" + str(entity.yaw) + ", " + str(entity.pitch) + ")\n"  )
    file.write("[Screenshot Path] " + imagePath + "\n")
    file.write("[Chat Log]\n")
    for chat in chat_log:
        file.write("\t" + str(chat) + "\n")
    file.write("[Builders Inventory] \n")
    for agent_name, items in list(inventory.items()):
        file.write("\t" + str(agent_name) + "\n")
        for item in items:
            file.write("\t\t" + str(item) + "\n")
    file.write("[Blocks In Grid] \n")
    for key, block in list(grid.items()):
        file.write("\t" + str(block) + "\n")
    # close the file
    file.close()

def removeLastComma(file):
    file.seek(file.tell() - 2, os.SEEK_SET)
    file.truncate()

def removeLastBrakets(file):
    file.seek(file.tell() - 6, os.SEEK_SET)
    file.truncate()

def writeWorldStateJson(pathLog, timestamp, entities, chat_log, inventory, grid, imagePath):
    file = open(pathLog + "/missionLog-v2-Builder.json", "a")
    # if empty, write the first line
    if os.stat(pathLog + "/missionLog-v2-Builder.json").st_size == 0:
        file.write("{\n")
        file.write("\t\"WorldStates\": [\n")
    else:
        # reomve the last \n")file.write("\t]\n")file.write("}\n") and add a comma and a new line
        removeLastBrakets(file)
        file.write(",\n")

    # write the world state
    file.write("\t\t{\n")
    # use entites position
    for ent in entities:
        file.write("\t\t\t\""+ ent.name + "Position\": {\n")
        file.write("\t\t\t\t\"X\": " + str(ent.x) + ",\n")
        file.write("\t\t\t\t\"Y\": " + str(ent.y) + ",\n")
        file.write("\t\t\t\t\"Z\": " + str(ent.z) + ",\n")
        file.write("\t\t\t\t\"Yaw\": " + str(ent.yaw) + ",\n")
        file.write("\t\t\t\t\"Pitch\": " + str(ent.pitch) + "\n")
        file.write("\t\t\t},\n")
    # write the chat history
    file.write("\t\t\t\"ChatHistory\": [\n")
    for chat in chat_log:
        file.write("\t\t\t\t\"" + str(chat) + "\",\n")
    # remove the last comma if there is at - 2
    if len(chat_log) > 0:
        removeLastComma(file)
    file.write("\n")
    file.write("\t\t\t],\n")
    # write the timestamp
    file.write("\t\t\t\"Timestamp\": \"" + str(timestamp) + "\",\n")
    # write the blocks in grid
    file.write("\t\t\t\"BlocksInGrid\": [\n")
    for key, block in list(grid.items()):
        file.write("\t\t\t\t{\n")
        file.write("\t\t\t\t\t\"X\": " + str(block.x) + ",\n")
        file.write("\t\t\t\t\t\"Y\": " + str(block.y) + ",\n")
        file.write("\t\t\t\t\t\"Z\": " + str(block.z) + ",\n")
        file.write("\t\t\t\t\t\"Type\": \"" + block.type + "\",\n")
        file.write("\t\t\t\t\t\"Colour\": \"" + block.colour + "\"\n")
        file.write("\t\t\t\t},\n")
    # remove the last comma
    if len(grid) > 0:
        removeLastComma(file)
    file.write("\n")
    file.write("\t\t\t],\n")
    # write the builder inventory
    file.write("\t\t\t\"BuilderInventory\": [\n")
    for key, items in list(inventory.items()):
        file.write("\t\t\t\t{\n")
        file.write("\t\t\t\t\t\"Name\": \"" + key + "\",\n")
        file.write("\t\t\t\t\t\"Items\": [\n")
        for item in items:
            # write the item index type colour and quantity
            file.write("\t\t\t\t\t\t{\n")
            file.write("\t\t\t\t\t\t\t\"Index\": " + str(item['index']) + ",\n")
            file.write("\t\t\t\t\t\t\t\"Type\": \"" + item['type'] + "\",\n")
            if 'colour' in item:
                file.write("\t\t\t\t\t\t\t\"Colour\": \"" + str(item['colour']) + "\",\n")
            file.write("\t\t\t\t\t\t\t\"Quantity\": " + str(item['quantity']) + "\n")
            file.write("\t\t\t\t\t\t},\n")
        # remove the last comma
        if (len(items) > 0):
            removeLastComma(file)
        file.write("\t\t\t\t\t]\n")
        file.write("\t\t\t\t},\n")
    # remove the last comma
    if len(inventory) > 0:
        removeLastComma(file)
    file.write("\t\t\t],\n")
    # write the screenshots
    file.write("\t\t\t\"Screenshots\": {\n")
    file.write("\t\t\t\t\"Path\": \"" + str(imagePath) + "\",\n")
    file.write("\t\t\t\t\"Timestamp\": \"" + str(timestamp) + "\"\n")
    file.write("\t\t\t}\n")
    file.write("\t\t}\n")
    file.write("\t]\n")
    file.write("}\n")
    # close the file
    file.close()