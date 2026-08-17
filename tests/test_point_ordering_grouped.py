from core.models import PointResult
from core.point_ordering import order_points, point_code_group


def test_code_group_extracts_prefix_from_point_names():
    assert point_code_group("A1") == "A"
    assert point_code_group("A60") == "A"
    assert point_code_group("KS159") == "KS"
    assert point_code_group("As-12") == "AS"
    assert point_code_group("CHECK") == "CHECK"


def test_grouped_zigzag_keeps_codes_independent():
    pts = [
        PointResult("A1", 30, 20, None), PointResult("A2", 10, 20, None),
        PointResult("A3", 30, 10, None), PointResult("A4", 10, 10, None),
        PointResult("B1", 300, 200, None), PointResult("B2", 100, 200, None),
        PointResult("B3", 300, 100, None), PointResult("B4", 100, 100, None),
    ]
    ordered = order_points(pts, mode="GRID_ZIGZAG_WEST", group_by_name=True)
    assert [p.group for p in ordered] == ["A","A","A","A","B","B","B","B"]
    assert [(p.point.src_x, p.point.src_y) for p in ordered[:4]] == [(10,20),(30,20),(30,10),(10,10)]
    assert [(p.point.src_x, p.point.src_y) for p in ordered[4:]] == [(100,200),(300,200),(300,100),(100,100)]


def test_east_start_reverses_first_row_inside_each_group():
    pts = [PointResult("A1",10,20,None),PointResult("A2",30,20,None),PointResult("A3",10,10,None),PointResult("A4",30,10,None)]
    ordered = order_points(pts, mode="GRID_ZIGZAG_EAST", group_by_name=True)
    assert [(p.point.src_x,p.point.src_y) for p in ordered] == [(30,20),(10,20),(10,10),(30,10)]
    assert [p.number for p in ordered] == [1,2,3,4]
