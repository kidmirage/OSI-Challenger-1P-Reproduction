# OSI-Challenger-1P-Reproduction
Challenger 1P emulator to be used with my OSI Challenger 1P reproduction.

So far I have a basic working emulator of a Challenger 1P personal computer running the default SYSMON monitor or alternately the more capable third party CEGMON monitor. This includes virtual display, keyboard, and cassette tapes.

This work is based on the project docmarionum1/py65emu with thanks.

Python dependencies that I know of: PyGame, pigpio

usage: python main.py [-h] [--filename FILENAME]
options:
  
  -h, --help           show this help message and exit
  
  --filename FILENAME  monitor ROM file to load. Default cegmon.hex  Optional synmon.hex, cwmhigh.hex.
                       NOTE: If you select the cwmhigh.hex monitor the display will be set to 64x16 characters. The default is 32x32
                             chracter of which only the middle 24x24 is actually used.
  
  
The emulator supports the loading and saving of basic programs to the TAPEs folder. (Very simple implementation at this point.)
- To load a basic program press CTRL-l and select the file to load from the dialog that pops up. Then enter the LOAD command at the > prompt.
- To save a basic program first enter the SAVE command, then type in LIST but do not press Enter. Press CTRL-s to select the file name to save the program to then press Return. The program will list to the screen and be save to the selected file. When the list is complete enter the LOAD command then press Space followed by Return to reset the virtual cassette.

