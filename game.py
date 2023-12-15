#!/usr/bin/env python3

import os
import shutil
import hashlib
import sys
import subprocess
import shutil
import base64

sys.path.append(os.path.dirname(__file__))

directions = [
    ('北', (0, -1)),
    ('东', (1, 0)),
    ('南', (0, 1)),
    ('西', (-1, 0))
]

convert_gifs_to_html = False

# The default image viewer on macos doesn't animate gifs, it shows the frames in a list.
# This is pretty shit...
if sys.platform == 'darwin':
    convert_gifs_to_html = True

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
            print("设置文件系统... " + str(int((done / total) * 100)) + "%")
        done += 1

        path = directories[i]
        real_makedirs(path)

    for i in range(len(files)):
        if i % report_interval == 0:
            print("设置文件系统.. " + str(int((done / total) * 100)) + "%")
        done += 1

        pair = files[i]
        real_create_file(pair[0], pair[1])

    for i in range(len(symlinks)):
        if i % report_interval == 0:
            print("设置文件系统... " + str(int((done / total) * 100)) + "%")
        done += 1

        pair = symlinks[i]
        real_make_link(pair[0], pair[1])


def real_make_link(dest, src):
    if sys.platform == 'win32':
        src = get_windows_path(src) + ".lnk"
        dest = get_windows_path(dest)[4:]

        swl.create_lnk(dest, src)
    elif sys.platform.startswith("linux"):
        if os.path.isdir(dest):
            with open(src, "w") as f:
                link_data = "[Desktop Entry]\n"
                link_data += "Icon=folder\n"
                link_data += "Type=Link\n"
                link_data += "URL[$e]=file://{}\n"

                f.write(link_data.format(os.path.abspath(dest)))
        else:
            os.symlink(os.path.abspath(dest), src)
    else:
        os.symlink(os.path.abspath(dest), src)


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


def obfuscate_str(string):
    # return string

    if "lookup" not in obfuscate_str.__dict__:
        # something a bit like rot13, but does numbers and some special chars too
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-_^!"
        obfuscate_str.lookup = {}
        for char in chars:
            rotate_index = chars.index(char) + int(len(chars) / 2)
            rotate_index = rotate_index % len(chars)
            obfuscate_str.lookup[char] = chars[rotate_index]

    retval = []
    for char in string:
        if char in obfuscate_str.lookup:
            retval.append(obfuscate_str.lookup[char])
        else:
            retval.append(char)

    return "".join(retval)


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
        return self.level.base_dir + "/" + obfuscate_str(str(self.x).zfill(4) + "_" + str(self.y).zfill(4) + get_env_str(env))

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
            message = "你眼前是一间阴暗的地牢 "

            if len(doors):
                message += "和 " + ("一些门" if len(doors) > 1 else "一扇门") + " 退出到 "

                if len(doors) == 1:
                    message += doors[0]
                else:
                    message += ", ".join(doors[:-1]) + " 和 " + doors[-1]

                message += "."
            else:
                message += "四面都是光滑的墙壁。你是怎么到这儿来的!"

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
                    self.level.render_teleport('移动 ' + dir_name, self, to_room, env, env)


class MessageRoom(Room):
    id = 1

    def __init__(self, level, message):
        super(self.__class__, self).__init__(level, -1, -1, True, '#')

        if message:
            self.messages = [[message, {}]]

        self.id = MessageRoom.id
        MessageRoom.id += 1

    def get_dir(self, env):
        return self.level.base_dir + "/" + obfuscate_str("message_" + str(self.id) + get_env_str(env))

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
        r = self.message_room(message + "\n你死了.")
        r.choices.append(["从关卡开始重新开始", self.sym_to_room['@'], self.default_values, {}, True])
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
            name = r[0]
            data = r[1]
            if convert_gifs_to_html and name.endswith(".gif"):
                name = name.replace(".gif", ".gif.html")
                data = b'<html><body><img src="data:image/png;base64,' + base64.b64encode(data) + b'"></body></html>'

            create_file(self.base_dir + "/" + name, data)

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
        # workaround for weird issue on windows where double clicking a shortcut to a html file doesn't open it
        if resource_name.endswith("html"):
            for r in self.resources:
                if r[0] == resource_name:
                    create_file(room.get_dir(env) + "/" + name_in_room, r[1])
                    return
            raise Exception()

        if convert_gifs_to_html:
            resource_name = resource_name.replace(".gif", ".gif.html")
            name_in_room = name_in_room.replace(".gif", ".gif.html")

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

    for fn in os.listdir(os.path.abspath(os.path.dirname(__file__)) + "/images/l1/"):
        with open(os.path.abspath(os.path.dirname(__file__)) + "/images/l1/" + fn, "rb") as f:
            l.resources.append([fn, f.read()])

    # start room
    room = l.sym_to_room['@']
    message = "你醒来发现自己躺在一个冰冷恐怖的地牢里。你的背后有一扇开着的门,\n"
    message += " 在你面前是一条狭窄的走廊。点燃的火盆指引着前方的道路.\n"
    message += " 你伸出手，摸摸你的头。疼得要命，你的额头上有一块葡萄柚大小的淤青.\n"
    message += " 你小心翼翼地站了起来."
    room.messages.append([message, {}])
    room.level_resources.append(["dungeon.gif", "dungeon.gif"])

    # chasm room
    room = l.sym_to_room['y']
    message = "往北，你看到一扇敞开的门。透过门，你只能看到金属上闪烁的光。你的眼睛充满了兴趣.\n"
    message += "会是金子吗？...\n"
    message += "你开始向门口走去，在你从黑暗的悬崖边上掉下去之前，你要抓住自己.\n"
    message += "在你和北门之间，岩石地板上有一条巨大的裂缝.\n"
    message += "它大概有三米宽，但是你觉得你可以跳过去.\n"
    message += "房间的另一面墙上也有门，就在裂缝的这一边."
    room.messages.append([message, {}])

    death_message = "你后退几步，跑上去，向门口跳去。在中间，你可以看到门框上有一个肿块,\n"
    death_message += "闪闪发光的黄金只是一个水坑!然而，你没有时间愤怒，因为你撞到了悬崖的另一边.\n"
    death_message += "你的手指摸索着要抓住，但是太晚了，你还没有抓住。当你开始下落时，你感觉到墙从你的手中滑过...\n"
    death_room = l.death_room(death_message)
    death_room.level_resources.append(["chasm.gif", "chasm.gif"])

    room.suppress_directions = ['北']
    room.choices.append(['向北移动(试着跳过缺口)', death_room, {}, {}, False])

    # puddle room
    room = l.sym_to_room['x']
    message = "你还记得早些时候你看到一道门里闪过一道金光.\n"
    message += "想想看，你意识到你已经绕着鸿沟走了一圈，应该在你之前能看到的房间里.\n"
    message += "你走到南门去调查，但什么也没发现，只有一个水坑，上面反射着黄色的光.\n"
    message += "你心里想，还好你没有冒着跳进那该死的水坑的风险.\n"
    room.messages.append([message, {}])

    death_message = "你穿过南门，直接进入你刚才看到的深渊。你为什么要那样做，你这个愚蠢的老家伙...\n"
    death_room = l.death_room(death_message)
    death_room.level_resources.append(["you.png", "you.png"])

    room.suppress_directions = ['南']
    room.choices.append(['进入 南', death_room, {}, {}, False])

    # map room
    room = l.sym_to_room['m']

    map_str = "你拿起地图看一看.\n"
    map_str += "你意识到地图上似乎用#符号表示开放区域，周围的岩石用 .\n"
    map_str += "您可以快速计算出自己的位置，并用@符号将其记录下来.\n"
    map_str += "你认为这是一个很好的系统，你应该用它来记录你的位置,\n"
    map_str += "如果你离开地图区域，可以用它来为自己制作新的地图(或者使用一张纸，这可能更容易)。.\n\n\n"
    map_str += l.get_map([room.x, room.y])
    l.resources.append(["map.txt", map_str])

    message = "当你进入房间时，你的脚在地板上擦过一个卷轴.\n"
    message += "你弯腰把它捡起来看一看。你知道这是一张地图!这个迟早会派上用场的.\n"
    room.messages.append([message, {}])


    room.level_resources.append(["map.txt", "map.txt"])

    # fork room
    room = l.sym_to_room['f']
    message = "你看到前方有个岔路口。一股恶臭从东面的通道飘向你的鼻孔.\n"
    message += "从西边的通道，你会觉得你能感觉到一阵轻微的新鲜空气."
    room.messages.append([message, {}])

    # key room
    room = l.sym_to_room['k']

    room.choices.append(['捡起钥匙', room, {"hasKey": True}, {"hasKey": False}, False])
    message = "当你走进房间的时候，你注意到一个闪亮的东西从你靴子下面的泥土里伸出来.\n"
    message += "你弯下腰去检查它。这是一把钥匙!这可能会派上用场."
    room.messages.append([message, {"hasKey": False}])


    room.level_resources.append(["key.gif", "key.gif"])

    # door room 
    room = l.sym_to_room['d']

    message = "房间北端的墙壁深处有一扇巨大而雄伟的门.\n"
    message += "它由厚厚的硬木制成，在一个巨大的铁铰链上旋转.\n"
    message += "从边缘渗透进来的是一股清新的微风."
    room.messages.append([message, {}])

    cant_open_door_room = l.message_room("你试了又试，但门就是不动。它一定是锁着的.")
    cant_open_door_room.choices.append(["Ok", room, {}, {}, False])

    open_door_message = "你使劲推门，但门一动也不动.\n"
    open_door_message += "你注意到门的右手边有一个小钥匙孔.\n"
    open_door_message += "一时兴起，你把之前拿起的钥匙插进钥匙孔，使劲拧。转动它!\n"
    open_door_message += "你再推一下门，门就滑回去了。一股清新的空气打在你的脸上.\n"
    open_door_message += "门上有一条通往螺旋楼梯的短走廊，通往地面."
    go_to_l2_room = l.message_room(open_door_message)
    go_to_l2_room.choices.append(["爬楼梯", l2.sym_to_room['@'], l2.default_values, {}, True])

    room.choices.append(['从那扇门进去', go_to_l2_room, {}, {"hasKey": True}, False])
    room.choices.append(['从那扇门进去', cant_open_door_room, {}, {"hasKey": False}, False])

    room.level_resources.append(["door.png", "door.png"])

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

    for fn in os.listdir(os.path.abspath(os.path.dirname(__file__)) + "/images/l2/"):
        with open(os.path.abspath(os.path.dirname(__file__)) + "/images/l2/" + fn, "rb") as f:
            l.resources.append([fn, f.read()])

    for fn in os.listdir(os.path.abspath(os.path.dirname(__file__)) + "/resources/l2/"):
        with open(os.path.abspath(os.path.dirname(__file__)) + "/resources/l2/" + fn, "rb") as f:
            l.resources.append([fn, f.read()])

    # start room
    room = l.sym_to_room['@']

    start_message = "就在你走下楼梯来到新的一层时，楼梯开始在你身后咕咕作响.\n"
    start_message += "它坍塌成一堆瓦砾，只留下一个深洞.\n"
    start_message += "你不会从那条路回去的.\n"
    start_message += "你看了看地图，意识到你已经离开了覆盖区域。你得开始自己做了.\n"
    room.messages.append([start_message, {}])

    # fork room
    room = l.sym_to_room['f']

    message = "你走到隧道的三岔路口.\n"
    message += "你以为在北边的隧道里看到了闪光，也许那就是出去的路."
    room.messages.append([message, {}])

    # sword room
    room = l.sym_to_room['s']
    sword_message = "当你进入，你注意到架子和目标散落在房间里.\n"
    sword_message += "它看起来像是某种军械库，但它很久以前就被遗弃了，而且情况很糟糕.\n"
    sword_message += "在一个角落里，有东西吸引了你的目光。这是一把剑!而且它的状况也很好."
    room.messages.append([sword_message, {"sword": False}])

    room.choices.append(["拿起剑", room, {"sword": True}, {"sword": False}, False])

    # shield room
    room = l.sym_to_room['h']
    shield_message = "房间远处的角落里有一具骷髅.\n"
    shield_message += "它瘦骨嶙峋的手指上抓着一个宽大的木制盾牌.\n"
    room.messages.append([shield_message, {"shield": False}])

    room.choices.append(["拿起盾牌", room, {"shield": True}, {"shield": False}, False])

    # after ogre room
    after_ogre_room = l.sym_to_room['a']
    after_ogre_room.suppress_directions = ['南']

    after_ogre_room.messages.append(["你在一条狭窄的隧道里，你可以看到远处尽头的一线曙光.", {}])

    # exit corridor 1
    room = l.sym_to_room['b']
    message = "灯越来越亮了!你一定找到了一条通往地面的隧道!.\n"
    room.messages.append([message, {}])

    room.level_resources.append(["tunnel.png", "tunnel.png"])

    # exit corridor 2
    room = l.sym_to_room['c']
    message = "光!你看到面前有一个洞穴出口，上面挂着树叶和树根.\n"
    message += "你做到了!你从地牢里出来了!\n"
    message += "恭喜你逃出了通讯录地牢!\n"
    room.messages.append([message, {}])
    room.suppress_directions = ['北', '东', '南', '西']

    room.level_resources.append(["Secret club for people who finished the game.html", "Secret club for people who finished the game.html"])


    # ogre room
    room = l.sym_to_room['o']

    room.suppress_directions = ['南', '东', '北', '西']
    room.level_resources.append(["ogre.gif", "ogre.gif"])

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
                        message += "当你走进房间时，你听到头顶传来隆隆的声音.\n"
                        message += "天花板上出现了一条裂缝，接着是另一条，又一条.\n"
                        message += "突然间，整个天花板都塌了下来，一个三米高的巨大食人魔冲了进来，手里挥舞着一根树干大小的棍棒.\n"
                        message += "碎石堵住了你进来的门，唯一的出口就在食人魔后面，所以你无处可逃.\n"
                    else:
                        if hasSword:
                            message += "你对着食人魔挥剑"
                        else:
                            message += "你跳起来猛击食人魔的脸"

                        message += ", 计算 " + get_hp_str(player_damage) + " 伤害.\n"

                        message += "食人魔挥舞着他的棍棒对准你的胸膛"

                        if hasShield:
                            message += ",但你用盾牌阻挡。不过这一击还是挺疼的"

                        message += ", 计算 " + get_hp_str(ogre_damage) + " 伤害.\n"

                    message += "你的 HP; " + get_hp_str(playerHp) + ", 食人魔的 HP; " + get_hp_str(ogreHp)
                    room.messages.append([message, required])

                    attack_message = "攻击食人魔"

                    if hasSword:
                        attack_message += " 用你的剑"

                    if player_next_hp > 0 and ogre_next_hp > 0:
                        next_state = {}
                        next_state.update(player_next_bools)
                        next_state.update(ogre_next_bools)
                        room.choices.append([attack_message, room, next_state, required, False])
                    elif player_next_hp == 0 and ogre_next_hp == 0:
                        death_message = "这是一场艰苦的战斗，与一个值得尊敬的敌人。你和食人魔都快到了忍耐的极限了.\n"
                        death_message += "你们齐声进攻，一个把另一个打倒在地。你的视力开始衰退.\n"
                        death_message += "就在你溜走的时候，你听到食人魔最后的生命汩汩地流出来。至少你也抓到那个混蛋了.\n"
                        room.choices.append([attack_message, l.death_room(death_message), {}, required, False])
                    elif ogre_next_hp > 0:
                        death_message = "你准备进攻，但是你的伤口使你的速度变慢了。你笨手笨脚，没打中，食人魔的大棍棒砸在你头上.\n"
                        death_message += "世界渐渐变黑...\n"
                        room.choices.append([attack_message, l.death_room(death_message), {}, required, False])
                    else:
                        message = "食人魔已经奄奄一息了。它瞄准你的头部侧身一击，但你毫不费力地用盾牌挡住了它.\n"
                        message += "你利用招架的冲力在他的防守下猛扑过去，把你的剑向上猛击进他的脑袋.\n"
                        message += "巨大的框架倒塌了，你只是在他落在你身上之前设法跳开了.\n"
                        message += "但你还有其他问题，屋顶还在塌陷!你可以在食人魔的尸体后面看到离你不远的出口.\n"
                        message += "你跑过去，在整个天花板塌下来之前穿过它，挡住了回去的路.\n"
                        win_room = l.message_room(message)
                        win_room.choices.append(["Ok", after_ogre_room, {}, {}, False])
                        room.choices.append([attack_message, win_room, {}, required, False])
    return l


def __main__():
    if sys.platform.startswith('linux'):
        if not shutil.which("dolphin"):
            print('You need to have the "Dolphin" file manager installed.', file=sys.stderr)
            print('It can be installed with your system package manager, by eg:', file=sys.stderr)
            print('"sudo apt install dolphin" or "sudo yum install dolphin"', file=sys.stderr)
            input('Press enter to exit')
            exit(1)

    print("generating lists...")
    l2 = get_l2()
    l1 = get_l1(l2)

    instructions_room = l1.message_room(None)
    if sys.platform == 'win32':
        instructions_room.level_resources.append(["instructions_windows.png", "instructions_windows.png"])
    elif sys.platform == 'darwin':
        instructions_room.level_resources.append(["instructions_osx.png", "instructions_osx.png"])
    elif sys.platform.startswith('linux'):
        instructions_room.level_resources.append(["instructions_linux.png", "instructions_linux.png"])

    instructions_room.choices.append(["开始(先阅读说明!)", l1.sym_to_room['@'], {}, {}, False])

    l2.render()
    l1.render()
    print("generating lists done")

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
        subprocess.call(["explorer.exe", get_windows_path(instructions_room.get_dir(instructions_room.level.default_values))])
    elif sys.platform == 'darwin':
        subprocess.Popen(["open", instructions_room.get_dir(instructions_room.level.default_values)], close_fds=True)
    elif sys.platform.startswith('linux'):
        subprocess.call(["dolphin", instructions_room.get_dir(instructions_room.level.default_values)])


if __name__ == "__main__":
    __main__()
