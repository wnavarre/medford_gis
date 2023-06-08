import shapely

rectangle = shapely.Polygon([(0., 0.), (15.1, 0.), (15.1, 30.1), (0., 30.1)])
rect_with_chimney = shapely.Polygon([(0., 0.),
                                     (15.1, 0.),
                                     (15.1, 30.1),
                                     (7., 30.1),
                                     (6., 45.1),
                                     (0., 45.1)])
