# The cassette is mapped into a 256 byte block of memory at F000-F3FF, although it
#  only uses the first two bytes. 
#
#     F000 - Write 0x03 then 0x11 to initialize the ACIA.
#            Read: 0x01 set if tape ready to read
#                  0x02 set if tape ready to write 
#
# This class emulates the Ohio Superboard II ACIA cassette interface..
#  
class Cassette:
   
    CONTROL_STATUS = 0xF000
    READ_WRITE = 0xF001
    
    RX_READY = 0x01
    TX_READY = 0x02
    
    def __init__(self):
        
        # The cassette will be virtualized through files.
        self.load_buffer = None
        self.load_buffer_len = 0
        self.load_index = 0
        
        self.save_filename = None
       
        # The cassette TX and RX status byte.
        self.acia_status = self.TX_READY
        
    def readByte(self, addr):
        # Read the RX and TX status.
        if addr == self.CONTROL_STATUS:
            return self.acia_status
 
        # Read the next byte from the file to load.
        elif addr == self.READ_WRITE:
            if self.acia_status & self.RX_READY > 0:
                if self.load_index < self.load_buffer_len:
                    b = self.load_buffer[self.load_index]
                    self.load_index += 1
                    if self.load_index == self.load_buffer_len:
                        # EOF
                        self.acia_status = self.TX_READY
                    return b
            return 0
                
                        
    def writeByte(self, addr, b):
        if addr == self.CONTROL_STATUS:
            # Control character.
            pass
        elif addr == self.READ_WRITE:
            if self.acia_status and self.TX_READY > 0 and self.save_filename != None and b > 0:
                with open(self.save_filename, 'a') as f:
                    f.write(chr(b))
    
    def callback(self, addr, value):
        if value != None:
            self.writeByte(addr, value)
        else:
            return self.readByte(addr)
       
    def load(self, filename):
        
        # If a file name returned read the file into the load buffer and 
        # setup the load index.
        if filename:
            f = open("./TAPEs/"+filename,'rb')
            self.load_buffer = f.read()
            self.load_index = 0
            self.load_buffer_len = len(self.load_buffer)
            self.acia_status = self.RX_READY
            f.close()

    def save(self, filename):
        
        if filename != "":
            
            # Remember the filename and enable the TX "buffer".
            self.save_filename = filename
            self.acia_status = self.TX_READY

            # Create an empty file.
            f = open(self.save_filename,'wb')
            f.close()
            
