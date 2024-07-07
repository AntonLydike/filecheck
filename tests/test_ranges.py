from filecheck.finput import InputRange, DiscontigousRange


def test_range():
    a = InputRange(0, 15)
    assert tuple(a.ranges()) == ((0, 15),)
    b = a.restrict_end(3)
    assert tuple(b.ranges()) == ((0, 3),)


def test_discontigous_range():
    a = DiscontigousRange(0, 100)
    assert tuple(a.ranges()) == ((0, 100),)

    a.add_hole(InputRange(10, 20))
    assert tuple(a.ranges()) == ((0, 10), (20, 100))

    # overlaps in front:
    a.add_hole(InputRange(9, 19))
    assert tuple(a.ranges()) == ((0, 9), (20, 100))

    # overlaps in back:
    a.add_hole(InputRange(11, 21))
    assert tuple(a.ranges()) == ((0, 9), (21, 100))

    # add another hole:
    a.add_hole(InputRange(30, 35))
    assert tuple(a.ranges()) == ((0, 9), (21, 30), (35, 100))

    # overlap the second one completely:
    a.add_hole(InputRange(25, 40))
    assert tuple(a.ranges()) == ((0, 9), (21, 25), (40, 100))

    # overlap both:
    a.add_hole(InputRange(14, 44))
    assert tuple(a.ranges()) == ((0, 9), (44, 100))

    # add one in front:
    a.add_hole(InputRange(0, 4))
    assert tuple(a.ranges()) == ((4, 9), (44, 100))

    # construct a separate range:
    d_range = DiscontigousRange(50, 100)
    d_range.add_hole(InputRange(60, 70))
    d_range.add_hole(InputRange(71, 89))
    d_range.add_hole(InputRange(92, 101))  # try one past the back:
    assert tuple(d_range.ranges()) == ((50, 60), (70, 71), (89, 92))

    a.add_hole(d_range)
    assert tuple(a.ranges()) == ((4, 9), (44, 50), (60, 70), (71, 89), (92, 100))
