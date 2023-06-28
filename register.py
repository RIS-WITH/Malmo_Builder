import os
from PIL import Image
import json


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
        
        text_to_write = ""
        # write the data to file
        text_to_write += "--------------------\n"
        text_to_write += "[Timestamp] " + str(timestamp) + "\n"
        if entities is not None:
            text_to_write += "[Entities] " + str(entities) + "\n"
        if image_path is not None:
            text_to_write += "[Screenshot Path] " + image_path + "\n"
        if chat_log is not None:
            text_to_write += "[Chat History]"  + str(write_chat_history(chat_log)) + "\n"
        if inventory is not None:
            text_to_write += "[Blocks In Inventory] " + str(write_builder_inventory(inventory)) + "\n"
        if grid is not None:
            text_to_write += "[Blocks In Grid] " + str(write_blocks_in_grid(grid)) + "\n"
        
        # remove the last newline character and write to file
        text_to_write = text_to_write.rstrip('\n')
        with open(txt_path, 'a+') as file:
            file.write(text_to_write + '\n')
            file.close()

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
        if os.stat(json_path).st_size  < 2:
            # all world states are under WorldStates key
            world_states = {
                'WorldStates': []
            }
            # add the world states to the json file
            with open(json_path, 'w') as f:
                f.write(json.dumps(world_states, indent=4))

        # write the world state
        world_state = {
            "entities": write_entities(entities),
            "chat_history": write_chat_history(chat_log),
            "timestamp": timestamp,
            "blocks_in_grid": write_blocks_in_grid(grid),
            "builder_inventory": write_builder_inventory(inventory),
            "screenshots": write_screenshots(image_path, timestamp)
        }

        # append the world state to the json file
        with open(json_path, 'r+') as f:
            data = json.load(f)
            data['WorldStates'].append(world_state)
            f.seek(0)
            json.dump(data, f, indent=4)

def write_entities(entities):
    if entities is None:
        return None

    entity_list = []
    for entity in entities:
        entity_dict = {
            str(entity.name) + "_position": {
                "X": entity.x,
                "Y": entity.y - 226,
                "Z": entity.z,
                "Yaw": entity.yaw,
                "Pitch": entity.pitch
            }
        }
        entity_list.append(entity_dict)

    return entity_list

def write_chat_history(chat_log):
    if chat_log is None:
        return None

    return [str(chat) for chat in chat_log]

def write_blocks_in_grid(grid):
    if grid is None:
        return None

    block_list = []
    for key, block in list(grid.items()):
        block_dict = {
            "X": block.x,
            "Y": block.y - 226,
            "Z": block.z,
            "Type": block.type,
            "Colour": block.color
        }
        block_list.append(block_dict)

    return block_list

def write_builder_inventory(inventory):
    if inventory is None:
        return None

    inventory_list = []
    for key, items in list(inventory.items()):
        item_list = []
        for item in items:
            item_dict = {
                "Index": item['index'],
                "Type": item['type'],
                "Quantity": item['quantity']
            }
            if 'colour' in item:
                item_dict['Colour'] = item['colour']
            item_list.append(item_dict)

        inventory_dict = {
            "Name": key,
            "Items": item_list
        }
        inventory_list.append(inventory_dict)

    return inventory_list

def write_screenshots(image_path, timestamp):
    if image_path is None:
        return None

    screenshot_dict = {
        "Path": str(image_path),
        "Timestamp": timestamp
    }

    return screenshot_dict

        
            
        
        