# Utilities related to colors.

# A standard color-blind palette, with equalized luminance, adding another a blue.
colors = [
    (165,   54,     0,      255),
    (179,   45,     181,    255),
    (0,     114,    178,    255),
    (144,   136,    39,     255),
    (52,    142,    83,     255),
    (5,     60,     255,    255)
]

colors = [(c[0]/255.0, c[1]/255.0, c[2]/255.0, c[3]/255.0) for c in colors]
