# Utilities related to colors.

# A standard color-blind palette, with equalized luminance, adding another a blue.
colors = [
    ((165,   54,     0,      255), ["orange", "brown"]),
    ((179,   45,     181,    255), ["pink"]),
    ((0,     114,    178,    255), ["blue", "lightBlue", "blue1"]),
    ((144,   136,    39,     255), ["yellow"]),
    ((52,    142,    83,     255), ["green"]),
    ((5,     60,     255,    255), ["darkBlue", "blue2"])
]

colors = [((c[0][0]/255.0, c[0][1]/255.0, c[0][2]/255.0, c[0][3]/255.0), c[1]) for c in colors]

def getColor(colorId, colors):
    if isinstance(colorId, int):
        # The colorId is an index into the array of colors.
        if colorId < 0 or colorId >= len(colors):
            print("Error: color index {} must be between 0 and {}".format(colorId, len(colors) - 1))
            return None
        return colors[colorId][0]

    elif isinstance(colorId, str):
        if colorId.startswith("#"):
            # The colorId is a CSS color, a string of the format "#RRGGBB" where
            # RR, GG and BB are hex numbers for the red, green and blue channels.
            # In general, it is recommended to stick with the colors in the palette,
            # but in some cases, other colors are useful (e.g., match how NeuTu uses
            # gray for post-synaptic bodies).
            return tuple([int(colorId[i:i+2], 16) / 255 for i in (1, 3, 5)])

        else:
            # The colorId is a color name, so check for a match with the names in
            # the palette.  Do a little processing so there is a successful match for
            # "light-blue", "lightblue", "LightBlue", etc.
            id = colorId.replace("-","").lower()
            for color in colors:
                if id in [c.lower() for c in color[1]]:
                    return color[0]
            print("Error: unknown color name '{}'".format(colorId))
            return None

    else:
        print("Error: invalid color identifier '{}'".format(colorId))
        return None

# The standard palette happens to have relatively similar colors at consecutive indices.
# So for very small data sets, like just two neurons, the colors don't have enough contrast.
# To fix this problem without changing the colors for older videos with larger data sets,
# this special function mixes up the standard palette if `groupToNeuronIds` indicates that
# the data set is very small.
def shuffledColorsForSmallDataSets(groupToNeuronIds):
    n = 0
    for ids in groupToNeuronIds.values():
        n += len(ids)
    if n <= len(colors):
        newColors = colors
        newColors[0] = colors[2]
        newColors[2] = colors[0]
        newColors[3] = colors[4]
        newColors[4] = colors[3]
        return newColors
    return colors
