import numpy as np
import matplotlib
import matplotlib.pyplot as plt

YELLOW   = 0
RED      = 1
BLUE     = 2
GREEN    = 3
PINK     = 4
NEUTRAL  = 5
COLOR_MAX   = 5
COLOR_COUNT = 6

class with_special_legend_func:
    """
    OH WHAT A HORRIBLE HACK THIS IS.

    So that we can do what *we* want with what
    geopandas would otherwise send off to ax.legend,
    so we can build our *own* legend
    """
    def __init__(self, w, f):
        self._w = w
        self._f = f
    def __getattr__(self, nm): return getattr(self._w, nm)
    def __setattr__(self, nm, v):
        if nm in ["_w", "_f"]:
            super().__setattr__(nm, v)
        else:
            setattr(self._w, nm, v)
    def legend(self, *args, **kwargs):
        if self._f is None: return
        if len(args) == 1:
            kwargs.setdefault("labels", args[0])
        elif len(args) == 2:
            kwargs.setdefault("handles", args[0])
            kwargs.setdefault("labels", args[1])
        elif len(args):
            raise ValueError("Too many position arguments to legend")
        return self._f(**kwargs)

def forward_legend_func(ax): return with_special_legend_func(ax, ax.legend)

class ColorSet:
    COLORS_HEX = [a[1] for a in [(YELLOW , "#E8C547"),
                                 (RED    , "#731C27"),
                                 (BLUE   , "#6096BA"),
                                 (GREEN  , "#2F4B26"),
                                 (PINK   , "#E0777D"),
                                 (NEUTRAL, "#D9CA95")]]
    def __init__(self, colors_used):
        mask = [ False ] * COLOR_COUNT
        for e in colors_used: mask[e] = True
        self._color_count = sum(mask)
        self.cmap = matplotlib.colors.ListedColormap(
            [self.COLORS_HEX[i] for i in range(COLOR_COUNT) if mask[i]],
            "medford_zoning"
        )
        mask[0] = int(mask[0])
        for i in range(1, COLOR_COUNT):
            mask[i] = mask[i] + mask[i - 1]
            assert(mask[i] <= self._color_count)
        self.vmap = mask
    def get_color_value(self, color): return self.vmap[color] - 1
    def color_count(self): return self._color_count

def color_hex(color): return ColorSet.COLORS_HEX[color]
    
class Category:
    def __init__(self, label, color=None, cond=None):
        if color is None:
            assert (cond is None)
            color = NEUTRAL
        assert(isinstance(color, int))
        assert(isinstance(label, str))
        self.label = label
        self.color = color
        self.cond  = cond
        
def resolve_all_categories(categories, feature_count, color_set):
    assert(categories)
    it = reversed(categories)
    first = next(it)
    assert(first.cond is None)
    first_color_value = color_set.get_color_value(first.color)
    labels   = [ "" ] * color_set.color_count()
    labels[first_color_value] = first.label
    catnames = list(range(color_set.color_count()))
    colors   = np.full(feature_count, first_color_value)
    for e in it:
        color_value = color_set.get_color_value(e.color)
        labels[color_value] = e.label
        colors[e.cond] = color_value
        assert(len(e.cond) == feature_count)
    return labels, catnames, colors

def height_width(height=None, width=None, ratio=None):
    print("HEIGHT_WIDTH_IN: ", height, width, ratio)
    if sum(e is None for e in (height, width, ratio)) != 1:
        raise ValueError("Exactly one of height, width, and ratio must be None.")
    if height is None: height = width  / ratio
    if width  is None: width  = height * ratio
    print("HEIGHT_WIDTH_OUT: ", height, ratio)
    return height, width

def draw_categories(features, categories, ax=None, legend=None, legend_kwds=None,
                    region=None, **style_kwds):
    if legend_kwds is None: legend_kwds = {}
    cset = ColorSet(c.color for c in categories)
    labels, catnames, colors = resolve_all_categories(categories, len(features.geometry), cset)
    use_real_ax = (legend is None) or (legend is ax)
    fake_ax = ax if use_real_ax else with_special_legend_func(ax, legend.legend)
    if legend_kwds: legend_kwds = legend_kwds.copy()

    legend_kwds.setdefault("labels", labels)
    if region is not None:
        legend_kwds.setdefault("loc", region.key_loc)
    out = features.plot(ax=ax,
                        column=colors,
                        cmap=cset.cmap,
                        categories=catnames,
                        categorical=True,
                        legend=(legend is not None),
                        legend_kwds=legend_kwds,
                        **style_kwds)
    if region is not None:
        xmin, ymin, xmax, ymax = region.bounds()
        ax.set_xlim(xmin, xmax)
        ax.set_ylim(ymin, ymax)
    return out
