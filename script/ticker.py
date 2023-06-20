from mapping import *
from itertools import chain

class BoolTickerResult():
    def __init__(self, bool_value):
        self.bool_value = bool_value
        self.title = None
        self.false_label = None
        self.true_label = None

def bool_ticker(features, f, region, *,
                legend=False, legend_kwds=None,
                reverse=False, true_color=None,
                false_color=None, width=None, height=None,
                count_x=1, count_y=1):
    legend = legend or (legend_kwds is not None)
    assert(true_color is not None)
    assert(false_color is not None)
    if None in (height, width):
        height, width = height_width(height, width, region.ratio())
        print("ratio=", region.ratio())
    width *= count_x
    height *= count_y
    print("width=", width)
    print("height=", height)
    fig, axes_set = plt.subplots(squeeze=True, ncols=count_x, nrows=count_y, figsize=(width, height), dpi=300)
    if (count_x * count_y) <= 1:
        axes_set = [[ axes_set ]]
    axes_set = list(chain.from_iterable(axes_set))
    #fig.tight_layout()
    PLACEHOLDER = 1
    categories = [
        Category("TRUES", true_color, PLACEHOLDER),
        Category("FALSES", false_color)
    ]
    inputs = range(count_x * count_y)
    if reverse: inputs = reversed(inputs)
    for ax, inp in zip(axes_set, inputs):
        assert(isinstance(ax, matplotlib.axes._axes.Axes))
        res = f(features, inp)
        if res is None: continue
        categories[0].cond = res.bool_value
        if legend:
            categories[0].label = res.true_label
            categories[1].label = res.false_label
        draw_categories(features, categories, legend=ax if legend else None, ax=ax, region=region,
                        legend_kwds=legend_kwds)
    return fig, axes_set
