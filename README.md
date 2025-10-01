# Mixtaper 

A shitty, cobbled together application to create mixtapes. I've done way too many of these - be happy with regular playlists. Very barebones GUI not withstanding (I avoid them whenever possible), this has made my personal experience creating mixtapes more enjoyable, therefore I want to share it.

## Features  
- **Tape Management:** Configure tape length (30, 45, 60, 90, 120, or 180 minutes), also supports custom lengths.
- **Library Management:** Load, search, and organize audio files (MP3, WAV, FLAC).  
- **Mixtape Creation:** Add, reorder, or remove songs for Side A and Side B.  
- **Playback:** Preview each side of the mixtape directly in the app.  
- **Export:** Save mixtape playlists or export the songs to a folder.
- **Auto Balance Sides:** Need help balancing both sides of the tape? We can brute force that!
- **Silence Tracks:** Add silence gaps. Sometimes you need breathing room between bangers, or you want to space out the agony, idc

## Requirements  
- Python 3.x  
- Required Libraries: `pygame`, `mutagen`, `tkinter`  

## Installation  
1. Clone or download the repository.  
2. Install dependencies:  
   ```pip install pygame mutagen```

Or alternatively, download `Mixtaper.exe`. I promise it isn't filled to the brim with viruses.

## Usage
1. Run the application:

    ```python mixtaper.py```

    (or execute `Mixtaper.exe`)

2. Do whatever you like, I'm not your mom, but here are some pointers:
   - You kinda have to load your library. This might take some time. (I might add incremental library updates, if you ask nicely)
   - Creating a mixtape is somewhat intuitive, the search function is a great help.
   - You should be able to play it back properly from this app, if you prefer an external player (and you should if you have self respect), the export function copies all songs to a new folder, making sure to add ````A[number]```` and ````B[number]```` to the name, so they are in order.

## Known Bugs / Issues
  - Technically the usage bar should change colour depending on how full the tape is. This however doesn't seem to work on windows.
  - You have no clear indication that the songs are still exporting, this shouldn't break anything, it just isn't intuitive.

## FAQ

### Q: Why don't you use `[tool xyz]`? It does everything this shitty project does, just better and more elegantly!
A: If I knew about `[tool xyz]`, I wouldn't have made this.

### Q: A toggle between a 70µs and 120µs EQ would be really nice! Is that something you can implement?
A: I tried. It doesn't work with pygame. PyaAudio might have worked, but that's a pain to make work across platforms, and I'd have had to manually resample songs according to your specific audio set-up. Forget it.

### Q: This GUI is so atrocious it made my eyes bleed.
A: That's not a question. 

### Q: Okay but for real, can we have an EQ?
A: Of course! Your OS should come with one, use that one.

## Notes
 - Library data is saved in library.json.
 - Yes, I know the code is messy. I hate UI design with a burning passion. Be glad it isn't a commandline application.
 - The auto-balance feature basically just shuffles songs randomly until the sides are roughly equal. Sometimes brute force is the answer. In my defense, inventory packing is unsolved, and this is rougly analogous to that.