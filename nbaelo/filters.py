

def format_point_differential(differential):
    net_change = '+' if differential >= 0 else '-'

    return net_change + str(round(abs(differential), 1))


def percent(value):
    if value >= 0.99:
        return '>99%'
    if value <= 0.01:
        return '<1%'
    return "{0:.0f}%".format(value * 100)