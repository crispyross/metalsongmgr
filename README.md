# MetalSongMgr

A command-line script that manages your custom songs in Metal: Hellsinger.  
Download the .zip for a custom song, import it via the manager, and then easily install it into any level (or boss fight), even while the game is running.

# Usage

Python 3.6+ is required (I think), tested on 3.11. Open your terminal, navigate to the folder containing this script, and run commands with `python metalsongmgr.py <command>`, e.g. `python metalsongmgr.py import coolsong.zip`.  
Available commands are shown with the `help` command.

TLDR: `import` into the manager, then `install` or `install-boss` into a level.

---

1. First, download and then import any songs you may want to use using the `import` command.
   - Example: `python metalsongmgr.py import mycoolsong.zip`
   - You may check what songs you have imported using the `list` (or `imported`) command. This lists the custom songs using their "bank names", which is how you should refer to them for the rest of the commands.
   - Note: Right now, I am expecting that the .zip contains exactly one .bank file and one .json file, which contains an association with a level as main stage and/or boss music. Might need some adjustments as custom song community develops.
   - Extra note: When a song is imported, the .bank file in the .zip is extracted to `<game install folder>/Metal_Data/StreamingAssets`, and some metadata about the song is stored in `<game install folder>/Metal_Data/StreamingAssets/customsongs-mgr-imported.json`.
1. Importing a song doesn't install it into any levels in-game (or, associate the .bank file with a level). To do so, there are several commands:
   - `install` (or `install-main`) associates a previously-imported song with a level (as the main stage music). Example: `python metalsongmgr.py install "Stygia" "My Song Here"`
   - `install-boss` associates a previously-imported song with a level (as the boss music).
   - A custom song takes priority over whatever song you've selected in in-game menu.
   - Every time the game goes to that black "Enter Hell" screen with a tip and that "ding-dong" sound, it reloads the song. So, the install command takes effect at that time. **You can, for example, apply a different song, then hit ESC in a level and restart, and the song will be applied on the restart.**
1. To view what songs are installed/mapped to a level, use the `installed` command.
1. If you want to go back to using the in-game chosen song for a specific level, use the `uninstall` or `uninstall-boss` commands similar to above.

Other commands:

- If you want to go back to using the in-game chosen songs for all levels, use the `vanilla` or `clear` command. This keeps your downloaded songs imported, but removes all song-stage associations.
- If you want to **COMPLETELY REMOVE** all downloaded songs and their metadata, so that **YOU WILL NEED TO REDOWNLOAD THEM**, use the `delete-all` or `clean` command.
  - You can do this for an individual song using the `delete` commmand.
- To view info (like BPM) for a song, use the `info "Custom Song"`.
