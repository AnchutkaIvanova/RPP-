import pytest
from triangle_class import Triangle, IncorrectTriangleSides

def test_create_triangle():
    triangle = Triangle(5, 5, 5)
    assert triangle.side1 == 5
    assert triangle.side2 == 5
    assert triangle.side3 == 5

def test_triangle_type_method():
    triangle = Triangle(4, 4, 3)
    assert triangle.triangle_type() == "isosceles"

def test_perimeter_method():
    triangle = Triangle(3, 4, 5)
    assert triangle.perimeter() == 12

def test_invalid_triangle_creation():
    with pytest.raises(IncorrectTriangleSides):
        triangle = Triangle(0, 0, 0)

if __name__ == "__main__":
    pytest.main()