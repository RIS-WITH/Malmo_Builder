import os
from PIL import Image


def save_world_state(lock, agent, config, experiment_id, timestamp, entities, chat_log, inventory, grid):
    # get screenshot path and save screenshot
    image_path = None
    if config['collect']['screenshot']["save"]:
        folder_path = config['collect']['screenshot']["path"]
        interval = config['collect']['screenshot']["interval"]
        image_path = save_screen(agent, experiment_id, timestamp, folder_path, interval)

    # print to console
    if config['collect']['log']['console']:
        print_world_state(timestamp, entities, chat_log, inventory, grid, image_path)

    save_txt = config['collect']['log']['txt']
    save_json = config['collect']['log']['json']
    if save_txt or save_json:
        #make a directory for the mission
        date = timestamp.split(" ")[0]
        path_to_log = config['collect']['log']['path'] + "/data-" + date + "/" + str(experiment_id)
        if not os.path.exists(path_to_log):
            os.makedirs(path_to_log)
        # save those info in txt and json files
        if save_txt:
            write_world_state_txt(lock, path_to_log, timestamp, entities, chat_log, inventory, grid, image_path)
        if save_json:
            write_world_state_json(lock, path_to_log, timestamp, entities, chat_log, inventory, grid, image_path)
    
                
# merge the two functions into one
def every_n_seconds_minutes(interval, timestamp):
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

def save_screen(agent, experiment_id, timestamp, folder_path, interval):
    observer = agent.getWorldState()
    # timestamp is a string 2023-05-17 11:24:07, convert it
    # first get the time
    time = timestamp.split(" ")[1]
    # then get the hour, minute, second
    hour = time.split(":")[0]
    minute = time.split(":")[1]
    second = time.split(":")[2]
    # time in second
    time_in_seconds = int(hour) * 3600 + int(minute) * 60 + int(second)

    interval_check = (interval == "every_move")
    interval_check = (interval == "every_second" and time_in_seconds % 1 == 0) or interval_check
    interval_check = (interval == "every_minute" and time_in_seconds % 60 == 0) or interval_check
    interval_check = (interval == "every_hour" and time_in_seconds % 3600 == 0) or interval_check
    interval_check = every_n_seconds_minutes(interval, time_in_seconds) or interval_check
        
    if observer.number_of_video_frames_since_last_state > 0 and interval_check:
        frame = observer.video_frames[-1]
        image = Image.frombytes('RGB', (frame.width, frame.height), bytes(frame.pixels) )
        # remove unwanted characters from timestamp
        time_string = str(timestamp).replace(":", "-")
        time_string = time_string.replace(" ", "_")
        #make a directory for the mission if it doesn't exist
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        image_pre_path = folder_path + "/" + str(experiment_id) + "-Builder"
        if not os.path.exists(image_pre_path):
            os.makedirs(image_pre_path)
        image_path = image_pre_path + "/" + str(time_string) + "-Builder.png"
        image.save(str(image_path))
        return image_path
    return ""

def print_world_state(timestamp, entities, chat_log, inventory, grid, image_path):
     # print to console
    print("--------------------")
    print("[Timestamp] " + str(timestamp))
    if entities is not None:
        print("[Builder Position] ")
        for entity in entities:
            print("\t" + str(entity.name) + " (x, y, z): (" + str(entity.x) + ", " + str(entity.y) + ", " + str(entity.z) + ") (yaw, pitch): (" + str(entity.yaw) + ", " + str(entity.pitch) + ")"  )
    if image_path is not None:
        print("[Screenshot Path] " + image_path)
    if chat_log is not None:
        print("[Chat Log]")
        for chat in chat_log:
            print("\t" + str(chat))
    if inventory is not None:
        print("[Blocks In Inventory] " + str(inventory))
    if grid is not None:
        print("[Blocks In Grid] " + str(grid))

def write_world_state_txt(lock, path_log, timestamp, entities, chat_log, inventory, grid, image_path):
    with lock:
        if not os.path.exists(path_log):
            os.makedirs(path_log)
        txt_path = path_log + "/observation.txt" 
        
        with open(txt_path, 'a+') as file:
            # write the data to file
            file.write("--------------------\n")
            file.write("[Timestamp] " + str(timestamp) + "\n")
            if entities is not None:
                file.write("[Builder Position] \n")
                for entity in entities:
                    file.write("\t" + str(entity.name) + " (x, y, z): (" + str(entity.x) + ", " + str(entity.y) + ", " + str(entity.z) + ") (yaw, pitch): (" + str(entity.yaw) + ", " + str(entity.pitch) + ")\n"  )
            if image_path is not None:
                file.write("[Screenshot Path] " + image_path + "\n")
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

def remove_last_comma(file):
    file.seek(file.tell() - 2, os.SEEK_SET)
    file.truncate()

def remove_last_brackets(file):
    file.seek(file.tell() - 6, os.SEEK_SET)
    file.truncate()

def write_world_state_json(lock, path_log, timestamp, entities, chat_log, inventory, grid, image_path):
    with lock:
        # if there is not a data file with todays date create one
        if not os.path.exists(path_log):
            os.makedirs(path_log)
        json_path = path_log + "/observation.json"
        if not os.path.exists(json_path):
            os.mknod(json_path)
            
        text_to_write = ""   
        # if empty, write the first line
        if os.stat(json_path).st_size == 0:
            text_to_write += "{\n"
            text_to_write += "\t\"WorldStates\": [\n"
        else:
            text_to_write += ",\n"
        # write the world state
        text_to_write += "\t\t{\n"
        # use entities position
        if entities is not None:
            for ent in entities:
                text_to_write += "\t\t\t\""+ ent.name + "_Position\": {\n"
                text_to_write += "\t\t\t\t\"X\": " + str(ent.x) + ",\n"
                text_to_write += "\t\t\t\t\"Y\": " + str(ent.y - 226) + ",\n"
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
                text_to_write = remove_last_comma_string(text_to_write)
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
                text_to_write += "\t\t\t\t\t\"Y\": " + str(block.y - 226) + ",\n"
                text_to_write += "\t\t\t\t\t\"Z\": " + str(block.z) + ",\n"
                text_to_write += "\t\t\t\t\t\"Type\": \"" + block.type + "\",\n"
                text_to_write += "\t\t\t\t\t\"Colour\": \"" + block.colour + "\"\n"
                text_to_write += "\t\t\t\t},\n"
            # remove the last comma
            if len(grid) > 0:
                text_to_write = remove_last_comma_string(text_to_write)
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
                    # write the item index type color and quantity
                    text_to_write += "\t\t\t\t\t\t{\n"
                    text_to_write += "\t\t\t\t\t\t\t\"Index\": " + str(item['index']) + ",\n"
                    text_to_write += "\t\t\t\t\t\t\t\"Type\": \"" + item['type'] + "\",\n"
                    if 'colour' in item:
                        text_to_write += "\t\t\t\t\t\t\t\"Colour\": \"" + str(item['colour']) + "\",\n"
                    text_to_write += "\t\t\t\t\t\t\t\"Quantity\": " + str(item['quantity']) + "\n"
                    text_to_write += "\t\t\t\t\t\t},\n"
                # remove the last comma
                if (len(items) > 0):
                    text_to_write = remove_last_comma_string(text_to_write)
                text_to_write += "\t\t\t\t\t]\n"
                text_to_write += "\t\t\t\t},\n"
            # remove the last comma
            if len(inventory) > 0:
                text_to_write = remove_last_comma_string(text_to_write)
            text_to_write += "\n"
            text_to_write += "\t\t\t],\n"
        # write the screenshots
        if image_path is not None:
            text_to_write += "\t\t\t\"Screenshots\": {\n"
            text_to_write += "\t\t\t\t\"Path\": \"" + str(image_path) + "\",\n"
            text_to_write += "\t\t\t\t\"Timestamp\": \"" + str(timestamp) + "\"\n"
            text_to_write += "\t\t\t},\n"
        # remove the last comma
        text_to_write = remove_last_comma_string(text_to_write)
        text_to_write += "\t\t}\n"
        text_to_write += "\t]\n"
        text_to_write += "}\n"
        
        # rewrite the file
        with open(json_path, 'a') as f:
            if os.stat(json_path).st_size != 0:
                remove_last_brackets(f)
            f.write(text_to_write)
        
def remove_last_comma_string(text_to_write):
    if text_to_write[-2] == ',':
        text_to_write = text_to_write[:-2] + "\n"
    return text_to_write

            
        
        