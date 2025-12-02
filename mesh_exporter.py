import json
import numpy as np
import os
import sys

# Mapping des types JSON → NumPy
TYPE_MAP = {
    "float": np.float32,
    "double": np.float64,
    "int16": np.int16,
    "uint8": np.uint8,
    "uint64": np.uint64,
    "int32": np.int32
}

def load_array(attr, base_path):
    """Charge un buffer .raw en numpy array avec le bon dtype"""
    dtype = TYPE_MAP.get(attr["type"]["string"]["value"], np.float32)
    size = int(attr["size"]["sequence"]["0"]["string"]["value"])
    nb_comp = int(attr.get("nb_of_components", {}).get("numeric", {}).get("value", 1))

    buffer_file = attr["buffer"]["blob"]["buffer"]
    raw_path = os.path.join(base_path, os.path.basename(buffer_file))
    arr = np.fromfile(raw_path, dtype=dtype)

    if arr.size != size * nb_comp:
        print(f"⚠️ Taille inattendue pour {raw_path}: {arr.size} vs {size*nb_comp}")
    if nb_comp > 1:
        arr = arr.reshape((-1, nb_comp))
    return arr

def export_obj(mesh, organ_name, outdir):
    """Exporte un mesh (points + cells) en .obj"""
    points = mesh["points"]
    normals = mesh.get("normals")
    indices = mesh["cell_data"]
    offsets = mesh["cell_offsets"]
    types = mesh["cell_types"]

    safe_name = organ_name.replace(" ", "_")
    obj_path = os.path.join(outdir, f"{safe_name}.obj")
    with open(obj_path, "w") as f:
        f.write(f"# Export OBJ for {safe_name}\n")
        f.write(f"mtllib {safe_name}.mtl\n")
        f.write(f"usemtl {safe_name}_mat\n")

        # Sommets
        for p in points:
            f.write(f"v {p[0]} {p[1]} {p[2]}\n")

        # Normales
        if normals is not None:
            for n in normals:
                f.write(f"vn {n[0]} {n[1]} {n[2]}\n")

        # Faces ou lignes
        for i in range(len(types)):
            start = offsets[i]
            end = offsets[i+1] if i+1 < len(offsets) else len(indices)
            verts = indices[start:end]

            if types[i] == 5 and len(verts) == 3:  # Triangle
                f.write(f"f {verts[0]+1} {verts[1]+1} {verts[2]+1}\n")
            elif types[i] == 9 and len(verts) == 4:  # Quad
                f.write(f"f {verts[0]+1} {verts[1]+1} {verts[2]+1} {verts[3]+1}\n")
            elif types[i] == 3 and len(verts) == 3:  # Triangle
                f.write(f"f {verts[0]+1} {verts[1]+1} {verts[2]+1}\n")

    print(f"✅ Exporté : {obj_path}")

def extract_meshes(json_data, base_path, outdir):
    """Parcourt le JSON et exporte tous les meshes"""
    seq = json_data["object"]["attributes"]["values"]["sequence"]
    for k, v in seq.items():
        obj = v["object"]
        if obj["meta_infos"]["item_0"]["value"] == "::fwMedData::ModelSeries":
            recs = obj["attributes"]["reconstruction_db"]["sequence"]
            for rk, rv in recs.items():
                rec = rv["object"]
                organ_name = rec["attributes"]["organ_name"]["string"]["value"]

                mesh_obj = rec["attributes"]["mesh"]["object"]["attributes"]

                points = load_array(mesh_obj["points"]["object"]["attributes"], base_path)
                normals = load_array(mesh_obj["point_normals"]["object"]["attributes"], base_path) \
                          if mesh_obj.get("point_normals") else None
                indices = load_array(mesh_obj["cell_data"]["object"]["attributes"], base_path)
                offsets = load_array(mesh_obj["cell_data_offsets"]["object"]["attributes"], base_path)
                offsets = offsets.astype(int)
                types = load_array(mesh_obj["cell_types"]["object"]["attributes"], base_path)

                mesh = {
                    "points": points,
                    "normals": normals,
                    "cell_data": indices,
                    "cell_offsets": offsets,
                    "cell_types": types
                }

                # --- Récupération couleur diffuse ---
                color = [0.8, 0.8, 0.8]  # fallback gris si pas trouvé
                mat = rec["attributes"].get("material")
                if mat and "object" in mat:
                    mat_attrs = mat["object"]["attributes"]
                    if "diffuse" in mat_attrs:
                        rgba_seq = mat_attrs["diffuse"]["object"]["attributes"]["rgba"]["sequence"]
                        color = [
                            float(rgba_seq["0"]["numeric"]["value"]),
                            float(rgba_seq["1"]["numeric"]["value"]),
                            float(rgba_seq["2"]["numeric"]["value"])
                        ]
                ambient = [0.2, 0.2, 0.2]  # fallback
                if "ambient" in mat_attrs:
                    rgba_seq = mat_attrs["ambient"]["object"]["attributes"]["rgba"]["sequence"]
                    ambient = [
                        float(rgba_seq["0"]["numeric"]["value"]),
                        float(rgba_seq["1"]["numeric"]["value"]),
                        float(rgba_seq["2"]["numeric"]["value"])
                    ]

                export_obj(mesh, organ_name, outdir)
                export_mtl(organ_name, color, ambient, outdir)


def export_mtl(organ_name, diffuse, ambient, outdir):
    safe_name = organ_name.replace(" ", "_")
    mtl_path = os.path.join(outdir, f"{safe_name}.mtl")
    with open(mtl_path, "w") as f:
        f.write(f"newmtl {safe_name}_mat\n")
        f.write(f"Kd {diffuse[0]} {diffuse[1]} {diffuse[2]}\n")  # Diffuse
        #f.write(f"Ka {ambient[0]} {ambient[1]} {ambient[2]}\n")  # Ambient
        f.write(f"Ka 0.1 0.1 0.1\n")  # Ambient
        f.write("Ks 0.0 0.0 0.0\n")  # tu peux aussi aller chercher specular si dispo
        f.write("d 1.0\n")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python mesh_exporter.py root.json root-json/ output_dir/")
        sys.exit(1)

    json_path = sys.argv[1]
    base_path = sys.argv[2]
    outdir = sys.argv[3]
    os.makedirs(outdir, exist_ok=True)

    with open(json_path, "r") as f:
        data = json.load(f)

    extract_meshes(data, base_path, outdir)
