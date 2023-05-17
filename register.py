import os
from PIL import Image


# merge the two functions into one
def everyNSecondsAndMinutes(interval, timestamp):
    if interval.startswith("every_") and (interval.endswith("_seconds") or interval.endswith("_minutes")):
        n = interval.split("_")[1]
        # if n is not a number in a string, return false
        if not n.isdigit():
            return False
        n = int(n)
        if interval.endswith("_seconds"):
            return timestamp % n == 0
        elif interval.endswith("_minutes"):
            return timestamp % (n * 60) == 0
    return False

def saveScreenShot(agent, experimentID, timestamp, folderPath, interval):
    observer = agent.getWorldState()
    # timestamp is a string 2023-05-17 11:24:07, convert it
    # first get the time
    time = timestamp.split(" ")[1]
    # then get the hour, minute, second
    hour = time.split(":")[0]
    minute = time.split(":")[1]
    second = time.split(":")[2]
    # time in second
    timesecond = int(hour) * 3600 + int(minute) * 60 + int(second)

    intervalCheck = (interval == "every_move")
    intervalCheck = (interval == "every_second" and timesecond % 1 == 0) or intervalCheck
    intervalCheck = (interval == "every_minute" and timesecond % 60 == 0) or intervalCheck
    intervalCheck = (interval == "every_hour" and timesecond % 3600 == 0) or intervalCheck
    intervalCheck = everyNSecondsAndMinutes(interval, timesecond) or intervalCheck
        
    if observer.number_of_video_frames_since_last_state > 0 and intervalCheck:
        frame = observer.video_frames[-1]
        image = Image.frombytes('RGB', (frame.width, frame.height), bytes(frame.pixels) )
        # remove unwanted charecters from timestamp
        timestring = str(timestamp).replace(":", "-")
        timeString = timestring.replace(" ", "_")
        #make a directory for the mission if it doesn't exist
        if not os.path.exists(folderPath):
            os.makedirs(folderPath)
        imagePrePath = folderPath + "/" + str(experimentID) + "-Builder"
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
    if entities is not None:
        print("[Builder Position] ")
        for entity in entities:
            print("\t" + str(entity.name) + " (x, y, z): (" + str(entity.x) + ", " + str(entity.y) + ", " + str(entity.z) + ") (yaw, pitch): (" + str(entity.yaw) + ", " + str(entity.pitch) + ")"  )
    if imagePath is not None:
        print("[Screenshot Path] " + imagePath)
    if chat_log is not None:
        print("[Chat Log]")
        for chat in chat_log:
            print("\t" + str(chat))
    if inventory is not None:
        print("[Blocks In Inventory] " + str(inventory))
    if grid is not None:
        print("[Blocks In Grid] " + str(grid))

def writeWorldStateTxt(pathLog, timestamp, entities, chat_log, inventory, grid, imagePath):
    # open a file in append mode in texts folder named with mission id
    file = open(pathLog + "/missionLog-Builder.txt", "a")
    # write the data to file
    file.write("--------------------\n")
    file.write("[Timestamp] " + str(timestamp) + "\n")
    if entities is not None:
        file.write("[Builder Position] \n")
        for entity in entities:
            file.write("\t" + str(entity.name) + " (x, y, z): (" + str(entity.x) + ", " + str(entity.y) + ", " + str(entity.z) + ") (yaw, pitch): (" + str(entity.yaw) + ", " + str(entity.pitch) + ")\n"  )
    if imagePath is not None:
        file.write("[Screenshot Path] " + imagePath + "\n")
    if chat_log is not None:
        file.write("[Chat Log]\n")
        for chat in chat_log:
            file.write("\t" + str(chat) + "\n")
    if inventory is not None:
        file.write("[Builders Inventory] \n")
        for agent_name, items in list(inventory.items()):
            file.write("\t" + str(agent_name) + "\n")
            for item in items:
                file.write("\t\t" + str(item) + "\n")
    if grid is not None:
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
    if entities is not None:
        for ent in entities:
            file.write("\t\t\t\""+ ent.name + "Position\": {\n")
            file.write("\t\t\t\t\"X\": " + str(ent.x) + ",\n")
            file.write("\t\t\t\t\"Y\": " + str(ent.y) + ",\n")
            file.write("\t\t\t\t\"Z\": " + str(ent.z) + ",\n")
            file.write("\t\t\t\t\"Yaw\": " + str(ent.yaw) + ",\n")
            file.write("\t\t\t\t\"Pitch\": " + str(ent.pitch) + "\n")
            file.write("\t\t\t},\n")
    # write the chat history
    if chat_log is not None:
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
    if grid is not None:
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
    if inventory is not None:
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
    if imagePath is not None:
        file.write("\t\t\t\"Screenshots\": {\n")
        file.write("\t\t\t\t\"Path\": \"" + str(imagePath) + "\",\n")
        file.write("\t\t\t\t\"Timestamp\": \"" + str(timestamp) + "\"\n")
        file.write("\t\t\t},\n")
    # remove the last comma
    removeLastComma(file)
    file.write("\t\t}\n")
    file.write("\t]\n")
    file.write("}\n")
    # close the file
    file.close()