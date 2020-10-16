# How was this made?

Warning: the following explanation presumes you are familiar with programming and filesystem concepts like symbolic links. It might be fun to read even if you're not, but I couldn't say. Also, you should play the game before reading this.

In any game, the world is a big glob of state variables.
The core idea is to model that state exhaustively. For now, let's presume we only have boolean variables. We can model the world as a list of booleans, like "has_key=true,has_sword=false". In this example, we would have 2*2 = 4 possible combinations. We also have a list of "rooms", let's say maybe 3 rooms in a line, like so:

    ┌─────┬─────┬─────┐
    │_0,0_│_1,0_│_2,0_│
    └─────┴─────┴─────┘


For each room we create a room object.

Now, for each permutation of our variables, we create a folder representing each room. In psuedo-code:
``` python
foreach (var has_key in {false, true}):
    foreach (var has_sword in {false, true}):
        foreach (var folder_name in rooms):
            create_room_folder(folder_name + "_key_" + has_key + "_sword_" + has_sword)
```

So we end up with 3 * 2 * 2 = 12 folders, each one representing a position and a set of variables.

Next we make symbolic links (or shortcuts on windows) from each "room folder" to the next.

```python
foreach (var room in previously_created):
    if (var west_room = get_room_at(room.x - 1, room.y, room.variables):
        create_symbolic_link(room.path + "/Move West", west_room.path)
    if (var east_room = get_room_at(room.x + 1, room.y, room.variables):
        create_symbolic_link(room.path + "/Move East", east_room.path)

    # ... etc for north and south
```

And now we have a dungeon of folders that we can click in to move around. We have variables, but we don't have any way pf changing them.
Well, that's easy, we can just reach into a specific room and put a special symbolic link in there

```python
foreach (var has_key in {false, true}):
    foreach (var has_sword in {false, true}):
        if not has_sword:
            var room_3 = get_room_at(3, 0, {has_key, has_sword})
            create_empty_file(room_3.path + "/You see a shiny sword") # This is just a message to the player

            # The override here means that this symbolic link will always lead to a room with "sword_true" in its path
            create_symbolic_link(room_3.path + "/Pick it up", west_room.path, override_variable={has_sword=True})
```

We needed to iterate the variables again, because we want to have the special link in every version of room 3 that has sword set to false, but not in any version of room 3 that has sword set to true.

And that is pretty much how it all works. The main limiting factor is that the number of folders you need to create grows exponentially with the number of variables. You can limit this by "scoping" things, eg because you know that if the player is in a room past a locked door, then has_key must be true because they couldn't get there otherwise. I did a little bit of this, but not so much.

In the end, the current version of the game create 41,514 directories, 15,2041 files (mostly empty files with messages in their names), and 45,399 links, which makes it rather unplayable for those unfortunate enough to try running it on a mechanical hard drive.
