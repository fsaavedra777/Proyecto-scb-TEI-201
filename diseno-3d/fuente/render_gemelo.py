"""
render_gemelo.py — Renders del gemelo 3D completo (VTK, fondo transparente para las diapositivas).

Genera en ../renders/:
  gemelo_completo.png              vista isométrica desde el frente, con la caja cerrada
  gemelo_completo_caja_abierta.png caja de control con la tapa levantada (explosionada)
  gemelo_completo_atras.png        vista desde atrás: estación de sensado y pinza
Cada pieza usa el color que trae el STEP.

Uso:  pip install cadquery vtk pillow     y luego     python render_gemelo.py
      (antes corran gemelo_completo.py para tener ../SCB_gemelo_completo.step)
"""
import os
import tempfile

import cadquery as cq
import vtk
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
STEP = os.path.join(AQUI, "..", "SCB_gemelo_completo.step")
SALIDA = os.path.join(AQUI, "..", "renders")
TMP = tempfile.mkdtemp()
_cache = {}


def cargar():
    partes = []
    for shape, nombre, loc, color in cq.Assembly.importStep(STEP):
        if shape is None:
            continue
        rgb = color.toTuple()[:3] if color else (0.75, 0.75, 0.75)
        partes.append((nombre, shape.moved(loc), rgb))
    return partes


def malla(nombre, shape):
    if nombre not in _cache:
        ruta = os.path.join(TMP, f"{len(_cache)}.stl")
        cq.exporters.export(shape, ruta, tolerance=0.12, angularTolerance=0.3)
        lector = vtk.vtkSTLReader(); lector.SetFileName(ruta); lector.Update()
        _cache[nombre] = lector.GetOutput()
    return _cache[nombre]


def actores(pd, rgb, opacidad=1.0, desplazar=(0, 0, 0)):
    normales = vtk.vtkPolyDataNormals(); normales.SetInputData(pd)
    normales.SetFeatureAngle(35); normales.SplittingOn()
    m = vtk.vtkPolyDataMapper(); m.SetInputConnection(normales.GetOutputPort())
    a = vtk.vtkActor(); a.SetMapper(m); a.SetPosition(*desplazar)
    p = a.GetProperty(); p.SetColor(*rgb); p.SetOpacity(opacidad)
    p.SetAmbient(0.22); p.SetDiffuse(0.78); p.SetSpecular(0.18); p.SetSpecularPower(25)
    bordes = vtk.vtkFeatureEdges(); bordes.SetInputData(pd)
    bordes.BoundaryEdgesOn(); bordes.FeatureEdgesOn(); bordes.SetFeatureAngle(40)
    bordes.ManifoldEdgesOff(); bordes.NonManifoldEdgesOff(); bordes.ColoringOff()
    mb = vtk.vtkPolyDataMapper(); mb.SetInputConnection(bordes.GetOutputPort())
    ab = vtk.vtkActor(); ab.SetMapper(mb); ab.SetPosition(*desplazar)
    ab.GetProperty().SetColor(0.12, 0.12, 0.12); ab.GetProperty().SetLineWidth(1.0)
    ab.GetProperty().SetOpacity(min(1.0, opacidad + 0.15))
    return [a, ab]


def render(partes, archivo, foco, direccion, distancia, tapa_levantada=False, tam=(2400, 1600)):
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.SetSize(*tam); rw.SetAlphaBitPlanes(1); rw.SetMultiSamples(0)
    r = vtk.vtkRenderer(); r.SetBackground(1, 1, 1); r.SetBackgroundAlpha(0.0)
    r.SetUseDepthPeeling(1); r.SetMaximumNumberOfPeels(10); r.SetUseFXAA(True); rw.AddRenderer(r)
    for nombre, shape, rgb in partes:
        if tapa_levantada and nombre.endswith("Tapa"):
            lista = actores(malla(nombre, shape), rgb, 0.55, (0, 0, 85))
        else:
            lista = actores(malla(nombre, shape), rgb)
        for a in lista:
            r.AddActor(a)
    luces = vtk.vtkLightKit(); luces.SetKeyLightIntensity(0.9); luces.AddLightsToRenderer(r)
    cam = r.GetActiveCamera()
    n = sum(d * d for d in direccion) ** 0.5
    cam.SetFocalPoint(*foco)
    cam.SetPosition(*[f + distancia * d / n for f, d in zip(foco, direccion)])
    cam.SetViewUp(0, 0, 1); cam.SetViewAngle(28); r.ResetCameraClippingRange()
    rw.Render()
    w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.SetInputBufferTypeToRGBA()
    w2i.ReadFrontBufferOff(); w2i.Update()
    ruta = os.path.join(SALIDA, archivo)
    wr = vtk.vtkPNGWriter(); wr.SetFileName(ruta); wr.SetInputConnection(w2i.GetOutputPort()); wr.Write()
    # recortar el fondo transparente sobrante, dejando un margen del 3 %
    im = Image.open(ruta)
    bb = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    m = int(0.03 * max(im.size))
    im.crop((max(0, bb[0] - m), max(0, bb[1] - m), min(im.width, bb[2] + m), min(im.height, bb[3] + m))).save(ruta, optimize=True)
    print("render:", archivo)


def main():
    os.makedirs(SALIDA, exist_ok=True)
    partes = cargar()
    render(partes, "gemelo_completo.png", (0, 40, 10), (0.55, -1.0, 0.78), 1150)
    render(partes, "gemelo_completo_caja_abierta.png", (95, -105, 45), (1.0, -0.62, 0.8), 720, tapa_levantada=True)
    render(partes, "gemelo_completo_atras.png", (0, 60, 10), (-0.6, 1.0, 0.7), 1150)


if __name__ == "__main__":
    main()
