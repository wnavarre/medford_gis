import matplotlib.pyplot as plt


def display(s):
    fix, ax = plt.subplots(1, 1)
    s.plot(ax=ax)
    fix.show()

def feet_to_meters(feet):
    return feet * 0.3048
