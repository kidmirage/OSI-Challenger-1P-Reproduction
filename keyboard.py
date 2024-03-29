import pygame
import threading
import sched, time

HAS_KEYBOARD = False
try:
    import pigpio
    HAS_KEYBOARD = True
    GPIO = pigpio.pi()
except:
    pass

# The keyboard is mapped into a 1K block of memory at DF00-DFFF, although it
#  only uses 1 byte.
#
# This class emulates the Ohio Superboard II keyboards.
#  
class Keyboard:

    KEY_RUBOUT = pygame.K_BACKSPACE
    KEY_UPARROW = pygame.K_UP
    KEY_LINEFEED = KEY_UPARROW
    KEY_RETURN = pygame.K_RETURN
    KEY_LCTRL = pygame.K_LCTRL
    KEY_RCTRL = pygame.K_RCTRL
    KEY_SHIFTLOCK = pygame.K_CAPSLOCK
    KEY_LSHIFT = pygame.K_LSHIFT
    KEY_RSHIFT = pygame.K_RSHIFT
    KEY_SPACE = pygame.K_SPACE
    KEY_ESC = pygame.K_ESCAPE
    KEY_REPEAT = pygame.K_END
    KEY_RESET = pygame.K_DELETE
    KEY_COLON = pygame.K_COLON
    
    # Physical Keyboard Pins
    KB_STROBE = 4
    KB_0 = 5    # Key code bits.
    KB_1 = 6
    KB_2 = 12
    KB_3 = 13
    KB_4 = 19
    KB_5 = 16
    KB_6 = 26
    KB_7 = 20

    """
     * There's no real storage associated with the keyboard, just an 8x8 matrix
     * of key switches.  The system writes a byte to the keyboard address which
     * activates one or more "row" lines on the matrix then reads a byte
     * which returns the "column" lines showing which switches on the selected
     * row(s) were closed.  By default all column bits are held high (so show
     * as 1) and will only be set low (show as 0) if a switch is pressed and
     * the corresponding row has been set low.
     *
     *  The keyboard matrix has the following layout:
     *
     *        C7    C6    C5    C4    C3    C2    C1    C0
     *           |     |     |     |     |     |     |     |
     *         ! |   " |   # |   $ |   % |   & |   ' |     |
     *         1 |   2 |   3 |   4 |   5 |   6 |   7 |     |
     *  R7 ------+-----+-----+-----+-----+-----+-----+-----+
     *         ( |   ) |(1)  |   * |   = | RUB |     |     |
     *         8 |   9 |   0 |   : |   - | OUT |     |     |
     *  R6 ------+-----+-----+-----+-----+-----+-----+-----+
     *         > |   \ |     |(2)  |     |     |     |     |
     *         . |   L |   O |   ^ |  CR |     |     |     |
     *  R5 ------+-----+-----+-----+-----+-----+-----+-----+
     *           |     |     |     |     |     |     |     |
     *         W |   E |   R |   T |   Y |   U |   I |     |
     *  R4 ------+-----+-----+-----+-----+-----+-----+-----+
     *           |     |     |     |     |  LF |   [ |     |
     *         S |   D |   F |   G |   H |   J |   K |     |
     *  R3 ------+-----+-----+-----+-----+-----+-----+-----+
     *           | ETX |     |     |     |   ] |   < |     |
     *         X |   C |   V |   B |   N |   M |   , |     |
     *  R2 ------+-----+-----+-----+-----+-----+-----+-----+
     *           |     |     |     |   ? |   + |   @ |     |
     *         Q |   A |   Z |space|   / |     |   P |     |
     *  R1 ------+-----+-----+-----+-----+-----+-----+-----+
     *      (3)  |     |(4)  |     |     | left|right|SHIFT|
     *           | CTRL|     |     |     |SHIFT|SHIFT| LOCK|
     *  R0 ------+-----+-----+-----+-----+-----+-----+-----+
     *  
     *  (1) Both MONUK02 and CEGMON decode shift-0 as @
     *  
     * Notes for Ohio Superboard II keyboard:
     *  (2) This key is labeled LINE FEED
     *  (3) This position is the REPEAT key
     *  (4) This position is the ESC key
     """
    # Keys mapped to rows and columns.
    keys = []
    
    # Create an instance of the scheduler
    scheduler = sched.scheduler()
    
    # Depending on the model of Challenger the keyboard pins may have to be inverted when read and written.
    INVERT_KEY = False
    
    # Have to feed hardware keys back to the enulator if we are in a popup.
    inPopup = False

    def __init__(self):
        self.kbport = 0xff   # Default is to return nothing.

        # Build the key matrix.  One byte per row, one bit per column.
        # Keys set bits to 0 when pressed, so we start out with all bits
        # set to 1.
        self.matrix = bytearray(8)
        for i in range (len(self.matrix)):
            self.matrix[i] = 0xff
            
        # Define keys that need to have shift applied.
        self.shift_keys = {ord("="), ord("\'"), ord("\""), ord("!"), ord("#"), ord("$"), ord("%"), ord("&"), ord("("), ord(")"), ord("*"), ord("+"), ord("<"), ord(">"), ord("?")}
        
        # Define the supported keys
        self.keys = {}
        
        self.addKey('1', '!', 7, 7)
        self.addKey('2', '\"', 7, 6)
        self.addKey('3', '#', 7, 5)
        self.addKey('4', '$', 7, 4)
        self.addKey('5', '%', 7, 3)
        self.addKey('6', '&', 7, 2)
        self.addKey('7', '\'', 7, 1)
        self.addKey('8', '(', 6, 7)
        self.addKey('9', ')', 6, 6)
        self.addKey('0', '@', 6, 5)     # Note: Shift-0 decodes as @
        self.addKey(';', 0, 1, 2)
        self.addKey('-', "=", 6, 3)
        self.addKey(self.KEY_RUBOUT, 0, 6, 2)
        self.addKey('.', '>', 5, 7)
        self.addKey('L', 'l', 5, 6)  
        self.addKey('O', 'o', 5, 5)
        self.addKey(self.KEY_RETURN, 0, 5, 3)
        self.addKey('W', 'w', 4, 7)
        self.addKey('E', 'e', 4, 6)
        self.addKey('R', 'r', 4, 5)
        self.addKey('T', 't', 4, 4)
        self.addKey('Y', 'y', 4, 3)
        self.addKey('U', 'u', 4, 2)
        self.addKey('I', 'i', 4, 1)
        self.addKey('S', 's', 3, 7)
        self.addKey('D', 'd', 3, 6)
        self.addKey('F', 'f', 3, 5)
        self.addKey('G', 'g', 3, 4)
        self.addKey('H', 'h', 3, 3)
        self.addKey('J', 'j', 3, 2)
        self.addKey('K', 'k', 3, 1)  
        self.addKey('X', 'x', 2, 7)
        self.addKey('C', 'c', 2, 6)
        self.addKey('V', 'v', 2, 5)
        self.addKey('B', 'b', 2, 4)
        self.addKey('N', 'n', 2, 3)
        self.addKey('M', 'm', 2, 2)  
        self.addKey(',', '<', 2, 1)
        self.addKey('Q', 'q', 1, 7)
        self.addKey('A', 'a', 1, 6)
        self.addKey('Z', 'z', 1, 5)
        self.addKey(self.KEY_SPACE, ' ', 1, 4)
        self.addKey('/', '?', 1, 3)
        self.addKey('', '+', 1, 2)
        self.addKey('P', 'p', 1, 1)  
        self.addKey(self.KEY_SHIFTLOCK, 0, 0, 0)
        self.addKey(self.KEY_LSHIFT, 0, 0, 2)
        self.addKey(self.KEY_RSHIFT, 0, 0, 1)
        self.addKey(self.KEY_LCTRL, 0, 0, 6)
        self.addKey(self.KEY_RCTRL, 0, 0, 6)
        self.addKey('\\', 0, 5, 6)
        self.addKey(':', '*', 6, 4)    # Note implements the : key.
        self.addKey(']', 0, 2, 2)
        self.addKey('_', 0, 5, 5)
        self.addKey(self.KEY_LINEFEED, 0, 5, 4)
        self.addKey(self.KEY_ESC, 0, 0, 5)
        self.addKey(self.KEY_REPEAT, 0, 0, 7)
        self.addKey('^', 0, 2, 3)
        
        if HAS_KEYBOARD:
            GPIO.set_mode(self.KB_STROBE, pigpio.INPUT)
            GPIO.set_mode(self.KB_0, pigpio.INPUT)
            GPIO.set_mode(self.KB_1, pigpio.INPUT) 
            GPIO.set_mode(self.KB_2, pigpio.INPUT)
            GPIO.set_mode(self.KB_3, pigpio.INPUT)
            GPIO.set_mode(self.KB_4, pigpio.INPUT)
            GPIO.set_mode(self.KB_5, pigpio.INPUT)
            GPIO.set_mode(self.KB_6, pigpio.INPUT)
            GPIO.set_mode(self.KB_7, pigpio.INPUT)
            
            # Setup some callbacks for the hardware keybpard.
            GPIO.callback(self.KB_STROBE, pigpio.FALLING_EDGE, self.hw_pressKey)

        # Start with SHIFTKOCK pressed
        self.pressKey(self.KEY_SHIFTLOCK)
        
    # Clear the keyboard matrix.
    def clearMatrix(self):
        for i in range (len(self.matrix)):
            self.matrix[i] = 0xff
        
    # Dump the matrix.
    def dumpMatrix(self, label, key):
        print(label,key,end=" ")
        for i in range (len(self.matrix)):
            print(bin(self.matrix[i]), end=" ")
        print()
       
    
    # Add details of a key.
    def addKey(self, k1, k2, row, col):
        key = [row, col]
        if k1 != 0:
            try:
                self.keys[ord(k1)] = key              
            except:
                self.keys[k1] = key
                
                
        if k2 != 0:
            try:
                self.keys[ord(k2)] = key              
            except:
                self.keys[k2] = key
                

    def readByte(self):
        # Returns the column values for any row that has been set to a 0
        #  in a value previously written to the kbport address.
        b = 0xff
        k = self.kbport
        for i in range(len(self.matrix)):
            if k & 1 == 0:
                b &= self.matrix[i]
            k >>= 1
        return b

    def writeByte(self, b):
        self.kbport = b
        
    def callback(self, addr, value):
        if value != None:
            if self.INVERT_KEY == True:
                self.writeByte(value^0xFF)
            else:
                self.writeByte(value)
        else:
            if self.INVERT_KEY == True:
                return self.readByte()^0xFF
            else:
                return self.readByte()
            
    def hw_getKey(self):
        key = 0
        if HAS_KEYBOARD:
            if GPIO.read(self.KB_0): key = key | 0b00000001
            if GPIO.read(self.KB_1): key = key | 0b00000010
            if GPIO.read(self.KB_2): key = key | 0b00000100
            if GPIO.read(self.KB_3): key = key | 0b00001000
            if GPIO.read(self.KB_4): key = key | 0b00010000
            if GPIO.read(self.KB_5): key = key | 0b00100000
            if GPIO.read(self.KB_6): key = key | 0b01000000
            if GPIO.read(self.KB_7): key = key | 0b10000000
        return key
    
    # Handle hardware keys presses and releases.
    def hw_pressKey(self, channel, edge, tick):
        key = self.hw_getKey()
        
        # Handle CTRL-C. Have to ensure that ctrl gets registered.
        if key == 3:
            # Send the CTRL signal and a C.
            self.pressKey(self.KEY_LCTRL)
            self.pressKey(99)
            
            # Schedule a key release for both the CTRL signal and C.
            self.scheduler.enter(.1, 1, self.releaseKey, argument=(self.KEY_LCTRL,))
            self.scheduler.enter(.1, 1, self.releaseKey, argument=(99,))
            self.scheduler.run()
            return
            
        # If this is one of the special CTRL keys kick them back to the emulator via the event queue.
        if key < 32:
            unicode = None
            if key == 18:
                unicode = '\x12' # CTRL-R
            elif key == 24:
                unicode = '\x18' # CTRL-X
            elif key == 12:
                unicode = '\x0c' # CTRL-L
            elif key == 19:
                unicode = '\x13' # CTRL-S
            if unicode != None:
                # Let the emulator handle these keys.
                down_event = pygame.event.Event(pygame.KEYDOWN, unicode=unicode, key=key, mod=0)
                pygame.event.post(down_event)
                return
            
        # Translate a few keys.
        if key == 91: key = 8 # RUBOUT
        if key == 9: key = 27 # ESC
        
        # If the emulator is in the load or save popup pass the key back to the emulator.
        if self.inPopup:
            # Let the emulator handle these keys.
            down_event = pygame.event.Event(pygame.KEYDOWN, unicode=chr(key), key=key, mod=0)
            pygame.event.post(down_event)
            return
        
        # Press the key and schedule a release for that key.
        self.pressKey(key)
        self.scheduler.enter(.1, 1, self.releaseKey, argument=(key,))
        self.scheduler.run()

    # Handle key presses and releases.
    def pressKey(self, key):
        if key in self.keys:
            k = self.keys[key]
            if k != None:
                self.matrix[k[0]] &= ~(1 << k[1])
                if key in self.shift_keys:
                    self.matrix[0] &= 0b11111101

    def releaseKey(self, key):
        if key in self.keys:
            k = self.keys[key]
            if k != None:
                self.matrix[k[0]] |= 1 << k[1]
                if key in self.shift_keys:
                    self.matrix[0] |= 0b00000010
