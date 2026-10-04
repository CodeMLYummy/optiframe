# Données et IA

Le rétroéclairage rend le verre facile à détourer. On s'en sert pour **fabriquer automatiquement les réponses** qui entraînent le modèle à se débrouiller sans rétroéclairage.

```mermaid
flowchart LR
    subgraph COLLECT["1. Collecte"]
        G1["Verre sur la feuille,<br/>rétroéclairé"] --> MASK["Masque propre<br/>(méthode classique)"]
        G2["Même verre, même position,<br/>sans rétroéclairage,<br/>reflets, ombres"]
    end
    subgraph LABEL["2. Étiquetage automatique"]
        PAIR["La feuille donne la même géométrie :<br/>le masque propre s'applique<br/>à la photo difficile"]
    end
    subgraph TRAINING["3. Entraînement (Colab)"]
        AUG["Augmentation :<br/>reflets, ombres, flou, compression"]
        UNET["U-Net + MobileNetV3"]
        METRIC["Score : IoU + erreur en mm<br/>sur nos verres au pied à coulisse"]
    end
    MASK --> PAIR
    G2 --> PAIR
    PAIR --> AUG --> UNET --> METRIC
    UNET --> ONNX["lens-seg.onnx<br/>→ backend/models/"]
```

> À compléter pendant le défi : nombre d'images, verres utilisés, IoU, erreur en mm.

- Collecte : lancer l'API avec `OPTIFRAME_DATASET_DIR=<dossier>`. Chaque mesure réussie y enregistre le cadre redressé et son masque.
- Entraînement : `training/train.py`. Le prétraitement (512 × 512, normalisation ImageNet) est identique dans `training/dataset.py` et `OnnxSegmenter.java`.
- Aucune donnée personnelle : seulement des verres sur une feuille, pas de visages ni d'ordonnances.

## Outils et licences

```mermaid
mindmap
  root((OptiFrame))
    Vision
      OpenCV 4.9<br/>Apache 2.0
      ONNX Runtime<br/>MIT
      MediaPipe Face Landmarker<br/>Apache 2.0, aperçu sur le visage
    IA
      segmentation_models_pytorch<br/>MIT
      timm MobileNetV3<br/>Apache 2.0
      albumentations<br/>MIT
    3D
      manifold-3d<br/>Apache 2.0
      three.js<br/>MIT
    Application
      Angular<br/>MIT
      Spring Boot<br/>Apache 2.0
    Code
      Claude Code<br/>assistant de programmation
```

[← Retour au README](../README.md)
