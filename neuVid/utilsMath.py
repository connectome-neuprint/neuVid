import math
import unittest

# Supports the needs of the `importNg.py` script by mimicing a few parts of the APIs for Vector and 
# Quaternion from the standard Blender mathutils package.  The importNg.py script then can be run
# with standard Python instead of through Blender (with the `--background --python` options).
# This approach prepares for a future when importNg.py may need Python modules not part of the
# standard Blender distribution, like the package for decompression of Draco encoded meshes
# (https://anaconda.org/conda-forge/draco).

# For simplicity, the unit tests are included in this file.  Run them as:
# $ python utilsMath.py

class Vector:
    def __init__(self, t):
        if len(t) != 3:
            raise TypeError
        self._c = list(t)
        self._len = math.sqrt(self._c[0] * self._c[0] + self._c[1] * self._c[1] + self._c[2] * self._c[2]) 

    @property
    def x(self):
        return self._c[0]

    @property
    def y(self):
        return self._c[1]
 
    @property
    def z(self):
        return self._c[2]

    @property
    def length(self):
        return self._len

    def __repr__(self):
        return "Vector(x={:.2f}, y={:.2f}, z={:.2f})".format(self.x, self.y, self.z)

    def __add__(self, v):
        return Vector((self._c[0] + v._c[0], self._c[1] + v._c[1], self._c[2] + v._c[2]))

    def __sub__(self, v):
        return Vector((self._c[0] - v._c[0], self._c[1] - v._c[1], self._c[2] - v._c[2]))

    def __mul__(self, s):
        return Vector((self._c[0] * s, self._c[1] * s, self._c[2] * s))

    def __truediv__(self, s):
        return Vector((self._c[0] / s, self._c[1] / s, self._c[2] / s))

    def normalized(self):
        if self._len == 0:
            return Vector((0, 0, 0))
        return Vector(tuple(x / self._len for x in self._c))    

    def dot(self, v):
        return self._c[0] * v._c[0] + self._c[1] * v._c[1] + self._c[2] * v._c[2]

    def cross(self, v):
        rx = self.y * v.z - self.z * v.y
        ry = self.z * v.x - self.x * v.z
        rz = self.x * v.y - self.y * v.x
        return Vector((rx, ry, rz))

    def rotate(self, q):
        qv = Vector((q.x, q.y, q.z))
        uv = qv.cross(self)
        uuv = qv.cross(uv)
        uv = uv * 2 * q.w
        uuv = uuv * 2
        self._c[0] += uv._c[0] + uuv._c[0]
        self._c[1] += uv._c[1] + uuv._c[1]
        self._c[2] += uv._c[2] + uuv._c[2]

    def angle(self, v):
        dot_self = self.dot(self)
        dot_other = v.dot(v)
        dot_both = self.dot(v)
        x = dot_both / (math.sqrt(dot_self) * math.sqrt(dot_other))
        if x <= -1.0:
            return math.pi
        elif x >= 1.0:
            return 0.0
        else:
            return math.acos(x)

class Quaternion:
    # Note that the input tuple is `(w, x, y, z)` to match Blender's mathutils.  Some other systems,
    # notably Neuroglancer's view state, use `(x, y, z, w)` as the tuple representation of a Quaternion,
    # so tuples from those systems must be swizzled.
    def __init__(self, t, a=None):
        if a == None:
            if len(t) != 4:
                raise TypeError
            self._c = list(t)
        else:
            if len(t) != 3:
                raise TypeError
            # The following formula assumes the axis is normalized.
            axisV = Vector(t).normalized()
            axis = (axisV.x, axisV.y, axisV.z)
            angle = a
            s = math.sin(angle / 2)
            w = math.cos(angle / 2)
            self._c = (w, axis[0] * s, axis[1] * s, axis[2] * s)

    @property
    def w(self):
        return self._c[0]

    @property
    def x(self):
        return self._c[1]

    @property
    def y(self):
        return self._c[2]
 
    @property
    def z(self):
        return self._c[3]

    @property
    def angle(self):
        return math.acos(self.w) * 2.0

    def __repr__(self):
        return "Quaternion(w={:.3f}, x={:.3f}, y={:.3f}, z={:.3f})".format(self.w, self.x, self.y, self.z)

    def normalized(self):
        len = math.sqrt(self._c[0] * self._c[0] + self._c[1] * self._c[1] + self._c[2] * self._c[2] + self._c[3] * self._c[3])
        return Quaternion(tuple(x / len for x in self._c))    

    def dot(self, q):
        return self._c[0] * q._c[0] + self._c[1] * q._c[1] + self._c[2] * q._c[2] + self._c[3] * q._c[3]

    def rotation_difference_angle(self, q):
        # From:
        # https://github.com/mrdoob/three.js/blob/master/src/math/Quaternion.js
        # Simpler than `rotation_differnce` followed by `angle` from:
        # https://github.com/dfelinto/blender/blob/master/source/blender/blenlib/intern/math_rotation.c
        # But seems to assume the quaternions are normalized.

        qA = self.normalized()
        qB = q.normalized()
        dot_clamped = max(-1.0, min(qA.dot(qB), 1.0))
        return 2 * math.acos(abs(dot_clamped))

#

class TestVector(unittest.TestCase):

    def test_invalid(self):
        with self.assertRaises(TypeError):
            Vector((1))

    def test_coords(self):
        v = Vector((1, -2, 3))
        self.assertEqual(v.x, 1)
        self.assertEqual(v.y, -2)
        self.assertEqual(v.z, 3)

        with self.assertRaises(AttributeError):
            v.x = 10
        self.assertEqual(v.x, 1)
        with self.assertRaises(AttributeError):
            v.y = -20
        self.assertEqual(v.y, -2)
        with self.assertRaises(AttributeError):
            v.z = 30
        self.assertEqual(v.z, 3)

    def test_length(self):
        v = Vector((1.2, -3.4, 5.6))
        self.assertEqual(v.length, math.sqrt(1.2 * 1.2 + -3.4 * -3.4 + 5.6 * 5.6))

    def test_add(self):
        vA = Vector((-1, 2, -3))
        vB = Vector((4, -5, 6))
        vC = vA + vB
        self.assertEqual(vC.x, -1 + 4)
        self.assertEqual(vC.y, 2 + -5)
        self.assertEqual(vC.z, -3 + 6)

    def test_sub(self):
        vA = Vector((-1.2, 3.4, -5.6))
        vB = Vector((7.8, -9.10, 11.12))
        vC = vA - vB
        self.assertEqual(vC.x, -1.2 - 7.8)
        self.assertEqual(vC.y, 3.4 - -9.10)
        self.assertEqual(vC.z, -5.6 - 11.12)

    def test_mul(self):
        vA = Vector((1.2, -3.4, 5.6))
        vB = vA * 7
        self.assertEqual(vB.x, 1.2 * 7)
        self.assertEqual(vB.y, -3.4 * 7)
        self.assertEqual(vB.z, 5.6 * 7)

    def test_div(self):
        vA = Vector((1.2, 3.4, 5.6))
        vB = vA / 7
        self.assertEqual(vB.x, 1.2 / 7)
        self.assertEqual(vB.y, 3.4 / 7)
        self.assertEqual(vB.z, 5.6 / 7)

    def test_normalized(self):
        vA = Vector((1, -2, 3))
        vAn = vA.normalized()
        self.assertAlmostEqual(vAn.length, 1)
    
        vB = Vector((0, 0, 0))
        vBn = vB.normalized()
        self.assertAlmostEqual(vBn.length, 0)

    def test_dot(self):
        vA = Vector((-1.2, 3.4, -5.6))
        vB = Vector((7.8, -9.10, 11.12))
        self.assertEqual(vA.dot(vB), -1.2 * 7.8 + 3.4 * -9.10 + -5.6 * 11.12)

    def test_cross(self):
        z = Vector((1, 0, 0)).cross(Vector((0, 1, 0)))
        self.assertEqual(z.x, 0)
        self.assertEqual(z.y, 0)
        self.assertEqual(z.z, 1)
    
        x = Vector((0, 1, 0)).cross(Vector((0, 0, 1)))
        self.assertEqual(x.x, 1)
        self.assertEqual(x.y, 0)
        self.assertEqual(x.z, 0)

        y = Vector((0, 0, 1)).cross(Vector((1, 0, 0)))
        self.assertEqual(y.x, 0)
        self.assertEqual(y.y, 1)
        self.assertEqual(y.z, 0)

    def test_rotate(self):
        q90aroundX = Quaternion((0.7071068286895752, 0.7071067690849304, 0.0, 0.0))
        v = Vector((0, 1, 0))
        v.rotate(q90aroundX)
        self.assertAlmostEqual(v.x, 0, places=6)
        self.assertAlmostEqual(v.y, 0, places=6)
        self.assertAlmostEqual(v.z, 1, places=6)
    
        q90aroundY = Quaternion((0.7071068286895752, 0.0, 0.7071067690849304, 0.0))
        v = Vector((0, 0, 1))
        v.rotate(q90aroundY)
        self.assertAlmostEqual(v.x, 1, places=6)
        self.assertAlmostEqual(v.y, 0, places=6)
        self.assertAlmostEqual(v.z, 0, places=6)

        qMinus90aroundZ = Quaternion((0.7071067690849304, 0.0, 0.0, -0.7071067690849304))
        v = Vector((1, 0, 0))
        v.rotate(qMinus90aroundZ)
        self.assertAlmostEqual(v.x, 0, places=6)
        self.assertAlmostEqual(v.y, -1, places=6)
        self.assertAlmostEqual(v.z, 0, places=6)

    def test_angle(self):
        vA = Vector((1, 0, 0))
        vB = Vector((0, 1, 0))
        self.assertAlmostEqual(vA.angle(vB), math.radians(90))
    
        vA = Vector((1, 1, 0))
        vB = Vector((0, 0, -1))
        self.assertAlmostEqual(vA.angle(vB), math.radians(90))

        vA = Vector((1, -math.sqrt(2), 1))
        vB = Vector((1, 0, 1))
        self.assertAlmostEqual(vA.angle(vB), math.radians(45))

class TestQuaternion(unittest.TestCase):

    def test_invalid(self):
        with self.assertRaises(TypeError):
            Quaternion((1))

    def test_coords(self):
        w = 1
        x = 2
        y = 3
        z = 4
        q = Quaternion((w, x, y, z))
        self.assertEqual(q.w, w)
        self.assertEqual(q.x, x)
        self.assertEqual(q.y, y)
        self.assertEqual(q.z, z)

        with self.assertRaises(AttributeError):
            q.w = 1
        self.assertEqual(q.w, w)
        with self.assertRaises(AttributeError):
            q.x = 2
        self.assertEqual(q.x, x)
        with self.assertRaises(AttributeError):
            q.y = 3
        self.assertEqual(q.y, y)
        with self.assertRaises(AttributeError):
            q.z = 4
        self.assertEqual(q.z, z)

    def test_from_axis_angle(self):
        axisBV = Vector((1, -1, 1))
        axisB = (axisBV.x, axisBV.y, axisBV.z)
        angleB = math.radians(45)
        q = Quaternion(axisB, angleB)
        self.assertAlmostEqual(q.w, 0.9238795042037964)
        self.assertAlmostEqual(q.x, 0.2209424078464508)
        self.assertAlmostEqual(q.y, -0.2209424078464508)
        self.assertAlmostEqual(q.z, 0.2209424078464508)

    def test_normalized(self):
        qA = Quaternion((1, -2, 3, -4))
        qB = qA.normalized()
        lenB = math.sqrt(qB.w * qB.w + qB.x * qB.x + qB.y * qB.y + qB.z * qB.z)
        self.assertAlmostEqual(lenB, 1)

    def test_dot(self):
        wA = 0
        xA = -1
        yA = 2
        zA = -3
        qA = Quaternion((wA, xA, yA, zA))

        wB = 4
        xB = 5
        yB = -6
        zB = -7
        qB = Quaternion((wB, xB, yB, zB))

        self.assertEqual(qA.dot(qB), wA * wB + xA * xB + yA * yB + zA * zB)

    def test_rotation_difference_angle(self):
        axisV = Vector((1, 2, 3))
        axis = (axisV.x, axisV.y, axisV.z)
        angleA = math.radians(30)
        angleB = math.radians(60)
        qA = Quaternion(axis, angleA)
        qB = Quaternion(axis, angleB)
        self.assertAlmostEqual(qA.rotation_difference_angle(qB), angleB - angleA)

if __name__ == '__main__':
    unittest.main()
