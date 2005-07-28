import util

# manages location-information for a single screenplay. a "location" is a
# single place that can be referred to using multiple scene names, e.g.
#  INT. MOTEL ROOM - DAY
#  INT. MOTEL ROOM - DAY - 2 HOURS LATER
#  INT. MOTEL ROOM - NIGHT
class Locations:
    def __init__(self):
        # a list of lists of strings, where the inner lists list scene
        # names to combine into one location. e.g.
        # [
        #  [
        #   "INT. ROOM 413 - DAY",
        #   "INT. ROOM 413 - NIGHT"
        #  ]
        # ]

        self.locations = []

    # refresh location list against the given scene names (in the format
    # returned by Screenplay.getSceneNames()). removes unknown and
    # duplicate scenes from locations, and if that results in a location
    # with 0 scenes, removes that location completely. also upper-cases
    # all the scene names, sorts the lists, first each location list's
    # scenes, and then the locations based on the first scene of the
    # location.
    def refresh(self, sceneNames):
        locs = []

        added = {}
        
        for sceneList in self.locations:
            scenes = []

            for scene in sceneList:
                name = util.upper(scene)

                if (name in sceneNames) and (name not in added):
                    scenes.append(name)
                    added[name] = None

            if scenes:
                scenes.sort()
                locs.append(scenes)

        locs.sort()
        
        self.locations = locs
