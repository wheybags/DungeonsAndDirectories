import os
import shutil
import hashlib
import sys
import subprocess

directions = [
    ('North', (0, -1)),
    ('East', (1, 0)),
    ('South', (0, 1)),
    ('West', (-1, 0))
]

if sys.platform == 'win32':
    import swinlnk
    import ctypes
    from ctypes import wintypes


    def get_windows_path(path):
        # only works on relative paths, but hey, it's good enough for us
        return "\\\\?\\" + os.getcwd() + "\\" + path.replace("/", "\\")


    _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
    _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    _GetShortPathNameW.restype = wintypes.DWORD


    def get_short_path_name(long_name):
        """
        Gets the short path name of a given long path.
        http://stackoverflow.com/a/23598461/200291
        """
        output_buf_size = 0
        while True:
            output_buf = ctypes.create_unicode_buffer(output_buf_size)
            needed = _GetShortPathNameW(long_name, output_buf, output_buf_size)
            if output_buf_size >= needed:
                return output_buf.value
            else:
                output_buf_size = needed


    swl = swinlnk.SWinLnk()

symlinks = []
directories = []
files = []


def mysymlink(dest, src):
    symlinks.append((dest, src))


def finish_links():
    total = len(directories) + len(files) + len(symlinks)
    done = 0

    report_interval = 300

    for i in range(len(directories)):
        if i % report_interval == 0:
            print("setting up filesystem... " + str(int((done / total) * 100)) + "%")
        done += 1

        path = directories[i]
        real_makedirs(path)

    for i in range(len(files)):
        if i % report_interval == 0:
            print("setting up filesystem... " + str(int((done / total) * 100)) + "%")
        done += 1

        pair = files[i]
        real_create_file(pair[0], pair[1])

    for i in range(len(symlinks)):
        if i % report_interval == 0:
            print("setting up filesystem... " + str(int((done / total) * 100)) + "%")
        done += 1

        pair = symlinks[i]
        real_make_link(pair[0], pair[1])


def real_make_link(dest, src):
    if sys.platform == 'win32':
        src = get_windows_path(src) + ".lnk"
        dest = get_windows_path(dest)[4:]

        swl.create_lnk(dest, src)
    else:
        os.symlink(src, dest)


def myopen(filename, mode):
    if sys.platform == 'win32':
        return open(get_windows_path(filename), mode)
    return open(filename, mode)


def create_file(filename, data=None):
    files.append((filename, data))


def real_create_file(filename, data):
    with myopen(filename, "wb") as f:
        if data:
            if isinstance(data, str):
                data = data.encode('utf-8')
            f.write(data)


def mymakedirs(path):
    directories.append(path)


def real_makedirs(path):
    if sys.platform == 'win32':
        components = path.replace("\\", "/").split("/")

        current = []
        for component in components:
            current.append(component)
            current_path = "\\\\?\\" + os.getcwd() + "\\" + ("\\".join(current))

            if not os.path.exists(current_path):
                os.mkdir(current_path)
    else:
        os.makedirs(path)


def myexists(path):
    if sys.platform == 'win32':
        return os.path.exists(get_windows_path(path))
    else:
        return os.path.exists(path)


def myrmtree(path):
    if sys.platform == 'win32':
        def process(_path):
            if os.path.isdir(_path):
                for child in os.listdir(_path):
                    process(_path + "\\" + child)
                os.rmdir(_path)
            else:
                os.remove(_path)

        process(get_windows_path(path))
    else:
        shutil.rmtree(path)


def get_env_str(env):
    s = ['']

    keys = list(env.keys())
    keys.sort()
    for k in keys:
        s.append(k + "_" + str(env[k]))

    return "^".join(s)


class Room(object):
    def __init__(self, level, x, y, passable, symbol):
        self.level = level
        self.x = x
        self.y = y
        self.passable = passable
        self.symbol = symbol

        self.choices = []
        self.suppress_directions = []

        self.messages = []

        self.level_resources = []

    def get_dir(self, env):
        return self.level.base_dir + "/" + str(self.x).zfill(4) + "_" + str(self.y).zfill(4) + get_env_str(env)

    def render_basic(self, env, allow_generate_message=True):
        my_dir = self.get_dir(env)
        mymakedirs(my_dir)

        # create_file(myDir + "/DEBUG_THIS_IS_ROOM_" + str(self.x) + "_" + str(self.y))

        doors = []

        for dir_name, offset in directions:
            newCoords = (self.x + offset[0], self.y + offset[1])
            if self.level.w > newCoords[0] >= 0 and self.level.h > newCoords[1] >= 0:
                to_room = self.level.rooms[newCoords[1]][newCoords[0]]

                if to_room.passable:
                    doors.append(dir_name)

        message = None

        for m, env_required in self.messages:
            do_this_choice = True
            for k in env_required:
                if env_required[k] != env[k]:
                    do_this_choice = False
                    break

            if do_this_choice:
                message = m

        if message is None and allow_generate_message:
            message = "You see a dank dungeon room before you "

            if len(doors):
                message += "with " + ("doors" if len(doors) > 1 else "a door") + " exiting to the "

                if len(doors) == 1:
                    message += doors[0]
                else:
                    message += ", ".join(doors[:-1]) + " and " + doors[-1]

                message += "."
            else:
                message += "with smooth walls on every side. How did you even get here!"

        if message:
            msg = [x for x in message.split('\n') if x]
            for i in range(len(msg)):
                create_file(my_dir + "/" + str(i).zfill(2) + "_" + msg[i])

        for name, dest, env_change, env_required, use_change_full in self.choices:
            do_this_choice = True
            for k in env_required:
                if env_required[k] != env[k]:
                    do_this_choice = False
                    break

            if not do_this_choice:
                continue

            if use_change_full:
                choice_env = env_change
            else:
                choice_env = dict(env)
                for k in env_change:
                    choice_env[k] = env_change[k]
            self.level.render_teleport(name, self, dest, env, choice_env)

        for r in self.level_resources:
            self.level.render_resource_in_room(self, r[0], r[1], env)

    def render(self, env):
        if not self.passable:
            return

        self.render_basic(env)

        for dir_name, offset in directions:
            if dir_name in self.suppress_directions:
                continue

            new_coords = (self.x + offset[0], self.y + offset[1])
            if self.level.w > new_coords[0] >= 0 and self.level.h > new_coords[1] >= 0:
                to_room = self.level.rooms[new_coords[1]][new_coords[0]]

                if to_room.passable:
                    self.level.render_teleport('Move ' + dir_name, self, to_room, env, env)


class MessageRoom(Room):
    id = 1

    def __init__(self, level, message):
        super(self.__class__, self).__init__(level, -1, -1, True, '#')

        if message:
            self.messages = [[message, {}]]

        self.id = MessageRoom.id
        MessageRoom.id += 1

    def get_dir(self, env):
        return self.level.base_dir + "/message_" + str(self.id) + get_env_str(env)

    def render(self, env):
        self.render_basic(env, False)


class Level(object):
    def __init__(self, base_dir, data_str, variables):
        rows = data_str.split()

        self.base_dir = base_dir
        self.w = len(rows[0])
        self.h = len(rows)
        self.rooms = []
        self.special_rooms = []
        self.resources = []

        for y in range(self.h):
            row = []
            for x in range(self.w):
                row.append(Room(self, x, y, True, '*'))
            self.rooms.append(row)

        self.sym_to_room = {}

        for y in range(self.h):
            for x in range(self.w):
                passable = rows[y][x] != '.'
                self.rooms[y][x] = Room(self, x, y, passable, rows[y][x])

                if self.rooms[y][x].symbol not in ['#', '.']:
                    self.sym_to_room[self.rooms[y][x].symbol] = self.rooms[y][x]

        self.variables = variables

        self.default_values = {k: False for k in self.variables}

    def add_special_rooms(self, special_rooms):
        self.special_rooms.extend(special_rooms)

    def message_room(self, message):
        r = MessageRoom(self, message)
        self.add_special_rooms([r])
        return r

    def death_room(self, message):
        r = self.message_room(message + "\nYou died.")
        r.choices.append(["Restart from beginning of the level", self.sym_to_room['@'], self.default_values, {}, True])
        return r

    def render(self):
        mymakedirs(self.base_dir)

        def perm(variables, vs, i, f):
            if i == len(variables):
                f(vs)
                return

            vs[variables[i]] = False
            perm(variables, vs, i + 1, f)
            vs[variables[i]] = True
            perm(variables, vs, i + 1, f)

        def render_one_perm(env):
            for y in range(self.h):
                for x in range(self.w):
                    self.rooms[y][x].render(env)

            for k in self.special_rooms:
                k.render(env)

        perm(self.variables, {}, 0, render_one_perm)

        for r in self.resources:
            create_file(self.base_dir + "/" + r[0], r[1])

    def render_teleport(self, link_name, from_room, to_room, from_env, to_env):
        mysymlink(to_room.get_dir(to_env), from_room.get_dir(from_env) + "/" + link_name)

    def get_map(self, highlight_pos=None):
        lines = []
        for y in range(self.h):
            line = []
            for x in range(self.w):
                if highlight_pos is not None and highlight_pos[0] == x and highlight_pos[1] == y:
                    line.append('@')
                elif self.rooms[y][x].passable:
                    line.append('#')
                else:
                    line.append('.')

            lines.append("".join(line))

        return "\n".join(lines)

    def render_resource_in_room(self, room, resource_name, name_in_room, env):
        mysymlink(self.base_dir + "/" + resource_name, room.get_dir(env) + "/" + name_in_room)


def get_l1(l2):
    l1_raw = """
.....
.d.k.
.#.#.
.#f#.
..#..
.mx#.
.#y..
..#..
..@..
.....
    """

    variables = ["hasKey"]

    l = Level(".game/l1", l1_raw, variables)

    for fn in os.listdir("images/l1/"):
        with myopen("images/l1/" + fn, "rb") as f:
            l.resources.append(["images_" + fn, f.read()])

    # start room
    room = l.sym_to_room['@']
    message = "You wake up to find yourself spread on the floor inside a cold and horrible dungeon. There is a barred door to your back,\n"
    message += " and a thin corridor in front of you. A lit brazier guides the path ahead.\n"
    message += " You reach up and feel your head. It hurts like hell and you've got a bruise the size of a grapefruit bulging up on your forehead.\n"
    message += " Warily, you pull yourself up onto your feet."
    room.messages.append([message, {}])
    room.level_resources.append(["images_dungeon.jpg", "dungeon.jpg"])

    # chasm room
    room = l.sym_to_room['y']
    message = "To the North, you see an open door. Through the door, you can just spot the glint of light on metal. Your eyes perk up with interest.\n"
    message += "Could it be gold...\n"
    message += "You start towards the door, and just catch yourself before you fall right off the edge of a deep, dark precipice.\n"
    message += "Between you and the North door, there's a huge crack in the rocky floor.\n"
    message += "It's about three metres wide, but you you reckon maybe you could jump it.\n"
    message += "There are also doors on the other walls of the room, on this side of the crack."
    room.messages.append([message, {}])

    death_message = "You take a few steps back, run up, and leap towards the door. At the midway point you see over a lump in the door frame,\n"
    death_message += "the glint of gold was just a puddle! You have no time for outrage however, as you slam into the other side of the precipice.\n"
    death_message += "Your fingers fumble for a hold, but it's too late, you've not made it. You feel the wall slide past your hands as you start to fall...\n"
    death_room = l.death_room(death_message)
    death_room.level_resources.append(["images_chasm.png", "chasm.png"])

    room.suppress_directions = ['North']
    room.choices.append(['Move North (Try to jump the gap)', death_room, {}, {}, False])

    # puddle room
    room = l.sym_to_room['x']
    message = "You remember from earlier that you saw a glint of gold through a doorway.\n"
    message += "Thinking about it, you realise you've walked around the chasm, and should be in the room you could see before.\n"
    message += "You walk over to the southern door to investigate, but find nothing but a puddle with a yellow gint of light reflecting off it.\n"
    message += "Good thing you didn't risk jumping that gap for a bleedin' puddle, you think to yourself.\n"
    room.messages.append([message, {}])

    death_message = "You walk through the southern door, and straight into the chasm you saw earlier. Why did you do that you silly old sod...\n"
    death_room = l.death_room(death_message)
    death_room.level_resources.append(["images_cliff_walk.jpg", "you.jpg"])

    room.suppress_directions = ['South']
    room.choices.append(['Move South', death_room, {}, {}, False])

    # map room
    room = l.sym_to_room['m']

    map_str = "You pick up the map and have a look.\n"
    map_str += "You realise that the map seems to show open areas with a # symbol, and the surrounding rock with .\n"
    map_str += "You quickly work out your own position, and note it down with an @ symbol.\n"
    map_str += "You think to yourself that this is a good system, and you should probably use it to keep track of your position,\n"
    map_str += "and maybe use it to make new maps for yourself if you leave the mapped area (or use a piece of paper, which might be easier).\n\n\n"
    map_str += l.get_map([room.x, room.y])
    l.resources.append(["map.txt", map_str])

    message = "As you enter the room, your foot brushes a scroll on the floor.\n"
    message += "You bend to pick it up and have a look. You realise that it's a map! This will come in handy.\n"
    room.messages.append([message, {}])

    room.level_resources.append(["map.txt", "map.txt"])

    # fork room
    room = l.sym_to_room['f']
    message = "You see a fork in the path ahead of you. A foul smell wafts towards your nostrils from the East passage.\n"
    message += "From the West passage, you think you can feel a slight breeze of fresh air."
    room.messages.append([message, {}])

    # key room
    room = l.sym_to_room['k']

    room.choices.append(['Pick up the key', room, {"hasKey": True}, {"hasKey": False}, False])
    message = "As you enter the room, you notice a glint of something shiny poking through the dirt under your boot.\n"
    message += "You bend to examine it. It's a key! That might come in handy."
    room.messages.append([message, {"hasKey": False}])

    room.level_resources.append(["images_key.png", "key.png"])

    # door room 
    room = l.sym_to_room['d']

    message = "Set deep into the wall on the North end of the room, is a large and imposing door.\n"
    message += "It is made of thick hardwood, and revolves on a masive iron hinge.\n"
    message += "Seeping around the edges is a slight breeze of some fresher air."
    room.messages.append([message, {}])

    cant_open_door_room = l.message_room("You try and try, but the door just won't budge. It must be locked.")
    cant_open_door_room.choices.append(["Ok", room, {}, {}, False])

    open_door_message = "You push hard at the door, but it doesn't budge an inch.\n"
    open_door_message += "You notice a small keyhole on the right hand side of the door.\n"
    open_door_message += "On a whim, you slot the key you picked up earlier into the keyhole, and twist hard. It turns!\n"
    open_door_message += "You push again at the door, and it slides back. A rush of fresher air hits your face.\n"
    open_door_message += "The door reveals a short corridoor leading to a spiral staircase, heading up towards the surface."
    go_to_l2_room = l.message_room(open_door_message)
    go_to_l2_room.choices.append(["Climb the staircase", l2.sym_to_room['@'], l2.default_values, {}, True])
    go_to_l2_room.level_resources.append(["images_stairs.jpg", "stairs.jpg"])

    room.choices.append(['Go through the door', go_to_l2_room, {}, {"hasKey": True}, False])
    room.choices.append(['Go through the door', cant_open_door_room, {}, {"hasKey": False}, False])

    room.level_resources.append(["images_door.jpg", "door.jpg"])

    return l


def get_l2():
    l2_raw = """
.......
...c...
.s.b...
.#.a.h.
.#.o.#.
.##f##.
...#...
...@...
.......
    """

    variables = ["ogre_0", "ogre_1", "ogre_2", "player_0", "player_1", "player_2", "sword", "shield"]

    l = Level(".game/l2", l2_raw, variables)
    l.default_values = {k: True for k in variables}
    l.default_values["sword"] = False
    l.default_values["shield"] = False

    for fn in os.listdir("images/l2/"):
        with myopen("images/l2/" + fn, "rb") as f:
            l.resources.append(["images_" + fn, f.read()])

    # start room
    room = l.sym_to_room['@']

    start_message = "Just as you step off the stairs onto the new level, the staircase begins to grumble and crunch behind you.\n"
    start_message += "It collapses into a pile of rubble, leaving just a deep hole.\n"
    start_message += "You won't be going back that way.\n"
    start_message += "You take a look at your map, and realise that you've left the covered area. You'll need to start making your own.\n"
    room.messages.append([start_message, {}])

    # fork room
    room = l.sym_to_room['f']

    message = "You come to a three way fork in the tunnel.\n"
    message += "You think you see a spark of light down the Northern tunnel, maybe it's the way out."
    room.messages.append([message, {}])

    # sword room
    room = l.sym_to_room['s']
    sword_message = "As you enter, you notice racks and targets scattered about the room.\n"
    sword_message += "It appears to be some sort of armoury, but it was abandoned a long time ago and is in pretty bad shape.\n"
    sword_message += "In one of the corners, something catches your eye. It's a sword! And it's in decent condition too."
    room.messages.append([sword_message, {"sword": False}])

    room.choices.append(["Pick up the sword", room, {"sword": True}, {"sword": False}, False])

    # shield room
    room = l.sym_to_room['h']
    shield_message = "There is a skeleton in the far corner of the room.\n"
    shield_message += "Clutched in its bony fingers is a wide wooden shield.\n"
    room.messages.append([shield_message, {"shield": False}])

    room.choices.append(["Pick up the shield", room, {"shield": True}, {"shield": False}, False])

    # after ogre room
    after_ogre_room = l.sym_to_room['a']
    after_ogre_room.suppress_directions = ['South']

    after_ogre_room.messages.append(["You are in a thin tunnel, you can see a glimmer of light at the far end.", {}])

    # exit corridor 1
    room = l.sym_to_room['b']
    message = "The light is getting brighter! You must have found a tunnel to the surface!.\n"
    room.messages.append([message, {}])

    room.level_resources.append(["images_tunnel.jpg", "tunnel.jpg"])

    # exit corridor 2
    room = l.sym_to_room['c']
    message = "Light! You see a cave exit before you, with leaves and roots hanging across it.\n"
    message += "You've done it! You made it out of the dungeon!\n"
    message += "Congratulations on escaping from the Dungeon of Directories!\n"
    room.messages.append([message, {}])
    room.suppress_directions = ['North', 'East', 'South', 'West']
    room.level_resources.append(["images_winner.jpg", "winner.jpg"])

    # ogre room
    room = l.sym_to_room['o']

    room.suppress_directions = ['South', 'East', 'North', 'West']
    room.level_resources.append(["images_ogre.jpg", "ogre.jpg"])

    hp_table = [(False, False, False), (False, False, True), (False, True, False), (False, True, True),
                (True, False, False), (True, False, True), (True, True, False), (True, True, True)]

    for playerHp in range(0, 8):
        for ogreHp in range(0, 8):
            for hasSword in [False, True]:
                for hasShield in [False, True]:

                    player_bools = {"player_0": hp_table[playerHp][0], "player_1": hp_table[playerHp][1],
                                   "player_2": hp_table[playerHp][2]}
                    ogre_bools = {"ogre_0": hp_table[ogreHp][0], "ogre_1": hp_table[ogreHp][1],
                                 "ogre_2": hp_table[ogreHp][2]}

                    player_damage = 1
                    ogre_damage = 3

                    if hasSword:
                        player_damage = 2
                    if hasShield:
                        ogre_damage = 1

                    player_next_hp = max(playerHp - ogre_damage, 0)
                    ogre_next_hp = max(ogreHp - player_damage, 0)

                    player_next_bools = {"player_0": hp_table[player_next_hp][0], "player_1": hp_table[player_next_hp][1],
                                       "player_2": hp_table[player_next_hp][2]}
                    ogre_next_bools = {"ogre_0": hp_table[ogre_next_hp][0], "ogre_1": hp_table[ogre_next_hp][1],
                                     "ogre_2": hp_table[ogre_next_hp][2]}

                    required = {"sword": hasSword, "shield": hasShield}
                    required.update(player_bools)
                    required.update(ogre_bools)

                    def get_hp_str(hp):
                        return str(int((hp / 7.0) * 100))

                    message = ""
                    if playerHp == 7 and ogreHp == 7:  # The player has just entered the ogre room
                        message += "As you step into the room, you hear a rumble from overhead.\n"
                        message += "A crack appears in the ceiling, followed by another, and another.\n"
                        message += "Suddenly, the whole ceiling caves in, and a three metre tall hulking great big Ogre smashes through, wielding a club the size of a tree trunk.\n"
                        message += "The rubble has blocked the door you came in by, and the only other exit is right behind the Ogre, so there's nowhere to run.\n"
                    else:
                        if hasSword:
                            message += "You swing your sword at the ogre"
                        else:
                            message += "You jump up and slug the Ogre forcefully in the face"

                        message += ", dealing " + get_hp_str(player_damage) + " damage.\n"

                        message += "The Ogre swings his club at your chest"

                        if hasShield:
                            message += ", but you block with your shield. The blow still hurts quite a bit though"

                        message += ", dealing " + get_hp_str(ogre_damage) + " damage.\n"

                    message += "Your HP; " + get_hp_str(playerHp) + ", Ogre's HP; " + get_hp_str(ogreHp)
                    room.messages.append([message, required])

                    attack_message = "Attack the Ogre"

                    if hasSword:
                        attack_message += " with your sword"

                    if player_next_hp > 0 and ogre_next_hp > 0:
                        next_state = {}
                        next_state.update(player_next_bools)
                        next_state.update(ogre_next_bools)
                        room.choices.append([attack_message, room, next_state, required, False])
                    elif player_next_hp == 0 and ogre_next_hp == 0:
                        death_message = "It's been a hard battle, with a worthy foe. Both you and the Ogre are near the end of your endurance.\n"
                        death_message += "In unison, you both attack, each one knocking the other to the ground. Your sight begins to fade.\n"
                        death_message += "Just as you slip away, you hear the last of the life gurgle out of the Ogre. At least you got the bastard too.\n"
                        room.choices.append([attack_message, l.death_room(death_message), {}, required, False])
                    elif ogre_next_hp > 0:
                        death_message = "You move in to attack, but you are slowed by your wounds. You fumble and miss, and the Ogre's great club comes crashing down on your head.\n"
                        death_message += "The world fades to black...\n"
                        room.choices.append([attack_message, l.death_room(death_message), {}, required, False])
                    else:
                        message = "The Ogre is on its last legs. It aims a sideways blow at your head, but you effortlessly deflect it with your shield.\n"
                        message += "You use the lunging momentum from the parry to swoop in under his guard, and slam your sword upwards into his head.\n"
                        message += "The great frame topples, and you just manage to prance out of the way before he lands on you.\n"
                        message += "You have other problems though, the roof is still caving in! You can see the exit not far from you behind the corpse of the Ogre.\n"
                        message += "You make a run for it and just get through before the whole ceiling falls in, barring the way back.\n"
                        win_room = l.message_room(message)
                        win_room.choices.append(["Ok", after_ogre_room, {}, {}, False])
                        room.choices.append([attack_message, win_room, {}, required, False])
    return l


def __main__():
    print("generating lists...")
    l2 = get_l2()
    l1 = get_l1(l2)

    instructions_room = l1.message_room(None)
    instructions_room.level_resources.append(["images_instructions.png", "instructions.png"])
    instructions_room.choices.append(["Start (Read instructions first!)", l1.sym_to_room['@'], {}, {}, False])

    l2.render()
    l1.render()
    print("generating lists done")

    do_generate = True
    do_generate = not myexists(".game/ready")

    if do_generate:
        print("cleaning up...")
        if myexists(".game"):
            myrmtree(".game")
        print("cleanup done")

        finish_links()

        if sys.platform == 'win32':
            # windows magic to hide the folder
            ctypes.windll.kernel32.SetFileAttributesW(".game", 2)

        with open(".game/ready", "wb"):
            pass

    if sys.platform == 'win32':
        subprocess.call(["explorer.exe", "Start playing.lnk"])


if __name__ == "__main__":
    __main__()
