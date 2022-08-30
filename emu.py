import pygame
import os
from cpu import CPU
from mmu import MMU
from keyboard import Keyboard
from cassette import Cassette

class Emulator:
    """
    
    Contains 8080 CPU that runs the Sol-20 CONSOL application and uses PyGame to display the 64 x 16 text screen.
    
    """
    RAM_ADDRESS = 0x0000
    BASIC_ADDRESS = 0xA000
    VIDEO_ADDRESS = 0xD000
    CHARSET_ADDRESS = 0xD400
    KEYBOARD_ADDRESS = 0xDF00
    IO_ADDRESS = 0xE000
    CASSETTE_ADDRESS = 0xF000
    MONITOR_ADDRESS = 0xF800
    
    BLACK = 0x000000
    WHITE = 0xFFFFFF
    GREEN = 0x00FF00
    AMBER = 0xFFBF00
    CAPTION_FORMAT = 'Challenger 1P ({})'
    
    def __init__(self, path=None):
        # Manage the transformation between actual key presses and what the
        #  Monitor program is expecting.
        self.keyboard = Keyboard()
        
        # Manage the ACIA cassette deck.
        self.cassette = Cassette()
        
        basic = open("ROMS/basic.hex", "r")  # 8K MS Basic.
        monitor = open("ROMs/"+path, "r")  # 2K Monitor Program.
        charset = open("ROMS/charset.hex", "r")  # 2K character generator.
        
        # Define blocks of memory.  Each tuple is
        # (start_address, length, readOnly=True, value=None, valueOffset=0)
        self.mmu = MMU([
                (self.RAM_ADDRESS, 40960), # Create RAM with 40K.
                (self.BASIC_ADDRESS, 8192, True, basic), # Basic.
                (self.VIDEO_ADDRESS, 1024), # Video Memory.
                (self.CHARSET_ADDRESS, 2048, True, charset), # Character Generator.
                (self.KEYBOARD_ADDRESS, 256, False, None, 0, self.keyboard.callback),
                (self.IO_ADDRESS, 6144), # Character Generator.
                (self.CASSETTE_ADDRESS, 256, False, None, 0, self.cassette.callback),
                (self.MONITOR_ADDRESS, 2048, True, monitor) # Advanced Monitor.
                
        ])
        
        # Create the CPU with the MMU and the starting program counter address.
        self.cpu = CPU(self.mmu, 0xFF00)

        # Class variables.
        self.character_width = 8
        self.character_height = 8                       
        self.display_height = self.character_height * 32
        self.display_width = self.character_width * 32
        self.show_size = (self.display_width*2, self.display_height*2)
        self.current_display_line = 0
        self.cursor_position = -1
        self.cursor_character = ''
        self.cursor_x = 0
        self.cusror_y = 0
        
        # Display settings.
        self.hide_control_characters = False
        self.invert_screen = False
        self.char_foreground_color = self.WHITE
        self.char_background_color = self.BLACK
        self.color_depth = 8
        self.is_cursor = False
        self.blinking_cursor = False
        self.full_screen = False
        
        # Create the display characters based on the original C1P ROM.
        self.characters = []
        fore = self.char_foreground_color
        back = self.char_background_color
        if self.invert_screen == True:
            fore = self.char_background_color
            back = self.char_foreground_color
        for c in range(0,255):
            image = pygame.Surface((self.character_width, self.character_height), depth=self.color_depth)
            image.fill(back)

            for row in range(0,8):
                    byte = self.mmu.memory[self.CHARSET_ADDRESS+c*8+row]
                    bit = 0x80
                    for col in range(0,8):
                        if byte & bit > 0:
                            image.set_at((col, row), fore)
                        bit = bit >> 1
            self.characters.append(image)
    
        # Create the screen.
        if self.full_screen:
            self.screen = pygame.display.set_mode(self.show_size, pygame.NOFRAME+pygame.FULLSCREEN)
            pygame.mouse.set_visible(0)
        else:
            self.screen = pygame.display.set_mode(self.show_size)
            pygame.display.set_caption(self.CAPTION_FORMAT.format(path))
            
        
        # Build the screen here.
        self.setup = pygame.Surface((self.display_width, self.display_height))
                
        
        # Clear the screen.
        self.screen.fill(self.BLACK)
       
        # Define a buffer with the current screen contents.
        self.screen_buffer = bytearray(1024)
        
       
    # Blit the character passed to the display screen at the coordinates passed.
    def _blit_character(self, c, x, y):
        buffer_pos = int(x/self.character_width) + int((y/self.character_height)*32)
        buffer_c = self.screen_buffer[buffer_pos]
        if buffer_c != c:
            # Only blit the character to the screen if it's different than the current one.
            if self.hide_control_characters and c < 32:
                # Blank control characters if switch set.
                self.setup.blit(self.characters[32],(x,y))
            else:
                self.setup.blit(self.characters[c],(x,y))
            self.screen_buffer[buffer_pos] = c
    
    # Update the screen with the characters from the shared display memory.
    def _refresh(self):
        """
        Draw the 32 x 32 text array on the screen.

        """
       
        # Display the whole screen.
        x = 0
        y = 0
        for i in range(self.VIDEO_ADDRESS, self.VIDEO_ADDRESS+1024):
            c = self.mmu.memory[i]
            
            # Blit the character to the display.
            self._blit_character(c,x,y)

            # Get ready for the next character.
            x += self.character_width;
            if x == self.character_width*32:
                x = 0;
                y += self.character_height
        pygame.transform.scale(self.setup, self.show_size, dest_surface=self.screen)
        pygame.display.update()
        
    
    def write_text(self, memory, address, x, y, text):
        offset = y * 32 + x
        for i in range(0, len(text)):
            memory[address+offset+i] = ord(text[i])
            
    def save_popup(self, memory, address):
        
        # Save the screen memory.
        save_memory = memory[address:address+1024]
        
        # Clear screen memory.
        memory[address:address+1024] = bytearray([32]*1024)
        
        # Screen offsets.
        MAX_NAME_SIZE = 20
        filename = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
        filename_str = ""
        name_offset = 0
        NAME_ROW = 4
        NAME_COL = 9
        
        # Show the static text.
        self.write_text(memory, address, 4, 1, "ENTER THE FILE TO SAVE TO")
        self.write_text(memory, address, 4, NAME_ROW, "NAME:_")
        self.write_text(memory, address, 4, 10, "TYPE IN THE FILE NAME")
        self.write_text(memory, address, 4, 11, "THEN PRESS RETURN")
        
        # Show the screen to the user.
        self._refresh()
        
        valid_chars = "-_.() "
   
        # Wait for a key.
        no_key = True
        over_write = False
        while no_key:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    no_key = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        no_key = False
                    elif event.key == pygame.K_RETURN:
                        filename_str = "./TAPEs/"
                        for i in filename:
                            if i != 0:
                                filename_str += i
                            else:
                                break
                        # Check to make sure the filename is not in use.
                        if not filename_str.lower().endswith(".bas"):
                            filename_str += ".bas"
                        if os.path.exists(filename_str):
                            self.write_text(memory, address, NAME_COL+name_offset, NAME_ROW, " ")
                            self.write_text(memory, address, 4, 10, filename_str[8:] + " EXISTS.                    " )
                            self.write_text(memory, address, 4, 11, "OVERWRITE? [Y/N]_")
                            self._refresh()
                            over_write = True
                        else:
                            self.cassette.save(filename_str)
                            no_key = False
                    elif event.key == pygame.K_BACKSPACE:
                        if name_offset > 0:
                            self.write_text(memory, address, NAME_COL+name_offset, NAME_ROW, " ")
                            filename[name_offset] = 0
                            name_offset -= 1
                            self.write_text(memory, address, NAME_COL+name_offset, NAME_ROW, "_")
                            self._refresh()
                    else:
                        try:
                            key = chr(ord(event.unicode))
                        except:
                            break
                        if over_write:
                            # Just looking for a Y. Any other character skips.
                            if key == "Y" or key == "y":
                                self.cassette.save(filename_str)
                            no_key = False
                        elif str.isalpha(key) or str.isdigit(key) or key in valid_chars:
                            if name_offset < MAX_NAME_SIZE:
                                # Valid filename character.
                                self.write_text(memory, address, NAME_COL+name_offset, NAME_ROW, key)
                                filename[name_offset] = key
                                name_offset += 1
                                self.write_text(memory, address, NAME_COL+name_offset, NAME_ROW, "_")
                                self._refresh()
        # Restore the screen.
        memory[address:address+1024] = save_memory
        self._refresh()
        
    def load_popup(self, memory, address):
        
        # Max number of files to show in the list.
        MAX_FILES = 15
        FIRST_FILE_ROW = 5
        
        # Save the screen memory.
        save_memory = memory[address:address+1024]
        
        # Clear screen memory.
        memory[address:address+1024] = bytearray([32]*1024)
        
        # Get a list of the .BAS files in the TAPEs folder.
        basic_files = []
        for file in os.listdir("./TAPEs"):
            if file.lower().endswith(".bas"):
                basic_files.append(file)
                
        # Show the static text.
        self.write_text(memory, address, 4, 1, "SELECT THE FILE TO LOAD")
        self.write_text(memory, address, 5, 24, ",<       PREVIOUS FILE")
        self.write_text(memory, address, 5, 25, ".>       NEXT FILE")
        self.write_text(memory, address, 5, 26, "RETURN   SELECT FILE")
        self.write_text(memory, address, 5, 27, "ESC      CANCEL")
        
        # Show the initial list of files on the screen.
        x = 5
        y = FIRST_FILE_ROW 
        for file in basic_files:
            self.write_text(memory, address, x, y, file)
            y += 1
            if y-FIRST_FILE_ROW == MAX_FILES:
                break
        
        # Initialize list controls.
        files_offset = 0
        selected_file = 0
        last_file = MAX_FILES
        if last_file > len(basic_files):
            last_file = len(basic_files)
            
        # Show the selected file.
        self.write_text(memory, address, 4, FIRST_FILE_ROW, ">")
        
        # Show the screen to the user.
        self._refresh()
         
        # Wait for a key.
        no_key = True
        while no_key:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    no_key = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        no_key = False
                    elif event.key == pygame.K_RETURN:
                        self.cassette.load(basic_files[files_offset+selected_file])
                        no_key = False
                    elif event.key == pygame.K_PERIOD:
                        self.write_text(memory, address, 4, FIRST_FILE_ROW+selected_file, " ")
                        if selected_file < last_file-1:   
                            selected_file += 1
                        elif MAX_FILES + files_offset < len(basic_files):
                            # Adjust the file list.
                            x = 5
                            y = FIRST_FILE_ROW
                            files_offset += 1
                            for i in range(files_offset,files_offset+MAX_FILES):
                                memory[address+32*y:address+32*y+32] = bytearray([32]*32)
                                self.write_text(memory, address, x, y, basic_files[i])
                                y += 1
                        self.write_text(memory, address, 4, FIRST_FILE_ROW+selected_file, ">")
                        self._refresh()
                    elif event.key == pygame.K_COMMA:
                        self.write_text(memory, address, 4, FIRST_FILE_ROW+selected_file, " ")
                        if selected_file > 0:   
                            selected_file -= 1
                        elif files_offset > 0:
                            # Adjust the file list.
                            x = 5
                            y = FIRST_FILE_ROW
                            files_offset -= 1
                            for i in range(files_offset,files_offset+MAX_FILES):
                                memory[address+32*y:address+32*y+32] = bytearray([32]*32)
                                self.write_text(memory, address, x, y, basic_files[i])
                                y += 1 
                            
                        self.write_text(memory, address, 4, FIRST_FILE_ROW+selected_file, ">")
                        self._refresh()
        
        # Restore the screen.
        memory[address:address+1024] = save_memory
        self._refresh()
                
    def run(self):
        """
        Sets up display and starts game loop

        :return:
        """
        
        # Clear the screen.
        self.screen.fill(self.BLACK)
        pygame.display.update()
        
        # Main loop.
        while True:
            
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_CAPSLOCK:
                        if pygame.key.get_mods() & pygame.KMOD_CAPS > 0:
                            self.keyboard.pressKey(event.key) 
                    elif event.key == pygame.K_DELETE:
                        # Restart the monitor.
                        self.cpu.r.pc = 0xff00
                    elif event.key == pygame.K_F1:
                        self.load_popup(self.mmu.memory, self.VIDEO_ADDRESS)
                    elif event.key == pygame.K_F2:
                        self.save_popup(self.mmu.memory, self.VIDEO_ADDRESS)
                    elif event.key == pygame.K_F3:
                        for i in range(0, 255):
                            self.mmu.memory[self.VIDEO_ADDRESS+256+i] = i
                    else:
                        try: 
                            self.keyboard.pressKey(ord(event.unicode))
                        except:
                            self.keyboard.pressKey(event.key)
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_CAPSLOCK:
                        if not pygame.key.get_mods() & pygame.KMOD_CAPS > 0:
                            self.keyboard.releaseKey(event.key) 
                    else:
                        try:
                            self.keyboard.releaseKey(ord(event.unicode))
                        except:
                            self.keyboard.releaseKey(event.key)  
  
            # This will run the CPU for about 4K cycles.
            for _ in range(1000):
                self.cpu.step()
            
            self._refresh()
                