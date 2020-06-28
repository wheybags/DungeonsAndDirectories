# from https://github.com/bristi/swinlnk/blob/e4bccd2be6e3e6fd501c627aead5602b132243fd/swinlnk/swinlnk.py

import re
import binascii
import logging

from pathlib import PureWindowsPath

log = logging.getLogger(__name__)

DEBUG = False

if DEBUG:

    #
    # Set up logging
    #

    handler = logging.StreamHandler()

    formatter = logging.Formatter(
        '## %(levelname)s [%(asctime)s](%(name)s) %(message)s',
        datefmt='%Y%m%d %H:%M:%S'
    )
    log.setLevel(logging.DEBUG)

    handler.setFormatter(formatter)
    log.addHandler(handler)

    log.info("Running in DEBUG mode")


class SWinLnk:
    r"""

    Note that all data is passed as strings of numbers (no preceding \x)

    """
    def __init__(self):

        ###############################################################
        # Variables from the official Microsoft documentation
        ###############################################################

        # HeaderSize
        self.HeaderSize = '4c000000'
        # LinkCLSID
        self.LinkCLSID = self.convert_clsid_to_data(
            "00021401-0000-0000-c000-000000000046"
        )
        # HasLinkTargetIDList ForceNoLinkInfo
        self.LinkFlags = '01010000'

        # FILE_ATTRIBUTE_DIRECTORY
        self.FileAttributes_Directory = '10000000'
        # FILE_ATTRIBUTE_ARCHIVE
        self.FileAttributes_File = '20000000'

        self.CreationTime = '0000000000000000'
        self.AccessTime = '0000000000000000'
        self.WriteTime = '0000000000000000'

        self.FileSize = '00000000'
        self.IconIndex = '00000000'
        # SW_SHOWNORMAL
        self.ShowCommand = '01000000'
        # No Hotkey
        self.Hotkey = '0000'
        self.Reserved = '0000'  # Non-modifiable value
        self.Reserved2 = '00000000'  # Non-modifiable value
        self.Reserved3 = '00000000'  # Non-modifiable value
        self.TerminalID = '0000'  # Non-modifiable value

        # Workplace
        self.CLSID_Computer = "20d04fe0-3aea-1069-a2d8-08002b30309d"
        # Network Places
        self.CLSID_Network = "208d2c60-3aea-1069-a2d7-08002b30309d"

        ###############################################################
        # Constants found from file analysis lnk
        ###############################################################

        # Local disk
        self.PREFIX_LOCAL_ROOT = '2f'
        # File folder
        self.PREFIX_FOLDER = '310000000000000000000000'
        # File
        self.PREFIX_FILE = '320000000000000000000000'
        # Root network file server
        self.PREFIX_NETWORK_ROOT = 'c30181'
        # Network printer
        self.PREFIX_NETWORK_PRINTER = 'c302c1'

        self.END_OF_STRING = '00'

    def ascii2hex(self, ascii_string):

        data = [format(ord(x), '02x') for x in ascii_string]

        datastring = ''.join(data)

        return datastring

    def gen_idlist(self, id_item):

        # We double length since our input lacks '\x'
        id_item_len = len(id_item) * 2
        item_size = format(int(id_item_len / 4) + 2, '04x')

        slices = [
            (2, 2),
            (0, 2),
        ]

        data = [item_size[x:x + y] for x, y in slices]

        datastring = ''.join(data) + id_item

        # > format(int(72/4)+2, '04x')
        # '0014'

        # When length is used on hex strings like \x00 and we just
        # have 00, then multiply by two ;)

        return datastring

    def convert_clsid_to_data(self, clsid):
        slices = [
            (6, 2),
            (4, 2),
            (2, 2),
            (0, 2),
            (11, 2),
            (9, 2),
            (16, 2),
            (14, 2),
            (19, 4),
            (24, 12),
        ]

        data = [clsid[x:x + y] for x, y in slices]

        datastring = ''.join(data)

        return datastring

    def create_lnk(self, link_target, link_name):
        """

        :param link_target: Eg 'C:\\foo\\bar'
        :param link_name: Eg /home/john/dunno.lnk
        :return:
        """

        root_lnk = False
        network_lnk = False

        target_leaf = ''

        p = PureWindowsPath(link_target)

        if str(p).startswith('\\\\'):
            # This is a network link
            # log.debug("Identified as network link")
            network_lnk = True
            prefix_root = self.PREFIX_NETWORK_ROOT
            item_data = '1f58' + self.convert_clsid_to_data(self.CLSID_Network)

            # Eg for '\\\\islion01\\foo\\bar' we get '\\\\islion01\\foo'
            target_root = str(p.parent)[:-1]

            # If we have network path with at least one element
            if re.match(r'\\\\[^\\]+\\.*', str(p)):
                target_leaf = str(p.name)

            # If we only have an initial backslash
            if target_root == '\\':
                target_root = str(p)
        else:
            # This is local I guess
            # log.debug("Identified as non-network link")
            prefix_root = self.PREFIX_LOCAL_ROOT
            item_data = '1f50' + self.convert_clsid_to_data(self.CLSID_Computer)

            target_root = p.drive

            if len(p.parts) > 1:
                # Leaf is part without drive (and backslash)
                # Eg for 'C:\\Foo\\Bar' we get 'Foo\\Bar'
                target_leaf = str(p)[len(p.drive)+1:]

            if not target_root.endswith('\\'):
                # TODO: Not sure this is a good idea..?
                # log.debug("target_root ends with '\\'")
                target_root += '\\'

        if len(target_leaf) == 0:
            # log.debug("No target leaf so assuming root link")
            root_lnk = True

        # We select the prefix that will be used to display the shortcut icon

        if p.suffix:
            prefix_of_target = self.PREFIX_FILE
            type_target = "file"
            file_attributes = self.FileAttributes_File
        else:
            prefix_of_target = self.PREFIX_FOLDER
            type_target = "folder"
            file_attributes = self.FileAttributes_Directory

        # Convert target values to binary
        # log.debug('target_root: {}'.format(target_root))
        # log.debug('target_leaf: {}'.format(target_leaf))

        target_root = self.ascii2hex(target_root)
        # Needed from Vista and higher otherwise the link is considered
        # empty (I have not found any information about this)
        target_root = target_root + ('00' * 21)

        target_leaf = self.ascii2hex(target_leaf)

        # Create the IDLIST that represents the core of the LNK file

        if root_lnk:
            idlist_items = ''.join([
                self.gen_idlist(item_data),
                self.gen_idlist(prefix_root + target_root + self.END_OF_STRING),
            ])
        else:
            idlist_items = ''.join([
                self.gen_idlist(item_data),
                self.gen_idlist(prefix_root + target_root + self.END_OF_STRING),
                self.gen_idlist(
                    prefix_of_target + target_leaf + self.END_OF_STRING
                ),
            ])

        idlist = self.gen_idlist(idlist_items)

        with open(link_name, 'wb') as fout:
            fout.write(
                binascii.unhexlify(''.join([
                    self.HeaderSize,
                    self.LinkCLSID,
                    self.LinkFlags,
                    file_attributes,
                    self.CreationTime,
                    self.AccessTime,
                    self.WriteTime,
                    self.FileSize,
                    self.IconIndex,
                    self.ShowCommand,
                    self.Hotkey,
                    self.Reserved,
                    self.Reserved2,
                    self.Reserved3,
                    idlist,
                    self.TerminalID,
                ]))
            )
