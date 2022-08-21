import pygame
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
                        self.cassette.load()
                    elif event.key == pygame.K_F2:
                        self.cassette.save()
                    else:
                        self.keyboard.pressKey(event.key)
                elif event.type == pygame.KEYUP:
                    if event.key == pygame.K_CAPSLOCK:
                        if not pygame.key.get_mods() & pygame.KMOD_CAPS > 0:
                            self.keyboard.releaseKey(event.key) 
                    else:
                        self.keyboard.releaseKey(event.key)
  
            # This will run the CPU for about 4K cycles.
            for _ in range(1000):
                self.cpu.step()
            
    
            self._refresh()
            pygame.transform.scale(self.setup, self.show_size, dest_surface=self.screen)
            pygame.display.update()
                