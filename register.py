import os
from PIL import Image


def saveWorldState(agent, config, experimentID, timestamp, entities, chat_log, inventory, grid):
    # get screenshot path and save screenshot
    imagePath = None
    if config['collect']['screenshot']["save"]:
        folderPath = config['collect']['screenshot']["path"]
        interval = config['collect']['screenshot']["interval"]
        imagePath = saveScreenShot(agent, experimentID, timestamp, folderPath, interval)

    # print to console
    if config['collect']['log']['console']:
        printWorldState(timestamp, entities, chat_log, inventory, grid, imagePath)

    saveTxt = config['collect']['log']['txt']
    saveJson = config['collect']['log']['json']
    if saveTxt or saveJson:
        #make a directory for the mission
        date = timestamp.split(" ")[0]
        pathLog = config['collect']['log']['path'] + "/data-" + date + "/" + str(experimentID)
        if not os.path.exists(pathLog):
            os.makedirs(pathLog)
        # save those info in txt and json files
        if saveTxt:
            writeWorldStateTxt(pathLog, timestamp, entities, chat_log, inventory, grid, imagePath)
        if saveJson:
            writeWorldStateJson(pathLog, timestamp, entities, chat_log, inventory, grid, imagePath)
    
                
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
        timestring = timestring.replace(" ", "_")
        #make a directory for the mission if it doesn't exist
        if not os.path.exists(folderPath):
            os.makedirs(folderPath)
        imagePrePath = folderPath + "/" + str(experimentID) + "-Builder"
        if not os.path.exists(imagePrePath):
            os.makedirs(imagePrePath)
        imagePath = imagePrePath + "/" + str(timestring) + "-Builder.png"
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
    if not os.path.exists(pathLog):
        os.makedirs(pathLog)
    txt_path = pathLog + "/observation.txt"
    
    # rewite so that only one process can write to the file at a time
    with open(txt_path, 'a+') as file:
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
    # if there is not a data file with todays date create one
    if not os.path.exists(pathLog):
        os.makedirs(pathLog)
    json_path = pathLog + "/observation.json"
    if not os.path.exists(json_path):
        os.mknod(json_path)
        
    text_to_write = ""
    # add the content of the file
    with open(json_path, 'r') as file:
        text_to_write += file.read()
        
    # if empty, write the first line
    if text_to_write == "":
        text_to_write += "{\n"
        text_to_write += "\t\"WorldStates\": [\n"
    else:
        # remove the ending bracket
        text_to_write = text_to_write[:-6]
        text_to_write += ",\n"
    # write the world state
    text_to_write += "\t\t{\n"
    # use entites position
    if entities is not None:
        for ent in entities:
            text_to_write += "\t\t\t\""+ ent.name + "_Position\": {\n"
            text_to_write += "\t\t\t\t\"X\": " + str(ent.x) + ",\n"
            text_to_write += "\t\t\t\t\"Y\": " + str(ent.y) + ",\n"
            text_to_write += "\t\t\t\t\"Z\": " + str(ent.z) + ",\n"
            text_to_write += "\t\t\t\t\"Yaw\": " + str(ent.yaw) + ",\n"
            text_to_write += "\t\t\t\t\"Pitch\": " + str(ent.pitch) + "\n"
            text_to_write += "\t\t\t},\n"
    # write the chat history
    if chat_log is not None:
        text_to_write += "\t\t\t\"ChatHistory\": [\n"
        for chat in chat_log:
            text_to_write += "\t\t\t\t\"" + str(chat) + "\",\n"
        # remove the last comma if there is at - 2
        if len(chat_log) > 0:
            text_to_write = removeLastTComma(text_to_write)
        text_to_write += "\n"
        text_to_write += "\t\t\t],\n"
    # write the timestamp
    text_to_write += "\t\t\t\"Timestamp\": \"" + str(timestamp) + "\",\n"
    # write the blocks in grid
    if grid is not None:
        text_to_write += "\t\t\t\"BlocksInGrid\": [\n"
        for key, block in list(grid.items()):
            text_to_write += "\t\t\t\t{\n"
            text_to_write += "\t\t\t\t\t\"X\": " + str(block.x) + ",\n"
            text_to_write += "\t\t\t\t\t\"Y\": " + str(block.y) + ",\n"
            text_to_write += "\t\t\t\t\t\"Z\": " + str(block.z) + ",\n"
            text_to_write += "\t\t\t\t\t\"Type\": \"" + block.type + "\",\n"
            text_to_write += "\t\t\t\t\t\"Colour\": \"" + block.colour + "\"\n"
            text_to_write += "\t\t\t\t},\n"
        # remove the last comma
        if len(grid) > 0:
            text_to_write = removeLastTComma(text_to_write)
        text_to_write += "\n"
        text_to_write += "\t\t\t],\n"
    # write the builder inventory
    if inventory is not None:
        text_to_write += "\t\t\t\"BuilderInventory\": [\n"
        for key, items in list(inventory.items()):
            text_to_write += "\t\t\t\t{\n"
            text_to_write += "\t\t\t\t\t\"Name\": \"" + key + "\",\n"
            text_to_write += "\t\t\t\t\t\"Items\": [\n"
            for item in items:
                # write the item index type colour and quantity
                text_to_write += "\t\t\t\t\t\t{\n"
                text_to_write += "\t\t\t\t\t\t\t\"Index\": " + str(item['index']) + ",\n"
                text_to_write += "\t\t\t\t\t\t\t\"Type\": \"" + item['type'] + "\",\n"
                if 'colour' in item:
                    text_to_write += "\t\t\t\t\t\t\t\"Colour\": \"" + str(item['colour']) + "\",\n"
                text_to_write += "\t\t\t\t\t\t\t\"Quantity\": " + str(item['quantity']) + "\n"
                text_to_write += "\t\t\t\t\t\t},\n"
            # remove the last comma
            if (len(items) > 0):
                text_to_write = removeLastTComma(text_to_write)
            text_to_write += "\t\t\t\t\t]\n"
            text_to_write += "\t\t\t\t},\n"
        # remove the last comma
        if len(inventory) > 0:
            text_to_write = removeLastTComma(text_to_write)
        text_to_write += "\n"
        text_to_write += "\t\t\t],\n"
    # write the screenshots
    if imagePath is not None:
        text_to_write += "\t\t\t\"Screenshots\": {\n"
        text_to_write += "\t\t\t\t\"Path\": \"" + str(imagePath) + "\",\n"
        text_to_write += "\t\t\t\t\"Timestamp\": \"" + str(timestamp) + "\"\n"
        text_to_write += "\t\t\t},\n"
    # remove the last comma
    text_to_write = removeLastTComma(text_to_write)
    text_to_write += "\t\t}\n"
    text_to_write += "\t]\n"
    text_to_write += "}\n"
    
    # if the length of the file is less than text_to_write then write to file
    if len(text_to_write) > os.path.getsize(json_path):
        # rewrite the file
        with open(json_path, 'w') as f:
            f.write(text_to_write)
        
def removeLastTComma(text_to_write):
    if text_to_write[-2] == ',':
        text_to_write = text_to_write[:-2] + "\n"
    return text_to_write

            
        
        