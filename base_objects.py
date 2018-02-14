import math

from defcon import Point as DefPoint, Contour as DefContour, Glyph as DefGlyph


class Point(DefPoint):
    """Subclassed Point object that give some tools for point
    manipulation and vectorization.

    Every methods returns a new instance of either Point or Vector object

    TODO(maybe): implements __add__, __sub__
    instead/in addition of displace(), vector()
    """
    def __init__(self, x, y, segmentType=None):
        super().__init__((x,y), segmentType)

    def __repr__(self):
        return "<{} coord: ({}, {}) type: {}>".format(
            self.__class__.__name__, self.x, self.y, self.segmentType)

    def vector(self, other):
        """Return the vector of two points"""
        return Vector(other.x - self.x, other.y - self.y)

    def relative(self, other):
        """Return the vector of two points as a new point with segmentType"""
        return Point(other.x - self.x, other.y - self.y, self.segmentType)

    def distance(self, other):
        """Return the length of the vector self->other"""
        return self.vector(other).norm()

    def scale(self, n):
        return Point(self.x * n, self.y * n)

    def displace(self, vector, segmentType='line'):
        """Return a new point with coordinates = point + vector
        It differs from the Defcon Point's move method by returning a new
        point instead of updating the instance point position.
        """
        return Point(self.x + vector.x, self.y + vector.y, segmentType)

    def toSvgCommand(self):
        NotImplemented


class Vector():
    __slots__ = ('_x', '_y')

    def __init__(self, x, y):
        self._x = x
        self._y = y

    def __repr__(self):
        return "<{} coord: ({}, {})>".format(
            self.__class__.__name__, self.x, self.y)

    def _get_x(self):
        return self._x

    def _set_x(self, value):
        self._x = value

    x = property(_get_x, _set_x, doc="The x direction.")

    def _get_y(self):
        return self._y

    def _set_y(self, value):
        self._y = value

    y = property(_get_y, _set_y, doc="The y direction.")

    def norm(self):
        return math.hypot(self.x, self.y)

    def unit_vector(self):
        norm = self.norm()
        return Vector(self.x / norm, self.y / norm)

    def rotate(self, theta):
        """ Rotate vector of angle theta given in deg
        """
        rad = math.radians(theta)
        cos, sin = math.cos(rad), math.sin(rad)
        return Vector(cos * self.x - sin * self.y,
                      sin * self.x + cos * self.y)

    def scale(self, number):
        return Vector(self.x * number, self.y * number)


class Segment:
    """Helper object that give tools for intersections dectection to produce
    stroke vectorization
    """
    def __init__(self, a, b):
        self.a = a
        self.b = b if isinstance(b, Point) else b.displace(a)

    def __repr__(self):
        return "<{} points: ({},{}), ({},{})>".format(
            self.__class__.__name__, self.a.x, self.a.y, self.b.x, self.b.y)

    def vector(self):
        """ Return the vector of the line
        """
        return self.a.vector(self.b)

    def intersection(self, other, force=False):
        """ Return the intersection point of two lines
        """
        a, b, c, d = self.a, self.b, other.a, other.b
        i, j = self.vector(), other.vector()

        div = i.x * j.y - i.y * j.x

        # check if i & j are not parallel
        if div != 0:
            # k = (j.x * a.y - j.x * c.y - j.y * a.x + j.y * c.x) / div
            # return Point(a + k * i)
            m = (i.x * a.y - i.x * c.y - i.y * a.x + i.y * c.x) / div
            # check if lines intersect
            if 0 < m < 1 or force:
                return [c.displace(j.scale(m))]
            else:
                return [b, c]

    def getParallel(self, theta, distance):
        vector = self.vector().unit_vector().rotate(theta).scale(distance)
        return Segment(self.a.displace(vector), self.b.displace(vector))

    def isClockwise(self):
        vector = self.vector()
        if vector.x < 0 or vector.y < 0:
            return True
        else:
            return False


class Contour(DefContour):
    def __init__(self, points):
        super().__init__()
        for point in points:
            self.appendPoint(point)

    def getCornerProjection(self, i, distance, orientation, linejoin):
        last = 0 if i == len(self._points) - 1 else i + 1
        p1, p2, p3 = self._points[i-1], self._points[i], self._points[last]
        s1 = Segment(p1, p2).getParallel(-90 * orientation, distance)
        s2 = Segment(p2, p3).getParallel(-90 * orientation, distance)
        if linejoin == 'bevel':
            intersection = s1.intersection(s2)
        elif linejoin == 'miter':
            intersection = s1.intersection(s2, force=True)
        elif linejoin == 'round':
            NotImplemented
        return intersection

    def getEdgeProjection(self, i, j, distance, orientation, linecap):
        p1, p2 = self._points[i], self._points[j]
        uv = p1.vector(p2).unit_vector()
        if linecap == 'spike':
            return [p1.displace(uv.rotate(90 * orientation).scale(distance), 'line'),
                    p1.displace(uv.rotate(180).scale(distance), 'line'),
                    p1.displace(uv.rotate(-90 * orientation).scale(distance), 'line')]
        else:
            NotImplemented

class Stroke(DefGlyph):
    def __init__(self, contours, relative=False):
        super().__init__()
        for contour in contours:
            self.appendContour(contour)
        self.relative = relative

    def to_relative(self):
        """ Return a new Stroke object with points in relative position
        """
        if self.relative:
            raise Exception('The stroke is already in relative position')
        new_contours = list()
        for contour in self._contours:
            points = [contour[i-1].relative(contour[i])
                      if i != 0 else contour[i]
                      for i in range(len(contour))]
            new_contour = Contour(points)
            new_contours.append(new_contour)

        return type(self)(new_contours, relative=True)

    # TODO: apply oblique style to points

class Shape(Stroke):
    def __init__(self, contours, width, linejoin='round', linecap='spike', angle=None):
        distance = width / 20
        contours = self.vectorize(contours, distance, linejoin, linecap)
        super().__init__(contours)

    @staticmethod
    def vectorize(contours, distance, linejoin, linecap):
        new_contours = list()
        for points in contours:
            # direction = Segment(points[0], points[1]).isClockwise()
            orientation = 1
            length = len(points)
            outer, inner = list(), list()
            new_layer = list()

            start = 1 if points.open else 0
            end = length - 1 if points.open else length

            if points.open:
                outer += points.getEdgeProjection(0, 1, distance, orientation, linecap)

            for i in range(start, end):
                outer += points.getCornerProjection(i, distance, orientation, linejoin)
                inner += points.getCornerProjection(i, distance, -orientation, linejoin)

            inner.reverse()

            if points.open:
                outer += points.getEdgeProjection(length - 1,length - 2, distance, orientation, linecap)
                if len(inner) > 0:
                    outer.extend(inner)
                new_contours.append(Contour(outer))

            else:
                new_contours += [Contour(outer), Contour(inner)]

        return new_contours
