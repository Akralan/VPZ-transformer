import pyvista as pv
import sys
import os

def view_obj_with_mtl(obj_path):
    # On suppose que le .mtl est dans le même dossier que le .obj
    base_dir = os.path.dirname(obj_path)
    obj_name = os.path.basename(obj_path)
    mtl_path = None

    # Cherche un .mtl correspondant
    for file in os.listdir(base_dir):
        if file.lower().endswith(".mtl") and file.lower().startswith(obj_name.split(".")[0].lower()):
            mtl_path = os.path.join(base_dir, file)
            break

    plotter = pv.Plotter()

    if mtl_path:
        print(f"[INFO] Import OBJ avec MTL : {obj_path} + {mtl_path}")
        plotter.import_obj(obj_path, filename_mtl=mtl_path)
    else:
        print(f"[WARN] Pas de .mtl trouvé, import simple : {obj_path}")
        plotter.import_obj(obj_path)

    plotter.show()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 3Dviewer.py <fichier.obj>")
        sys.exit(1)

    obj_file = sys.argv[1]
    if not os.path.exists(obj_file):
        print(f"Fichier introuvable : {obj_file}")
        sys.exit(1)

    view_obj_with_mtl(obj_file)
