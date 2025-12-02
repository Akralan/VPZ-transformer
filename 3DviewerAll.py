import pyvista as pv
import sys
import os

def view_all_objs_in_folder(folder_path):
    plotter = pv.Plotter()

    for file in os.listdir(folder_path):
        if file.lower().endswith(".obj"):
            obj_path = os.path.join(folder_path, file)
            mtl_path = None

            # Cherche un .mtl correspondant
            base_name = os.path.splitext(file)[0].lower()
            for candidate in os.listdir(folder_path):
                if candidate.lower().endswith(".mtl") and candidate.lower().startswith(base_name):
                    mtl_path = os.path.join(folder_path, candidate)
                    break

            if mtl_path:
                print(f"[INFO] Import OBJ avec MTL : {obj_path} + {mtl_path}")
                plotter.import_obj(obj_path, filename_mtl=mtl_path)
            else:
                print(f"[WARN] Pas de .mtl trouvé, import simple : {obj_path}")
                plotter.import_obj(obj_path)

    plotter.show()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python 3Dviewer.py <dossier>")
        sys.exit(1)

    folder = sys.argv[1]
    if not os.path.isdir(folder):
        print(f"Dossier introuvable : {folder}")
        sys.exit(1)

    view_all_objs_in_folder(folder)
