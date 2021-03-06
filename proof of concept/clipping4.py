"""
Copyright 2017 Sigvald Marholm <marholm@marebakken.com>

This file is part of FEdensity.

FEdensity is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

FEdensity is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License along with
FEdensity. If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import print_function
import numpy as np
import matplotlib.pyplot as plt
import mpl_toolkits.mplot3d as a3
from scipy.spatial import ConvexHull
from itertools import combinations, count
import timeit
import copy
import time

epsilon = 1e-10

def update_edge(edge, p, n):
    v1 = edge[0]
    v2 = edge[1]

    # Normal component wrt plane
    v1_normal = np.dot(v1-p,n)
    v2_normal = np.dot(v2-p,n)

    if v1_normal > -epsilon and v2_normal > -epsilon:
        return None, None

    if v1_normal <= -epsilon and v2_normal <= -epsilon:
        return edge, None

    if v1_normal > -epsilon and v1_normal <= epsilon: # in plane
        return edge, v1

    if v2_normal > -epsilon and v2_normal <= epsilon: # in plane
        return edge, v2

    edge_normal = np.dot(v2-v1,n)
    alpha = -v1_normal / edge_normal
    v_new = v1 + alpha*(v2-v1)

    if v1_normal > epsilon:
        edge[0] = v_new
    else:
        edge[1] = v_new

    assert edge_length(edge)>epsilon

    return edge, v_new

def is_behind_plane(point, p, n):
    normal_component = np.dot(point-p,n)
    return normal_component < 0


# Vertex = [x,y]
# Edge = [Vertex,Vertex] = [[x,y],[x,y]]
# Face = [Edge,Edge,Edge,Edge] = [[[x,y],[x,y]],...]

# No ID's, just storing vertices and edges directly nested.
# Disadvantage: No re-using of already cut edges
# Advantages: Does not need to keep track of edges.
# It's likely cheaper to cut some edges twice than to book-keep

def vertices_equal(a, b, tol=epsilon):
    # just comparing a==b should be allright in this case since it's only
    # copied values, however, it's better to produce safe code in case it's
    # sometimes used differently.
    return np.linalg.norm(a-b)<epsilon

def vertex_in_list(vertex, edge, tol=epsilon):
    return np.any([vertices_equal(a,vertex) for a in edge])

def find_other_edge(face, edge, vertex):
    """
    Returns the other edge in face which shares this vertex.
    """
    for other_edge in face:
        if other_edge is not edge:
            if vertex_in_list(vertex, other_edge):
                return other_edge

def find_other_vertex(edge, vertex):
    """
    Returns the other vertex of this edge.
    """
    if np.all(edge[0]==vertex):
        return edge[1]
    else:
        return edge[0]

def extract_face_vertices(face):
    face_vertices = []
    edge = face[0]
    vertex = edge[0]
    first_vertex = vertex
    while True:
        face_vertices.append(vertex)
        edge = find_other_edge(face, edge, vertex)
        vertex = find_other_vertex(edge, vertex)
        if vertex is first_vertex:
            return face_vertices

def flatten(inp):
    output = []
    for x in inp:
        for y in x:
            output.append(y)
    return output

def edge_length(edge):
    return np.linalg.norm(edge[0]-edge[1])

class Polyhedron(object):
    def __init__(self, *vertices):

        assert len(vertices)==4

        vertices = [np.array(b,float) for b in vertices]

        edges = list(combinations(vertices,2))
        edges = [list(a) for a in edges]

        # print(np.array(edges))

        self.faces = []
        self.faces.append([3,4,5])
        self.faces.append([1,2,5])
        self.faces.append([0,2,4])
        self.faces.append([0,1,3])

        for i,face in enumerate(self.faces):
            for j,edge_id in enumerate(face):
                self.faces[i][j] = copy.deepcopy(edges[edge_id])

    def __repr__(self):
        s = "Polyhedron\n\n"
        for i,f in enumerate(self.faces):
            s += "face %d:\n"%i
            for j,e in enumerate(f):
                s += "  edge " + str(j) + ": "
                for v in e:
                    s += str(v) + " "
                s += "\n"
            s += "\n"
        return s

    def vertices_are_unique(self):
        vertices = flatten(flatten(self.faces))
        vertice_id = [id(v) for v in vertices]
        n_total = len(vertice_id)
        n_unique = len(set(vertice_id))
        return n_total==n_unique

    def vertex_coordinates_are_unique(self):
        coords = flatten(flatten(flatten(self.faces)))
        coord_id = [id(c) for c in coords]
        n_total = len(coord_id)
        n_unique = len(set(coord_id))
        return n_total==n_unique

    def extract_face_vertices(self):
        faces = []
        for face in self.faces:
            faces.append(extract_face_vertices(face))
        return faces

    def plot(self):
        faces = self.extract_face_vertices()
        ax = a3.Axes3D(plt.figure())
        tri = a3.art3d.Poly3DCollection(faces)
        tri.set_alpha(0.3)
        ax.add_collection3d(tri)
        plt.show()

    def clip(self, p, n):

        new_face = []
        for face_id,face in reversed(zip(count(),self.faces)):

            new_edge = []
            for edge_id,edge in reversed(zip(count(),face)):

                edge, new_vertex = update_edge(edge, p, n)

                if edge is None:
                    face.pop(edge_id)

                if new_vertex is not None:
                    new_edge.append(copy.deepcopy(new_vertex))

            assert len(new_edge)==0 or len(new_edge)==2
            if len(new_edge)==2 and edge_length(new_edge)>epsilon:
                face.append(new_edge)
                new_face.append(copy.deepcopy(new_edge))

            if face == []:
                self.faces.pop(face_id)

        if len(new_face)>2:
            self.faces.append(new_face)

        assert self.vertices_are_unique()

    def volume(self):
        if len(self.faces)==0: return 0.0

        volume = 0.0
        a = self.faces[0][0][0]
        for face in self.faces:
            face_vertices = extract_face_vertices(face)
            if not vertex_in_list(a,face_vertices):
                b = face_vertices[0]
                for i in range(1,len(face_vertices)-1):
                    c = face_vertices[i]
                    d = face_vertices[i+1]
                    cross = np.cross(b-d,c-d)
                    dot = np.dot(a-d,cross)
                    volume += abs(dot)
        volume *= (1.0/6)
        return volume

def method3():

    vertices = [np.array([0,0,0]),
                np.array([1,0,0]),
                np.array([0,1,0]),
                np.array([0,0,1])]

    p = Polyhedron(*vertices)

    p.clip([0.5,0,0],[1,0,0])
    p.clip([0,0.5,0],[0,1,0])
    p.clip([0,0,0.5],[0,0,1])

    return p.volume()

if __name__ == '__main__':



    # vertices = [np.array([0,0,0]),
    #             np.array([1,0,0]),
    #             np.array([0,1,0]),
    #             np.array([0,0,1])]
    #
    # p2 = Polyhedron(*vertices)
    # p.clip([0.5,0,0],[1,0,0])
    # # p.clip([0.3,0,0],[1,0,0])
    # # p.clip([0.1,0,0],[1,0,0])
    # # p.clip([0,0.3,0],[0,1,0])
    # p.clip([0,0.5,0],[0,1,0])
    # p.clip([0,0,0.5],[0,0,1])
    # # p.clip([0,0.4,0.4],[0,1,1])
    # print(p.volume())
    # p.plot()

    # vertices = [np.array([-2,-2,-2]),
    #             np.array([8,-2,-2]),
    #             np.array([-2,8,-2]),
    #             np.array([-2,-2,8])]
    #
    # p = Polyhedron(*vertices)
    # p.clip([1,0,0],[1,0,0])
    # p.clip([0,1,0],[0,1,0])
    # p.clip([0,0,1],[0,0,1])
    #
    # for theta in range(0,360,1):
    #     theta_rad = float(theta) * np.pi / 180
    #     x = np.cos(theta_rad)
    #     y = np.sin(theta_rad)
    #     p.clip([x,y,0],[x,y,-0.5])
    #     p.clip([x,y,0],[x,y,1])
    # p.clip([0,0,0.3],[0,0,1])
    # print(p.volume())
    # p.plot()


    vertices = [np.array([-1,-1,-1]),
                np.array([8,-1,-1]),
                np.array([-1,8,-1]),
                np.array([-1,-1,8])]

    p = Polyhedron(*vertices)
    p.clip([1,0,0],[1,0,0])
    p.clip([0,1,0],[0,1,0])
    p.clip([0,0,1],[0,0,1])

    t0 = time.time()
    for theta in range(0,360):
        theta_rad = float(theta) * np.pi / 180
        x = np.cos(theta_rad)
        y = np.sin(theta_rad)
        p.clip([x,y,0],[x,y,0])
    # p.clip([0,0,0.3],[0,0,1])
    t1 = time.time()
    print("Cutting:",t1-t0)
    t0 = time.time()
    volume = p.volume()
    t1 = time.time()
    print("Volume:",t1-t0)
    print(volume)
    # p.plot()
