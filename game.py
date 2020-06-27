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
    def get_windows_path(path):
        # only works on relative paths, but hey, it's good enough for us
        return "\\\\?\\" + os.getcwd() + "\\" + path.replace("/", "\\")
        
    import ctypes
    from ctypes import wintypes
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


symlinks = []
directories = []
files = []

def mysymlink(dest, src):
    symlinks.append((dest, src))
    
def finish_links():

    print "creating directories..."
    for i in range(len(directories)):
        if i % 100 == 0:
            print "creating directories, " + str(i) + "/" + str(len(directories)) + " " + str(int(float(i)/float(len(directories))*100)) + "%"
        path = directories[i]
        real_makedirs(path)
    print "all directories created"
    
    print "creating files..."
    for i in range(len(files)):
        if i % 100 == 0:
            print "creating files, " + str(i) + "/" + str(len(files)) + " " + str(int(float(i)/float(len(files))*100)) + "%"
        path = files[i]
        real_create_file(path)
    print "all files created"
    
    print "creating links..."
    for i in range(len(symlinks)):
        if i % 100 == 0:
            print "creating links, " + str(i) + "/" + str(len(symlinks)) + " " + str(int(float(i)/float(len(symlinks))*100)) + "%"
        pair = symlinks[i]
        real_make_link(pair[0], pair[1])
    print "all links created"        
        

def real_make_link(dest, src):
    if sys.platform == 'win32':

        src = get_windows_path(src) + ".lnk"
        dest = get_windows_path(dest)[4:]

        powershell_command = "$WScriptShell = New-Object -ComObject WScript.Shell;$Shortcut = $WScriptShell.CreateShortcut(\"{}\"); $Shortcut.TargetPath = \"{}\"; $Shortcut.Save()".format(
            src, dest)

        subprocess.call(['powershell.exe', powershell_command])
    else:
        os.symlink(src, dest)

def myopen(filename, mode):
    if sys.platform == 'win32':  
        return open(get_windows_path(filename), mode)
    return open(filename, mode)
    
def create_file(filename):
    files.append(filename)
        
def real_create_file(filename):
    with myopen(filename, "wb"):
        pass
        
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
	

def test():

    path = 'a' * 200
    mymakedirs(path)
    mymakedirs(path + "/" + path)

    create_file(path + "/" + path  + "/asd")
        
    mymakedirs(path + "/b")


    target = path + "/" + path
    origin = path + "/b"
    linkName = "testLink"


    mysymlink(target, origin + "/" + linkName)

    #print "QQQ", os.path.isdir(get_windows_path(origin + "/" + linkName)), os.path.islink (get_windows_path(origin + "/" + linkName))
    #myrmtree(origin + "/" + linkName)
    
    finish_links()

    exit()

#test()


def getEnvStr(env):
    s = ['']

    keys = env.keys()
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
        self.suppressDirections = []

        self.messages = []

        self.levelResources = []

    def getDir(self, env):
        return self.level.baseDir + "/" + str(self.x).zfill(4) + "_" + str(self.y).zfill(4) + getEnvStr(env)

    def renderBasic(self, env):
        myDir = self.getDir(env)
        mymakedirs(myDir)

        create_file(myDir + "/DEBUG_THIS_IS_ROOM_" + str(self.x) + "_" + str(self.y))

        doors = []

        for dirName, offset in directions:
            newCoords = (self.x + offset[0], self.y + offset[1])
            if newCoords[0] < self.level.w and newCoords[0] >= 0 and newCoords[1] < self.level.h and newCoords[1] >= 0:
                toRoom = self.level.rooms[newCoords[1]][newCoords[0]]

                if toRoom.passable:
                    doors.append(dirName)


        message = None

        for m, envRequired in self.messages:
            doThisChoice = True
            for k in envRequired:
                if envRequired[k] != env[k]:
                    doThisChoice = False
                    break
            
            if doThisChoice:
                message = m
        
        if message == None:
            message = "You see a dank dungeon room before you "

            if len(doors):
                message += "with " + ("doors" if len(doors) > 1 else "a door") + " exiting to the "
               
                if len(doors) == 1:
                    message += doors[0]
                else:
                    message += ", ".join(doors[:-1]) + " and " + doors[-1]

                message += "."
            else:
                message += "with smooth walls on every side. How did you even get here?"

        
        msg = [x for x in message.split('\n') if x]
        for i in range(len(msg)):
            create_file(myDir + "/" + str(i).zfill(2) + "_" + msg[i])

        for name, dest, envChange, envRequired, useChangeFull in self.choices:
            doThisChoice = True
            for k in envRequired:
                if envRequired[k] != env[k]:
                    doThisChoice = False
                    break
            
            if not doThisChoice:
                continue
            
            if useChangeFull:
                choiceEnv = envChange
            else:
                choiceEnv = dict(env)
                for k in envChange:
                    choiceEnv[k] = envChange[k]
            self.level.renderTeleport(name, self, dest, env, choiceEnv)

        for r in self.levelResources:
            self.level.renderResourceInRoom(self, r[0], r[1], env)





    def render(self, env):
        if not self.passable:
            return


        self.renderBasic(env)

        for dirName, offset in directions:
            if dirName in self.suppressDirections:
                continue

            newCoords = (self.x + offset[0], self.y + offset[1])
            if newCoords[0] < self.level.w and newCoords[0] >= 0 and newCoords[1] < self.level.h and newCoords[1] >= 0:
                toRoom = self.level.rooms[newCoords[1]][newCoords[0]]

                if toRoom.passable:
                    self.level.renderTeleport('Move ' + dirName, self, toRoom, env, env)
        
 
class MessageRoom(Room):
    def __init__(self, level, message, extraId=None):
        super(self.__class__, self).__init__(level, -1, -1, True, '#')
        
        self.messages = [[message, {}]]
        self.extraId = extraId

    def getDir(self, env):
        sha_1 = hashlib.sha1()
        sha_1.update(self.messages[0][0])
        thisHash = sha_1.hexdigest() + str(self.extraId)
        
        return self.level.baseDir + "/message_" + thisHash + getEnvStr(env)

    def render(self, env):
        self.renderBasic(env)

               
             

class Level(object):
    def init_base(self, baseDir, w, h):
        self.baseDir = baseDir
        self.w = w
        self.h = h
        self.rooms = []
        self.specialRooms = []
        self.resources = []

        for y in range(self.h):
            row = []
            for x in range(self.w):
                row.append(Room(self, x, y, True, '*'))
            self.rooms.append(row)

    def __init__(self, baseDir, dataStr, variables):
        rows = dataStr.split()

        self.init_base(baseDir, len(rows[0]), len(rows))

        self.symToRoom = {}

        for y in range(self.h):
            for x in range(self.w):
                passable = rows[y][x] != '.'
                self.rooms[y][x] = Room(self, x, y, passable, rows[y][x])
                
                if self.rooms[y][x].symbol not in ['#', '.']:
                    self.symToRoom[self.rooms[y][x].symbol] = self.rooms[y][x]

        self.variables = variables

        self.defaultValues = {k: False for k in self.variables}

    def addSpecialRooms(self, specialRooms):
        self.specialRooms.extend(specialRooms)

    def messageRoom(self, message, extraId=None):
        r = MessageRoom(self, message, extraId)
        self.addSpecialRooms([r])
        return r

    def deathRoom(self, message, extraId=None):
        r = self.messageRoom(message + "\nYou died.", extraId)
        r.choices.append(["Restart from beginning of the level", self.symToRoom['@'], self.defaultValues, {}, True])
        return r


    def render(self):
        mymakedirs(self.baseDir)

        def perm(variables, vs, i, f):
            if i == len(variables):
                f(vs)
                return
           
            vs[variables[i]] = False
            perm(variables, vs, i+1, f)
            vs[variables[i]] = True
            perm(variables, vs, i+1, f)

        def renderOnePerm(env):
            for y in range(self.h):
                for x in range(self.w):
                    self.rooms[y][x].render(env)

            for k in self.specialRooms:
                k.render(env)

        perm(self.variables, {}, 0, renderOnePerm)

        #for r in self.resources:
        #    with myopen(self.baseDir + "/" + r[0], "wb") as f:
        #        f.write(r[1])

    def renderTeleport(self, linkName, fromRoom, toRoom, fromEnv, toEnv):
        mysymlink(toRoom.getDir(toEnv), fromRoom.getDir(fromEnv) + "/" + linkName)

    def getMap(self, hilightPos = None):
        lines = []
        for y in range(self.h):
            line = []
            for x in range(self.w):
                if hilightPos != None and hilightPos[0] == x and hilightPos[1] == y:
                    line.append('@')
                elif self.rooms[y][x].passable:
                    line.append('#')
                else:
                    line.append('.')

            lines.append("".join(line))

        return "\n".join(lines)
    
    def renderResourceInRoom(self, room, resourceName, nameInRoom, env):
        mysymlink(self.baseDir + "/" + resourceName, room.getDir(env) + "/" + nameInRoom)


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
    room = l.symToRoom['@'] 
    message = "You wake up to find yourself spread on the floor inside a cold and horrible dungeon. There is a barred door to your back,\n"
    message += " and a thin corridoor in front of you. A lit brazier guides the path ahead.\n"
    message += " You reach up and feel your head. It hurts like hell and you've got a bruise the size of a grapefruit bulging up on your forehead.\n"
    message += " Warily, you pull yourself up onto your feet."
    room.messages.append([message, {}])
    room.levelResources.append(["images_dungeon.jpg", "dungeon.jpg"])
    

    # chasm room
    room = l.symToRoom['y']
    message = "To the North, you see an open door. Through the door, you can just spot the glint of light on metal. Your eyes perk up with interest. Could it be gold...\n"
    message += "You start towards the door, and just catch yourself before you fall right off the edge of a deep, dark precipice.\n"
    message += "Between you and the North door, there's a huge crack in the rocky floor. It's about three metres wide, but you you reckon maybe you could jump it.\n"
    message += "There are also doors on the other walls of the room, on this side of the crack."
    room.messages.append([message, {}])

    deathMessage = "You take a few steps back, run up, and leap towards the door. At the midway point you see over a lump in the door frame,\n"
    deathMessage += "the glint of gold was just a puddle! You have no time for outrage however, as you slam into the other side of the precipice.\n"
    deathMessage += "Your fingers fumble for a hold, but it's too late, you've not made it. You feel the wall slide past your hands as you start to fall...\n"
    deathRoom = l.deathRoom(deathMessage)
    deathRoom.levelResources.append(["images_chasm.png", "chasm.png"])

    room.suppressDirections = ['North']
    room.choices.append(['Move North (Try to jump the gap)', deathRoom, {}, {}, False])

    # puddle room
    room = l.symToRoom['x']
    message = "You rememeber from earlier that you saw a glint of gold through a doorway.\n"
    message += "Thinking about it, you realise you've walked around the chasm, and should be in the room you could see before.\n"
    message += "You walk over to the southern door to investigate, but find nothing but a puddle with a yellow gint of light reflecting off it.\n"
    message += "Good thing you didn't risk jumping that gap for a bleedin' puddle, you think to yourself.\n"
    room.messages.append([message, {}])

    deathMessage = "You walk through the southern door, and straight into the chasm you saw earlier. Why did you do that you silly old sod...\n"
    deathRoom = l.deathRoom(deathMessage)
    deathRoom.levelResources.append(["images_cliff_walk.jpg", "you.jpg"])

    room.suppressDirections = ['South']
    room.choices.append(['Move South', deathRoom, {}, {}, False])
    
    # map room
    room = l.symToRoom['m']
    
    mapStr = "You pick up the map and have a look.\n"
    mapStr += "You realise that the map seems to show open areas with a # symbol, and the surrounding rock with .\n"
    mapStr += "You quickly work out your own position, and note it down with an @ symbol.\n"
    mapStr += "You think to yourself that this is a good system, and you should probably use it to keep track of your position,\n"
    mapStr += "and maybe use it to make new maps for yourself if you leave the mapped area (or use a piece of paper, which might be easier).\n\n\n"
    mapStr += l.getMap([room.x, room.y])
    l.resources.append(["map.txt", mapStr])

    message = "As you enter the room, your foot brushes a scroll on the floor.\n"
    message += "You bend to pick it up and have a look. You realise that it's a map! This will come in handy.\n"
    room.messages.append([message, {}])

    room.levelResources.append(["map.txt", "map.txt"])
    
    # fork room
    room = l.symToRoom['f']
    message = "You see a fork in the path ahead of you. A foul smell wafts towards your nostrils from the East passage.\n"
    message += "From the West passage, you think you can feel a slight breeze of fresh air."
    room.messages.append([message, {}])

    # key room
    room = l.symToRoom['k']

    room.choices.append(['Pick up the key', room, {"hasKey": True}, {"hasKey": False}, False])
    message = "As you enter the room, you notice a glint of something shiny poking through the dirt under your boot.\n"
    message += "You bend to examine it. It's a key! That might come in handy."
    room.messages.append([message, {"hasKey": False}])
    
    room.levelResources.append(["images_key.png", "key.png"])
   
    # door room 
    room = l.symToRoom['d']

    message = "Set deep into the wall on the North end of the room, is a large and imposing door.\n"
    message += "It is made of thick hardwood, and revolves on a masive iron hinge.\n"
    message += "Seeping around the edges is a slight breeze of some fresher air."
    room.messages.append([message, {}])

    cantOpenDoorRoom = l.messageRoom("You try and try, but the door just won't budge. It must be locked.")
    cantOpenDoorRoom.choices.append(["Ok", room, {}, {}, False])

    openDoorMessage = "You push hard at the door, but it doesn't budge an inch.\n"
    openDoorMessage += "You notice a small keyhole on the right hand side of the door.\n"
    openDoorMessage += "On a whim, you slot the key you picked up earlier into the keyhole, and twist hard. It turns!\n"
    openDoorMessage += "You push again at the door, and it slides back. A rush of fresher air hits your face.\n"
    openDoorMessage += "The door reveals a short corridoor leading to a spiral staircase, heading up towards the surface."
    goToL2Room = l.messageRoom(openDoorMessage)
    goToL2Room.choices.append(["Climb the staircase", l2.symToRoom['@'], l2.defaultValues, {}, True])
    goToL2Room.levelResources.append(["images_stairs.jpg", "stairs.jpg"])

    room.choices.append(['Go through the door', goToL2Room, {}, {"hasKey": True}, False])
    room.choices.append(['Go through the door', cantOpenDoorRoom, {}, {"hasKey": False}, False])
    
    room.levelResources.append(["images_door.jpg", "door.jpg"])

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
    l.defaultValues = {k: True for k in variables}
    l.defaultValues["sword"] = False
    l.defaultValues["shield"] = False

    for fn in os.listdir("images/l2/"):
        with myopen("images/l2/" + fn, "rb") as f:
            l.resources.append(["images_" + fn, f.read()])

    
    # start room
    room = l.symToRoom['@']
    
    startMessage = "Just as you step off the stairs onto the new level, the staircase begins to grumble and crunch behind you.\n"
    startMessage += "It collapses into a pile of rubble, leaving just a deep hole.\n"
    startMessage += "You won't be going back that way.\n" 
    startMessage += "You take a look at your map, and realise that you've left the covered area. You'll need to start making your own.\n"
    room.messages.append([startMessage, {}])

    # fork room
    room = l.symToRoom['f']

    message = "You come to a three way fork in the tunnel.\n"
    message += "You think you see a spark of light down the Northern tunnel, maybe it's the way out."
    room.messages.append([message, {}])

    # sword room
    room = l.symToRoom['s']
    swordMessage = "As you enter, you notice racks and targets scattered about the room.\n"
    swordMessage += "It appears to be some sort of armoury, but it was abandoned a long time ago and is in pretty bad shape.\n"
    swordMessage += "In one of the corners, something catches your eye. It's a sword! And it's in decent condition too."
    room.messages.append([swordMessage, {"sword": False}])

    room.choices.append(["Pick up the sword", room, {"sword": True}, {"sword": False}, False])

    # shield room
    room = l.symToRoom['h']
    shieldMessage = "There is a skeleton in the far corner of the room.\n"
    shieldMessage += "Clutched in its bony fingers is a wide wooden shield.\n"
    room.messages.append([shieldMessage, {"shield": False}])

    room.choices.append(["Pick up the shield", room, {"shield": True}, {"shield": False}, False])

    # after ogre room
    afterOgreRoom = l.symToRoom['a']
    afterOgreRoom.suppressDirections = ['South']

    afterOgreRoom.messages.append(["You are in a thin tunnel, you can see a glimmer of light at the far end.", {}])

    # exit corridoor 1
    room = l.symToRoom['b']
    message = "The light is getting brighter! You must have found a tunnel to the surface!.\n"
    room.messages.append([message, {}])
    
    room.levelResources.append(["images_tunnel.jpg", "tunnel.jpg"])

    # exit corridoor 2
    room = l.symToRoom['c']
    message = "Light! You see a cave exit before you, with leaves and roots hanging across it.\n"
    message += "You've done it! You made it out of the dungeon!\n"
    message += "REDACTED"
    message += "REDACTED"
    room.messages.append([message, {}])
    room.suppressDirections = ['North', 'East', 'South', 'West']
    room.levelResources.append(["images_winner.jpg", "winner.jpg"])


    # ogre room
    room = l.symToRoom['o']

    room.suppressDirections = ['South', 'East', 'North', 'West']
    room.levelResources.append(["images_ogre.jpg", "ogre.jpg"])

    hpTable = [(False,False,False), (False,False,True), (False,True,False), (False,True,True), (True,False,False), (True,False,True), (True,True,False), (True,True,True)]
    
    its = 0

    for playerHp in range(0, 8):
        for ogreHp in range(0, 8):
            for hasSword in [False, True]:
                for hasShield in [False, True]:
                    its+=1

                    playerBools = {"player_0": hpTable[playerHp][0], "player_1": hpTable[playerHp][1], "player_2": hpTable[playerHp][2]}
                    ogreBools = {"ogre_0": hpTable[ogreHp][0], "ogre_1": hpTable[ogreHp][1], "ogre_2": hpTable[ogreHp][2]}
                    
                    playerDamage = 1
                    ogreDamage = 3

                    if hasSword:
                        playerDamage = 2
                    if hasShield:
                        ogreDamage = 1

                    playerNextHp = max(playerHp - ogreDamage, 0)
                    ogreNextHp = max(ogreHp - playerDamage, 0)

                    playerNextBools = {"player_0": hpTable[playerNextHp][0], "player_1": hpTable[playerNextHp][1], "player_2": hpTable[playerNextHp][2]}
                    ogreNextBools = {"ogre_0": hpTable[ogreNextHp][0], "ogre_1": hpTable[ogreNextHp][1], "ogre_2": hpTable[ogreNextHp][2]}
                    

                    required = {"sword": hasSword, "shield": hasShield}
                    required.update(playerBools)
                    required.update(ogreBools)

                    def getHpStr(hp):
                        return str(int((hp/7.0) * 100))

                    message = ""
                    if playerHp == 7 and ogreHp == 7: # The player has just entered the ogre room
                        message += "As you step into the room, you hear a rumble from overhead.\n"
                        message += "A crack appears in the ceiling, followed by another, and another.\n"
                        message += "Suddenly, the whole ceiling caves in, and a three metre tall hulking great big Ogre smashes through, wielding a club the size of a tree trunk.\n"
                        message += "The rubble has blocked the door you came in by, and the only other exit is right behind the Ogre, so there's nowhere to run.\n"
                    else:
                        if hasSword:
                            message += "You swing your sword at the ogre"
                        else:
                            message += "You jump up and slug the Ogre forcefully in the face"

                        message += ", dealing " + getHpStr(playerDamage) + " damage.\n"
                        
                        message += "The Ogre swings his club at your chest"

                        if hasShield:
                            message += ", but you block with your shield. The blow still hurts quite a bit though"

                        message += ", dealing " + getHpStr(ogreDamage) + " damage.\n"

                    message += "Your HP; " + getHpStr(playerHp) + ", Ogre's HP; " + getHpStr(ogreHp)
                    room.messages.append([message, required])

                    attackMessage = "Attack the Ogre"

                    if hasSword:
                        attackMessage += " with your sword"

                    if playerNextHp > 0 and ogreNextHp > 0:
                        nextState = {}
                        nextState.update(playerNextBools)
                        nextState.update(ogreNextBools)
                        room.choices.append([attackMessage, room, nextState, required, False])
                    elif playerNextHp == 0 and ogreNextHp == 0:
                        deathMessage = "It's been a hard battle, with a worthy foe. Both you and the Ogre are near the end of your endurance.\n"
                        deathMessage += "In unison, you both attack, each one knocking the other to the ground. Your sight begins to fade.\n"
                        deathMessage += "Just as you slip away, you hear the last of the life gurgle out of the Ogre. At least you got the bastard too.\n"
                        room.choices.append([attackMessage, l.deathRoom(deathMessage, its), {}, required, False])
                    elif ogreNextHp > 0:
                        deathMessage = "You move in to attack, but you are slowed by your wounds. You fumble and miss, and the Ogre's great club comes crashing down on your head.\n"
                        deathMessage += "The world fades to black...\n"
                        room.choices.append([attackMessage, l.deathRoom(deathMessage, its), {}, required, False])
                    else:
                        message = "The Ogre is on its last legs. It aims a sideways blow at your head, but you effortlessly deflect it with your shield.\n"
                        message += "You use the lunging momentum from the parry to swoop in under his guard, and slam your sword upwards into his head.\n"
                        message += "The great frame topples, and you just manage to prance out of the way before he lands on you.\n"
                        message += "You have other problems though, the roof is still caving in! You can see the exit not far from you behind the corpse of the Ogre.\n"
                        message += "You make a run for it and just get through before the whole ceiling falls in, barring the way back.\n"
                        winRoom = l.messageRoom(message, its)
                        winRoom.choices.append(["Ok", afterOgreRoom, {}, {}, False])
                        room.choices.append([attackMessage, winRoom, {}, required, False])
    return l


def __main__():
    print "cleaning up..."
    if myexists(".game"):
        myrmtree(".game")
        
    if myexists("Start Playing"):
        os.remove("Start Playing")
    if myexists("Start Playing.lnk"):
        os.remove("Start Playing.lnk")
        
    print "cleanup done"

    print "generating lists..."
    l2 = get_l2()
    l1 = get_l1(l2)

    l2.render()
    l1.render()
    print "generating lists done"

    # set up a start point
    startRoom = l1.symToRoom['@'] 

    mysymlink(startRoom.getDir(startRoom.level.defaultValues), "Start Playing")

    finish_links()
    
if __name__ == "__main__":
    __main__()

