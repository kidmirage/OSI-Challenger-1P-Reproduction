from argparse import ArgumentParser
from emu import Emulator


def main():
    arg_parser = ArgumentParser()
    arg_parser.add_argument('--filename', help='ROM file')
    args = arg_parser.parse_args()

    filename = args.filename if args.filename else 'synmon.hex'
    emu = Emulator(path=filename)
    emu.run()

if __name__ == '__main__':
    main()
