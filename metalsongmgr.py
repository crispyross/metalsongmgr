import json
from zipfile import ZipFile
import os
import re
import sys
from inspect import signature

METAL_HELLSINGER_ASSET_DIRS = [
    r'C:\Program Files (x86)\Steam\steamapps\common\Metal Hellsinger\Metal_Data\StreamingAssets',
    r'E:\SteamLibrary\steamapps\common\Metal Hellsinger\Metal_Data\StreamingAssets',
    # Note: os.path.expanduser means to turn the "~" into /home/YourUsername on Linux, or /Users/YourUsername on Mac
    os.path.expanduser('~/Library/Application Support/Steam/SteamApps/common/Metal Hellsinger/Metal_Data/StreamingAssets'), # Mac
    os.path.expanduser('~/.steam/steam/SteamApps/common/Metal Hellsinger/Metal_Data/StreamingAssets') # Linux
]

ASSET_DIR = '' # Gets set up in check_asset_dirs() before dispatch
MY_JSON_NAME = 'customsongs-mgr-imported.json'

LEVEL_NAMES = [
    'Tutorial',
    'Voke',
    'Stygia',
    'Yhelm',
    'Incaustis',
    'Gehenna',
    'Nihil',
    'Acheron',
    'Sheol',
    'Hell_Gates',  # Not sure what this is
 ]

# ----------------
# Functions mapped to CLI commands
# ----------------

def do_import(zip_path: str):
    try:
        with ZipFile(zip_path, 'r') as zip:
            names = zip.namelist()
            bank_names = [n for n in names if n.endswith('.bank')]
            customsongs_json_names = [n for n in names if n.endswith('.json')]
            if len(bank_names) != 1 or len(customsongs_json_names) != 1 or customsongs_json_names[0] != 'customsongs.json':
                print("Invalid archive. Zip must contain exactly one .bank file and exactly one .json file called customsongs.json.")
                exit(1)
            
            # Handle bank file
            zip.extract(bank_names[0], ASSET_DIR) # well that was easy

            # Read json data
            song_name = re.sub(r'\.bank$', '', bank_names[0])
            with zip.open('customsongs.json') as songjson:
                try:
                    # Grab the first level music replacement in the json file
                    song_data = json.load(songjson)['customLevelMusic'][0]
                except json.JSONDecodeError:
                    print("JSON data appears to be invalid.")
                    exit(1)
                # If song replaces main music, grab that corresponding json node
                if 'MainMusic' in song_data and song_data['MainMusic']['Bank'] == song_name:
                    song_data = song_data['MainMusic']
                # Else, maybe it replaces boss music only?
                elif 'BossMusic' in song_data and song_data['BossMusic']['Bank'] == song_name:
                    song_data = song_data['BossMusic']
                else:
                    print(f"In customsongs.json, can't find a node containing the custom song bank ({song_name}). Bank file was installed but manual setup is needed for json.")
                    exit(1)
    except OSError:
        print(f'Failed to load {zip_path}.')

    # Add to imported songs and write back to file
    all_songs = get_imported_songs()

    if any((s for s in all_songs if s['Bank'] == song_name)):
        print("NOTICE: Replacing existing song with identical bank name.")
        all_songs = [s for s in all_songs if s['Bank'] != song_name]
    
    all_songs.append(song_data)

    with open(ASSET_DIR + '/' + MY_JSON_NAME, 'w') as f:
        data = { 'imported_songs': all_songs }
        json.dump(data, f, sort_keys=True, indent=4)

    print(f"Song successfully imported as {song_name}.")

def do_list():
    songs = get_imported_songs()
    if len(songs) == 0:
        print("No songs are currently imported.")
    else:
        print(f'{len(songs)} songs are currently imported:')
        for song in songs:
            print(song['Bank'])

def make_vanilla():
    remove_print_err(ASSET_DIR + '/customsongs.json')
    print('Done.')

def installed():
    game_json = get_game_custom_songs_json()
    if len(game_json['customLevelMusic']) == 0:
        print("No songs are currently installed as level/song associations.")
        return
        
    result = ''
    for entry in game_json['customLevelMusic']:
        level_name = entry['LevelName']
        if 'MainMusic' in entry:
            result += f'{level_name} (Main): {entry["MainMusic"]["Bank"]}\n'
        if 'BossMusic' in entry:
            result += f'{level_name} (Boss): {entry["BossMusic"]["Bank"]}\n'
    
    print('Custom level/song associations:')
    print(result)

def set_main_music(level_name: str, song_name: str):
    set_music(level_name, song_name, "MainMusic")

def set_boss_music(level_name: str, song_name: str):
    set_music(level_name, song_name, "BossMusic")

def set_music(level_name: str, song_name: str, music_type_key: str):
    req_song = get_imported_song(song_name)
    if req_song is None:
        print(f"Can't find imported song with name \"{song_name}\". Try using the list command to check songs.")
        exit(1)
    level_name = get_vanilla_level_name(level_name)
    if level_name is None:
        print("Invalid vanilla level name.")
        print(f"Valid level names: {LEVEL_NAMES}")
        exit(1)

    game_json = get_game_custom_songs_json()
    
    # If there is already an entry for the level, set that entry's BossMusic or MainMusic to requested song
    found = False
    for song_entry in game_json['customLevelMusic']:
        if song_entry['LevelName'] == level_name:
            if music_type_key in song_entry:
                existing_song = song_entry[music_type_key]['Bank']
                print(f"Switching out from {existing_song} to {song_name}.")
            song_entry[music_type_key] = req_song
            found = True
            break
        
    # Else, add a new entry for that level/song
    if not found:
        game_json['customLevelMusic'].append({
            'LevelName': level_name,
            music_type_key: req_song
        })

    with open(ASSET_DIR + '/customsongs.json', 'w') as f:
        json.dump(game_json, f, indent=4)
    print('Added new custom song/level association.')

def info(song_name: str):
    s = get_imported_song(song_name)
    if s is None:
        print(f"Can't find imported song with name \"{song_name}\". Try using the list command to check songs.")
        return
    
    song_name = s['Bank']  # Proper capitalization
    print(f"Info for imported song {song_name}:")
    for field, val in s.items():
        print(f"\t{field}: {val}")
        
def remove_main_music(level_name: str):
    remove_music(level_name, "MainMusic")

def remove_boss_music(level_name: str):
    remove_music(level_name, "BossMusic")

def remove_music(level_name: str, music_type_key: str):
    game_json = get_game_custom_songs_json()
    for i, entry in enumerate(game_json['customLevelMusic']):
        if entry['LevelName'] == level_name:
            del entry[music_type_key]
            # Delete entire entry if we deleted the only song replacement in that entry
            if 'MainMusic' not in entry and 'BossMusic' not in entry:
                del game_json['customLevelMusic'][i]
            break

def delete_song(song_name: str):
    songs = get_imported_songs()
    found = False
    for i, s in enumerate(songs):
        if s["Bank"] == song_name:
            del s[i]
            found = True
            break

    if found:
        # Write changed imported songs json back
        pass
    
    file = f'{ASSET_DIR}/{song_name}.bank'
    remove_print_err(file)
    print('Song deleted.')

def clean():
    make_vanilla() # Game json
    remove_print_err(ASSET_DIR + '/' + MY_JSON_NAME) # My json
    # Songs
    for song in get_imported_songs():
        delete_song(song['Bank'])


# ----------------
# Helper fns
# ----------------

def get_imported_songs() -> list:
    '''Get all imported songs (list of dicts containing Bank, BPM, etc)'''
    path = ASSET_DIR + '/' + MY_JSON_NAME
    try:
        with open(path) as f:
            return json.load(f)['imported_songs']
    except:
        return []
    
def get_imported_song(name: str) -> dict | None:
    songs = get_imported_songs()
    if songs is None:
        return None
    for song in songs:
        if song['Bank'].casefold() == name.casefold():
            return song
    return None

def get_game_custom_songs_json() -> dict:
    '''Get installed custom songs, or create empty songs list if none could be read'''
    path = ASSET_DIR + '/customsongs.json'
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return { 'customLevelMusic': [] }

def check_asset_dirs():
    global ASSET_DIR
    if ASSET_DIR:
        return
    for dir in METAL_HELLSINGER_ASSET_DIRS:
        if os.path.exists(dir):
            # print(f"Found asset directory at {dir}")
            ASSET_DIR = dir
            return
    print("Couldn't find Metal Hellsinger installation folder. Try editing METAL_HELLSINGER_ASSET_DIRS at the top of the script to add where you installed the game.")
    exit(1)

def remove_print_err(path):
    try:
        os.remove(path)
    except:
        print(f"Warning: Failed to remove file {path}")

def get_vanilla_level_name(req_level: str) -> str | None:
    for name in LEVEL_NAMES:
        if name.casefold() == req_level.casefold():
            return name
    return None

# ----------------
# Args parser & dispatch
# ----------------

def help_exit():
    print(f'Usage: {sys.argv[0]} <command> <command_parameters>')
    print('Valid Commands:')
    print('list / imported:')
    print('   lists all imported songs.')
    print('installed:')
    print('   lists all installed songs, i.e. current mappings in customsongs.json.')
    print('info <songName>:')
    print('   Shows metadata for the given song.')
    print('import <zip_path>:')
    print('   imports a zip file containing a .bank file and a customsongs.json, so that the song may be installed to a stage.')
    print('install / install-main <level_name> <song_name>:')
    print('   installs/associates the previously-imported song to a level (as the stage music).')
    print('install-boss <level_name> <song_name>:')
    print('   installs/associates the previously-imported song to a level (as the boss music).')
    print('uninstall / uninstall-main <level_name>:')
    print('   uninstalls/disassociates the previously-imported song from a level (for stage music).')
    print('uninstall-boss <level_name>:')
    print('   uninstalls/disassociates the previously-imported song to a level (for boss music).')
    print('vanilla / clear:')
    print('   uninstalls/unregisters all songs, while keeping them imported.')
    print('delete <song_name>:')
    print('   unimport and a custom song and delete its bank file.')
    print('delete-all / clean:')
    print('   unimport all songs, delete their bank files, and delete customsongs.json and this program\'s imported songs json.')
    print('help:')
    print('   displays this message.')
    exit(0)

# Maps CLI command names to function references
fn_dispatch_table = {
    'list': do_list,
    'imported': do_list,

    'installed': installed,

    'info': info,

    'import': do_import,

    'install': set_main_music,
    'install-main': set_main_music,

    'install-boss': set_boss_music,

    'uninstall': remove_main_music,
    'uninstall-main': remove_main_music,

    'uninstall-boss': remove_boss_music,

    'vanilla': make_vanilla,
    'clear':   make_vanilla,

    'delete': delete_song,
    
    'delete-all': clean,
    'clean': clean,

    'help': help_exit,
}

if __name__ == '__main__':
    args = sys.argv[1:]  # Don't care about invoked script name
    if len(args) == 0:
        help_exit()

    cmd = args[0]
    args = args[1:]

    if cmd not in fn_dispatch_table.keys():
        print(f'Invalid command.')
        help_exit()
    
    fn = fn_dispatch_table[cmd]

    # Now we have something like cmd='level-music', args=['Voke', 'My Song'].
    # But if user doesn't enter song name in quotes on command line, I will receive args=['Voke', 'My', 'Song'].
    # Assist the user by combining all args after the first one into one arg, separated by spaces.
    if len(args) > 2 and (cmd.startswith('install') or cmd == 'info'):
        args = [args[0], ' '.join(args[1:])]
    
    # Same thing but for song name as first and only parameter
    if len(args) > 1 and (cmd.startswith('delete') or cmd == 'clean'):
        args = [' '.join(args)]

    # Use reflection to check # of args is correct (probably bad)
    num_params = len(signature(fn).parameters)
    if len(args) != num_params:
        print(f'Command {cmd} expects {num_params} parameters; got {len(args)}.')
        help_exit()

    # Setup and dispatch
    check_asset_dirs()
    fn(*args)