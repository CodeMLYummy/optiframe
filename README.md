# OptiFrame YCrunch

Du verre de lunettes recyclé à la monture imprimée en 3D. Défi CodeML 2026, Santé Numérique Sans Frontières.

- **Application :** https://optiframe.app
- **Précision visée :** 0,5 mm sur A, B et le pont, selon la norme ISO 12870 (le jury accorde le maximum à 1 mm). Voir [Validation](docs/validation.md).

```mermaid
flowchart LR
    A[/"Photo d'un verre<br/>sur la feuille"/] --> B["Mesures en mm<br/>A, B, périmètre"]
    B --> C(["Contour SVG 1:1<br/>pour vérifier sur papier"])
    B --> D["Monture 3D<br/>pour deux verres"]
    D --> E(["monture.stl<br/>prête à imprimer"])

    classDef result fill:#dcfce7,stroke:#15803d,color:#0b3d1c
    class C,E result
```

### Architecture

Trois parties : l'**application** sur le téléphone, le **serveur** qui mesure, et l'**entraînement** du modèle d'IA, fait une seule fois à l'avance.

```mermaid
flowchart TB
    subgraph PHONE["Téléphone : application web (Angular)"]
        CAM[/"Caméra ou import de photo"/]
        CARDS["Fiche par verre<br/>mesures + image de contrôle"]
        GEN["Générateur de monture<br/>(manifold-3d)"]
        VIEW["Aperçu 3D<br/>(three.js)"]
        EXP(["Téléchargements<br/>monture.stl, contour.svg"])
    end

    subgraph SERVER["Serveur : API (Spring Boot)"]
        RECT["Redressement<br/>marqueurs ArUco (OpenCV)"]
        SEG["Détection du verre<br/>modèle IA ou méthode classique"]
        MEAS["Mesure<br/>contour en mm, A, B, périmètre"]
    end

    subgraph TRAIN["Entraînement (Python, Colab)"]
        DATA[("Jeu de données<br/>photos + masques")]
        MODEL[("Modèle U-Net<br/>exporté en ONNX")]
    end

    SHEET[("Feuille de référence<br/>sheet-layout.json")]

    CAM -- "photo" --> RECT
    RECT --> SEG --> MEAS
    MEAS -- "contour en mm" --> CARDS
    CARDS -- "verre droit + verre gauche" --> GEN
    GEN --> VIEW
    GEN --> EXP
    MEAS -. "photos auto-étiquetées" .-> DATA
    DATA --> MODEL
    MODEL -. "lens-seg.onnx" .-> SEG
    SHEET -. "position des marqueurs" .-> RECT

    classDef phone fill:#dbeafe,stroke:#1d4ed8,color:#0b1f4d
    classDef server fill:#dcfce7,stroke:#15803d,color:#0b3d1c
    classDef train fill:#ffedd5,stroke:#c2410c,color:#431407
    class CAM,CARDS,GEN,VIEW,EXP phone
    class RECT,SEG,MEAS server
    class DATA,MODEL train
```

Bleu : sur le téléphone. Vert : sur le serveur. Orange : préparé à l'avance. Les cylindres sont des fichiers ou des données.

| Dossier | Contenu |
|---|---|
| `frontend/` | Application Angular 22 (PWA) |
| `backend/` | API Spring Boot 4, `POST /api/measure` |
| `training/` | Feuille de référence, jeu de données, entraînement, export ONNX |

### Documentation

| Page | Contenu |
|---|---|
| [Fonctionnement](docs/fonctionnement.md) | Parcours de l'utilisateur, contrôles de la photo, images de contrôle |
| [Monture](docs/monture.md) | Génération de la monture, tenue du verre dans le cercle, conventions |
| [Capture](docs/capture.md) | Feuille de référence, éclairage, prise de vue |
| [Données et IA](docs/donnees-ia.md) | Collecte auto-étiquetée, entraînement, outils et licences |
| [Validation](docs/validation.md) | Écarts mesurés, limites connues et parades |
| [Déploiement](docs/deploiement.md) | Cloud Run, Cloud Build, variables d'environnement |

### Lancer en local

```bash
# API (Java 25+)
cd backend && ./mvnw spring-boot:run          # http://localhost:8080

# App (Node 22.22+, 24.15+ ou 26+)
cd frontend && npm install && npm start       # http://localhost:4200

# Feuille de référence
cd training && pip install -r requirements.txt && python make_sheet.py

# Tester sur un téléphone (la caméra exige HTTPS)
cloudflared tunnel --url http://localhost:4200
```

Tests : `cd backend && ./mvnw test` (mesure de bout en bout sur une photo synthétique inclinée) et `cd frontend && npm test`.
