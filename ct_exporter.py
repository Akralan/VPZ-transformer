import json
import numpy as np
import nibabel as nib
import os
import sys

def load_raw_volume(raw_path, shape, dtype, strides=None):
    """Charge un fichier RAW en numpy 3D avec strides."""
    with open(raw_path, "rb") as f:
        data = f.read()
    
    if strides is not None:
        # Utiliser np.ndarray avec strides personnalisés
        vol = np.ndarray(
            shape=shape,
            dtype=dtype,
            buffer=data,
            strides=strides
        )
    else:
        # Fallback : reshape simple
        arr = np.frombuffer(data, dtype=dtype)
        vol = arr.reshape(shape)
    
    return vol.copy()  # Copie pour éviter les problèmes de buffer

def export_nifti(vol, out_path):
    """Sauvegarde en NIfTI compressé avec header complet."""
    # Créer l'image NIfTI avec affine identity
    nifti_img = nib.Nifti1Image(vol, affine=np.eye(4))
    
    # Configurer le header correctement
    hdr = nifti_img.header
    hdr['descrip'] = b'CT scan exported from VPZ'  # Description non vide
    hdr['xyzt_units'] = 2  # 2 = mm (spatial units)
    hdr['qform_code'] = 1  # 1 = scanner anatomical coordinates
    hdr['sform_code'] = 1  # 1 = scanner anatomical coordinates
    
    # Définir pixdim (dimensions des voxels en mm)
    # Par défaut 1mm isotrope, tu peux ajuster si tu as les vraies dimensions
    hdr['pixdim'][1:4] = [1.0, 1.0, 1.0]  # x, y, z en mm
    
    nib.save(nifti_img, out_path)
    print(f"✅ Exported NIfTI: {out_path}")

def extract_images_from_json(json_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    json_dir = os.path.dirname(os.path.abspath(json_path))
    with open(json_path, "r", encoding="utf-8") as f:
        root = json.load(f)

    def explore(data, path=""):
        if isinstance(data, dict):
            # Repère un bloc fwData::Image
            if "meta_infos" in data:
                meta = data["meta_infos"].get("item_0", {}).get("value", "")
                if meta == "::fwData::Image":
                    attrs = data.get("attributes", {})
                    buf_info = attrs.get("array", {}).get("object", {}).get("attributes", {}).get("buffer", {})
                    if not buf_info:
                        buf_info = attrs.get("buffer", {})
                    blob = buf_info.get("blob", {})

                    if blob:
                        buffer_file = blob.get("buffer")
                        dtype = (
                            attrs.get("array", {})
                            .get("object", {})
                            .get("attributes", {})
                            .get("type", {})
                            .get("string", {})
                            .get("value", "uint8")
                        )
                        size_seq = (
                            attrs.get("array", {})
                            .get("object", {})
                            .get("attributes", {})
                            .get("size", {})
                            .get("sequence", {})
                        )
                        dims = [int(size_seq[str(i)]["string"]["value"]) for i in range(len(size_seq))]
                        
                        # Récupérer les strides
                        strides_seq = (
                            attrs.get("array", {})
                            .get("object", {})
                            .get("attributes", {})
                            .get("strides", {})
                            .get("sequence", {})
                        )
                        strides = None
                        if strides_seq:
                            strides = tuple(int(strides_seq[str(i)]["string"]["value"]) for i in range(len(strides_seq)))
                        
                        print(f"\n🩻 Found {buffer_file} ({dtype}, {dims}, strides={strides})")

                        # Utiliser le chemin relatif du JSON (ex: "root-json/xxx.raw")
                        # Convertir les slashes du JSON en slashes système
                        buffer_file_normalized = buffer_file.replace("\/", os.sep).replace("/", os.sep)
                        abs_path = os.path.join(json_dir, buffer_file_normalized)
                        
                        if not os.path.exists(abs_path):
                            print(f"⚠️ Missing RAW file: {abs_path}")
                            return
                        out_name = os.path.splitext(os.path.basename(buffer_file))[0] + ".nii.gz"
                        vol = load_raw_volume(abs_path, dims, np.dtype(dtype), strides)
                        export_nifti(vol, os.path.join(out_dir, out_name))

            for k, v in data.items():
                explore(v, f"{path}/{k}")

        elif isinstance(data, list):
            for i, item in enumerate(data):
                explore(item, f"{path}[{i}]")

    explore(root)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python ct_exporter.py <root.json> <output_folder>")
        sys.exit(1)

    json_path = sys.argv[1]
    out_dir = sys.argv[2]

    extract_images_from_json(json_path, out_dir)
