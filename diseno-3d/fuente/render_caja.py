"""
render_caja.py — Renders de la caja de control (VTK, fondo transparente para las diapositivas).

Genera en ../renders/:
  caja_exterior.png       caja cerrada, vista isométrica
  caja_interior.png       sin tapa: distribución de los componentes
  caja_explosionada.png   tapa levantada, placas fuera de sus pilares y módulos fuera de sus rieles
Uso:  pip install cadquery vtk     y luego     python render_caja.py
"""
import os
import tempfile

import cadquery as cq
import vtk

import caja_control as C

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "renders")
TMP = tempfile.mkdtemp()


def actor_de(shape, rgb, opacidad=1.0, bordes=True):
    ruta = os.path.join(TMP, f"p{id(shape)}.stl")
    cq.exporters.export(shape, ruta, tolerance=0.08, angularTolerance=0.25)
    lector = vtk.vtkSTLReader(); lector.SetFileName(ruta); lector.Update()
    normales = vtk.vtkPolyDataNormals(); normales.SetInputConnection(lector.GetOutputPort())
    normales.SetFeatureAngle(35); normales.SplittingOn()
    m = vtk.vtkPolyDataMapper(); m.SetInputConnection(normales.GetOutputPort())
    a = vtk.vtkActor(); a.SetMapper(m)
    p = a.GetProperty(); p.SetColor(*rgb); p.SetOpacity(opacidad)
    p.SetAmbient(0.25); p.SetDiffuse(0.75); p.SetSpecular(0.15); p.SetSpecularPower(20)
    actores = [a]
    if bordes:
        fe = vtk.vtkFeatureEdges(); fe.SetInputConnection(lector.GetOutputPort())
        fe.BoundaryEdgesOn(); fe.FeatureEdgesOn(); fe.SetFeatureAngle(35)
        fe.ManifoldEdgesOff(); fe.NonManifoldEdgesOff(); fe.ColoringOff()
        me = vtk.vtkPolyDataMapper(); me.SetInputConnection(fe.GetOutputPort())
        ae = vtk.vtkActor(); ae.SetMapper(me)
        ae.GetProperty().SetColor(0.15, 0.15, 0.15); ae.GetProperty().SetLineWidth(1.2)
        ae.GetProperty().SetOpacity(min(1.0, opacidad + 0.2))
        actores.append(ae)
    return actores


def unir(solidos):
    u = solidos[0]
    for s in solidos[1:]:
        u = u.union(s)
    return u


def render(piezas, archivo, azimut=-35, elevacion=28, zoom=1.15, tam=(1800, 1200)):
    rw = vtk.vtkRenderWindow(); rw.SetOffScreenRendering(1); rw.SetSize(*tam); rw.SetAlphaBitPlanes(1)
    rw.SetMultiSamples(8)
    r = vtk.vtkRenderer(); r.SetBackground(1, 1, 1); r.SetBackgroundAlpha(0.0); rw.AddRenderer(r)
    r.SetUseDepthPeeling(1); r.SetMaximumNumberOfPeels(8)
    for shape, rgb, op in piezas:
        for a in actor_de(shape, rgb, op):
            r.AddActor(a)
    luces = vtk.vtkLightKit(); luces.SetKeyLightIntensity(0.85); luces.AddLightsToRenderer(r)
    cam = r.GetActiveCamera()
    cam.SetFocalPoint(C.L_INT / 2, C.W_INT / 2, C.H_INT / 2)
    cam.SetPosition(C.L_INT / 2, C.W_INT / 2 - 400, C.H_INT / 2)
    cam.SetViewUp(0, 0, 1)
    cam.Azimuth(azimut); cam.Elevation(elevacion); cam.OrthogonalizeViewUp()
    r.ResetCamera(); cam.Zoom(zoom)
    rw.Render()
    w = vtk.vtkWindowToImageFilter(); w.SetInput(rw); w.SetInputBufferTypeToRGBA(); w.ReadFrontBufferOff(); w.Update()
    png = vtk.vtkPNGWriter(); png.SetFileName(os.path.join(SALIDA, archivo)); png.SetInputConnection(w.GetOutputPort())
    png.Write()
    print("render:", archivo)


if __name__ == "__main__":
    os.makedirs(SALIDA, exist_ok=True)
    base, tapa = C.base(), C.tapa()
    comps = {n: (unir(s), rgb) for n, (s, rgb) in C.componentes().items()}
    GRIS, AMARILLO = (0.87, 0.87, 0.85), (0.96, 0.74, 0.12)

    internos = [(s, rgb, 1.0) for s, rgb in comps.values()]
    render([(base, GRIS, 1.0), (tapa, AMARILLO, 1.0)] + internos, "caja_exterior.png")
    render([(base, GRIS, 1.0)] + internos, "caja_interior.png", azimut=-20, elevacion=55, zoom=1.2)

    # Explosionada: así se desarma para reparar
    # (los módulos salen de sus rieles hacia la zona libre; se levantan para que no se tapen)
    desplaz = {"Arduino UNO R3": (0, 0, 60), "Placa perforada + borneras": (0, 0, 60),
               "HX711": (22, 0, 32), "MT3608": (-22, 0, 32)}
    exp = [(base, GRIS, 1.0), (tapa.translate((0, -45, 135)), AMARILLO, 1.0)]
    for n, (s, rgb) in comps.items():
        exp.append((s.translate(desplaz[n]), rgb, 1.0))
    render(exp, "caja_explosionada.png", azimut=150, elevacion=50, zoom=1.0, tam=(1800, 1500))
