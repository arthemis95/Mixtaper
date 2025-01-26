# Cassette Mixtape Tool  

A shitty, cobbled together application to create mixtapes. I've done way too many of these
be happy with regular playlists.

## Features  
- **Tape Management:** Configure tape length (30, 60, 90, or 120 minutes).  
- **Library Management:** Load, search, and organize audio files (MP3, WAV, FLAC).  
- **Mixtape Creation:** Add, reorder, or remove songs for Side A and Side B.  
- **Playback:** Preview each side of the mixtape directly in the app.  
- **Export:** Save mixtape playlists or export the songs to a folder.  

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

## Known Bugs / Issues / General thoughts
  - Technically the usage bar should change colour depending on how full the tape is. This hower doesn't seem to work on windows.
  - You have no clear indication that the songs are still exporting, this shouldn't break anything, it just isn't intuitive.
  - Not a bug again, but adding a 120µs and 70µs EQ could be nice.

## Notes
 - Library data is saved in library.json.
 - Mixtapes are saved/exported as JSON files or copied to a selected directory.