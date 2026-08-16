from core.models import PointResult
from core.point_ordering import order_points


def test_grouped_zigzag_keeps_codes_independent():
    pts = [
        PointResult("A", 30, 20, None), PointResult("A", 10, 20, None),
        PointResult("A", 30, 10, None), PointResult("A", 10, 10, None),
        PointResult("B", 300, 200, None), PointResult("B", 100, 200, None),
        PointResult("B", 300, 100, None), PointResult("B", 100, 100, None),
    ]
    ordered = order_points(pts, mode="GRID_ZIGZAG_WEST", group_by_name=True)
    assert [p.point.name for p in ordered] == ["A","A","A","A","B","B","B","B"]
    assert [(p.point.src_x, p.point.src_y) for p in ordered[:4]] == [(10,20),(30,20),(30,10),(10,10)]
    assert [(p.point.src_x, p.point.src_y) for p in ordered[4:]] == [(100,200),(300,200),(300,100),(100,100)]


def test_east_start_reverses_first_row_inside_each_group():
    pts = [PointResult("A",10,20,None),PointResult("A",30,20,None),PointResult("A",10,10,None),PointResult("A",30,10,None)]
    ordered = order_points(pts, mode="GRID_ZIGZAG_EAST", group_by_name=True)
    assert [(p.point.src_x,p.point.src_y) for p in ordered] == [(30,20),(10,20),(10,10),(30,10)]
    assert [p.number for p in ordered] == [1,2,3,4]
