# -*- coding: utf-8 -*-
"""Face swap local (InsightFace inswapper_128) : remplace le visage de la source
par un visage de RÉFÉRENCE (une vraie photo d'une autre personne).

NOTE : pour générer un visage à partir d'une DESCRIPTION texte, il faut un modèle
de diffusion (SD/FLUX + IP-Adapter) — InsightFace seul ne fait que SWAPPER.
"""
import argparse
import os


def replace_face(source_image, reference_image, output_path=None):
    """Swap le visage de source_image avec celui de reference_image."""
    import cv2
    import insightface
    from insightface.app import FaceAnalysis

    app = FaceAnalysis(name="buffalo_l",
                       providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))

    swapper_path = os.path.join(os.path.dirname(__file__), "inswapper_128.onnx")
    if not os.path.exists(swapper_path):
        raise FileNotFoundError(
            "inswapper_128.onnx introuvable. Télécharge-le depuis un miroir HuggingFace "
            "et place-le dans le dossier du script."
        )
    swapper = insightface.model_zoo.get_model(swapper_path, download=False, download_zip=False)

    src = cv2.imread(source_image)
    ref = cv2.imread(reference_image)
    if src is None or ref is None:
        raise ValueError("Impossible de lire les images source/référence.")

    src_faces = app.get(src)
    ref_faces = app.get(ref)
    if not src_faces:
        raise ValueError("Aucun visage détecté dans la source.")
    if not ref_faces:
        raise ValueError("Aucun visage détecté dans la référence.")

    result = swapper.get(src, src_faces[0], ref_faces[0], paste_back=True)
    if output_path is None:
        base, ext = os.path.splitext(source_image)
        output_path = f"{base}_swapped{ext}"
    cv2.imwrite(output_path, result)
    return output_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--reference", required=True)
    ap.add_argument("--output", default=None)
    args = ap.parse_args()
    out = replace_face(args.source, args.reference, args.output)
    print(f"Face swap OK -> {out}")
