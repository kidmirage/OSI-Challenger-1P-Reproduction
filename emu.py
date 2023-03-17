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
    CHARSET_ADDRESS = 0xD800
    KEYBOARD_ADDRESS = 0xDF00
    IO_ADDRESS = 0xE000
    CASSETTE_ADDRESS = 0xF000
    MEMORY_BLOCK = 0xF100
    MONITOR_ADDRESS = 0xF800
    
    BLACK = 0x000000
    WHITE = 0xFFFFFF
    GREEN = 0x00FF00
    AMBER = 0xFFBF00
    CAPTION_FORMAT = 'Challenger 4P ({})'
    
    VIDEO_MEMORY_SIZE = 1024
    VIDEO_ROW_SIZE = 32
    VIDEO_NUM_ROWS = 32
    
    
    def __init__(self, path=None):
        # Manage the transformation between actual key presses and what the
        #  Monitor program is expecting.
        self.keyboard = Keyboard()
        
        # Manage the ACIA cassette deck.
        self.cassette = Cassette()
    
        # Remember what is currently showing on the screen.
        self.video_cache = bytearray(self.VIDEO_MEMORY_SIZE)
        
        dir_path = os.path.dirname(os.path.realpath(__file__))
        basic = open(dir_path+"/ROMs/basic.hex", "r")  # 8K MS Basic.
        monitor = open(dir_path+"/ROMs/"+path, "r")  # 2K Monitor Program.
        charset = open(dir_path+"/ROMs/charset.hex", "r")  # 2K character generator.
        
        # Set the screen width and keyboard read (inverted or normal).
        if path == "cwmhigh.hex":
            self.VIDEO_ROW_SIZE = 64
            self.VIDEO_MEMORY_SIZE = 2048
            self.keyboard.INVERT_KEY = True
            self.CASSETTE_ADDRESS = 0xFC00
            self.cassette.CONTROL_STATUS = 0xFC00
            self.cassette.READ_WRITE = 0xFC01
            self.video_cache = bytearray(self.VIDEO_MEMORY_SIZE)
        
        
        # Define blocks of memory.  Each tuple is
        # (start_address, length, readOnly=True, value=None, valueOffset=0)
        self.mmu = MMU([
                (self.RAM_ADDRESS, 40960), # Create RAM with 40K.
                (self.BASIC_ADDRESS, 8192, True, basic), # Basic.
                (self.VIDEO_ADDRESS, self.VIDEO_MEMORY_SIZE), # Video Memory.
                (self.CHARSET_ADDRESS, 2048, True, charset), # Character Generator.
                (self.IO_ADDRESS, 6144), # Memory mapped IO
                (self.MEMORY_BLOCK, 1792), # Memory used by 4P
                (self.MONITOR_ADDRESS, 2048, True, monitor), # Advanced Monitor.
                (self.KEYBOARD_ADDRESS, 2, False, None, 0, self.keyboard.callback), # Keyboard Control.
                (self.CASSETTE_ADDRESS, 2, False, None, 0, self.cassette.callback) # Cassette Control.
                
        ])
        
        # Create the CPU with the MMU and the starting program counter address.
        self.cpu = CPU(self.mmu, 0xFF00)
        
        # Determine the monitor screen size.
        pygame.init()
        infos = pygame.display.Info()
        self.screen_width = infos.current_w
        self.screen_height = infos.current_h

        # Display variables.
        self.screen_scale = 1
        self.full_screen = False
        self.x_offset = 0
        self.y_offset = 0
        
        # If the screen has a width of 720 assume it is a composite monitor.
        if self.screen_width == 720:
            self.full_screen = True
            if self.VIDEO_ROW_SIZE == 64:
                self.x_offset = 56
                self.y_offset = 16
        else:
            self.screen_scale = 2
        
        # Define the screen.
        self.character_width = 8
        self.character_height = 8                       
        self.display_height = self.character_height * self.VIDEO_NUM_ROWS + self.y_offset
        self.display_width = self.character_width * self.VIDEO_ROW_SIZE + self.x_offset * 2
        self.show_size = (self.display_width*self.screen_scale, self.display_height*self.screen_scale)
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
        
        # Character position into the display based on integer position in video memory.
        self.x_pos = []
        self.y_pos = []
        
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
            
        # Calculate the character positions on the screen based on the integer position into the video memory.
        x = 0
        y = 0
        for i in range(self.VIDEO_MEMORY_SIZE):
            # Remember the position for this video memory offset.
            self.x_pos.append(x+self.x_offset)
            self.y_pos.append(y+self.y_offset)
            
            # Get ready for the next character.
            x += self.character_width;
            if x == self.character_width*self.VIDEO_ROW_SIZE:
                x = 0;
                y += self.character_height
        
        # Create the screen.
        if self.full_screen:
            self.show_size = (720, 480)
            self.screen = pygame.display.set_mode(self.show_size, pygame.FULLSCREEN+pygame.NOFRAME)
            pygame.mouse.set_visible(0)
        else:
            self.screen = pygame.display.set_mode(self.show_size)
            pygame.display.set_caption(self.CAPTION_FORMAT.format(path))
        
        # Build the screen here.
        print(self.show_size)
        print(self.display_width, self.display_height)
        self.setup = pygame.Surface((self.display_width, self.display_height))
        
        # Clear the screen.
        self.screen.fill(self.BLACK)
        
    
    # Update the screen with the characters from the shared display memory.
    def _refresh(self):
        """
        Draw the video memory text array on the screen.

        """
       
        # Display the whole screen if any changes have been made.
        x = 0
        y = 0
        changed = False
        for i in range(self.VIDEO_MEMORY_SIZE):
            c = self.mmu.memory[self.VIDEO_ADDRESS + i]
            
            if c != self.video_cache[i]:
                
                # Only blit the character to the screen if it's different than the current one.
                if self.hide_control_characters and c < 32:
                    # Blank control characters if switch set.
                    self.setup.blit(self.characters[32], (self.x_pos[i], self.y_pos[i]))
                else:
                    self.setup.blit(self.characters[c], (self.x_pos[i], self.y_pos[i])) 
                
                # Remember that the screen has been uopdated and what it was changed to.
                self.video_cache[i] = c
                
                # Have to refresh screen
                changed = True

                
        if changed == True:
            pygame.transform.scale(self.setup, self.show_size, self.screen)
            pygame.display.update()
        
    
    def write_text(self, memory, address, x, y, text):
        offset = y * self.VIDEO_ROW_SIZE + x
        for i in range(0, len(text)):
            memory[address+offset+i] = ord(text[i])
            
    def save_popup(self):
        
        self.keyboard.inPopup = True
        
        memory = self.mmu.memory
        address = self.VIDEO_ADDRESS
        
        # Save the screen memory.
        save_memory = memory[address:address+self.VIDEO_MEMORY_SIZE]
        
        # Clear screen memory.
        memory[address:address+self.VIDEO_MEMORY_SIZE] = bytearray([32]*self.VIDEO_MEMORY_SIZE)
        
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
                        filename_str = os.path.dirname(os.path.realpath(__file__))+"/TAPEs/"
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
        memory[address:address+self.VIDEO_MEMORY_SIZE] = save_memory
        self._refresh()
        
        self.keyboard.inPopup = False
        
    def load_popup(self):
        
        self.keyboard.inPopup = True
        
        # Max number of files to show in the list.
        MAX_FILES = 15
        FIRST_FILE_ROW = 5
        
        memory = self.mmu.memory
        address = self.VIDEO_ADDRESS
        
        # Save the screen memory.
        save_memory = memory[address:address+self.VIDEO_MEMORY_SIZE]
        
        # Clear screen memory.
        memory[address:address+self.VIDEO_MEMORY_SIZE] = bytearray([32]*self.VIDEO_MEMORY_SIZE)
        
        # Get a list of the .BAS files in the TAPEs folder.
        basic_files = []
        for file in os.listdir("TAPEs"):
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
                                memory[address+self.VIDEO_ROW_SIZE*y:address+self.VIDEO_ROW_SIZE*y+self.VIDEO_ROW_SIZE] = bytearray([32]*self.VIDEO_ROW_SIZE)
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
                                memory[address+self.VIDEO_ROW_SIZE*y:address+self.VIDEO_ROW_SIZE*y+self.VIDEO_ROW_SIZE] = bytearray([32]*self.VIDEO_ROW_SIZE)
                                self.write_text(memory, address, x, y, basic_files[i])
                                y += 1 
                            
                        self.write_text(memory, address, 4, FIRST_FILE_ROW+selected_file, ">")
                        self._refresh()
        
        # Restore the screen.
        memory[address:address+self.VIDEO_MEMORY_SIZE] = save_memory
        self._refresh()
        
        self.keyboard.inPopup = False
    
    # Restart the monitor.
    def reset(self):
        self.cpu.r.pc = 0xff00
                
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
                elif event.type == pygame.VIDEOEXPOSE:
                    pygame.display.update()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_CAPSLOCK:
                        if pygame.key.get_mods() & pygame.KMOD_CAPS > 0:
                            self.keyboard.pressKey(event.key)
                    elif event.unicode == '\x12': # CTRL-R
                        self.reset()
                    elif event.unicode == '\x18': # CTRL-X
                        exit()
                    elif event.unicode == '\x0c': # CTRL-L
                        self.load_popup()
                    elif event.unicode == '\x13': # CTRL-S
                        self.save_popup()
                    else:
                        if event.mod & (self.keyboard.KEY_LCTRL | self.keyboard.KEY_RCTRL) > 0:
                            key = event.key
                        else:
                            try:
                                key = ord(event.unicode)
                            except:
                                key = event.key
                        self.keyboard.pressKey(key)
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_CAPSLOCK:
                        if not pygame.key.get_mods() & pygame.KMOD_CAPS > 0:
                            self.keyboard.releaseKey(event.key) 
                    else:
                        if event.mod & (self.keyboard.KEY_LCTRL | self.keyboard.KEY_RCTRL) > 0:
                            key = event.key
                        else:
                            try:
                                key = ord(event.unicode)
                            except:
                                key = event.key
                        self.keyboard.releaseKey(key)
                        
            # This will run the CPU for about 4K cycles.
            for _ in range(500):
                self.cpu.ten_steps()
            self._refresh()
                