# Fonctionnement

## Parcours de l'utilisateur

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant App as Application (téléphone)
    participant API as Serveur

    U->>App: Ouvre le lien (QR code)
    loop Pour chaque verre (droit, puis gauche)
        U->>App: Prend la photo
        App->>App: Corrige l'orientation, réduit à 4000 px
        App->>API: Envoie la photo
        alt Photo correcte
            API-->>App: Contour + mesures + images de contrôle
            App-->>U: Affiche A, B, périmètre
        else Problème détecté
            API-->>App: Message clair (feuille, flou, verre mal placé)
            App-->>U: "Reprenez la photo : ..."
        end
    end
    U->>App: Saisit le PD du patient (ou PD par œil)
    U->>App: Générer la monture
    App->>App: Calcule la monture en 3D (sur le téléphone)
    App-->>U: Aperçu 3D + bouton monture.stl
```

## Comment une photo devient une mesure

Chaque contrôle peut arrêter le traitement avec un message en français qui dit quoi corriger.

```mermaid
flowchart TD
    P[/"Photo reçue"/] --> M{"Au moins 3 marqueurs<br/>sur 8 trouvés ?"}
    M -- non --> E1["Erreur : « Feuille de référence introuvable.<br/>Cadrez toute la feuille. »"]
    M -- oui --> H["Redressement : vue de dessus<br/>10 pixels = 1 mm"]
    H --> F{"Feuille bien à plat ?<br/>écart < 0,5 mm"}
    F -- non --> E2["Erreur : « La feuille semble pliée. »"]
    F -- oui --> S{"Photo nette ?"}
    S -- non --> E3["Erreur : « Photo floue. »"]
    S -- oui --> C["Découpe du cadre central"]
    C --> AI{"Modèle d'IA<br/>disponible ?"}
    AI -- oui --> SEG1["Segmentation par le modèle"]
    AI -- non --> SEG2["Segmentation classique<br/>bords + anneau sombre"]
    SEG1 --> V{"Verre trouvé<br/>et dans le cadre ?"}
    SEG2 --> V
    V -- non --> E4["Erreur : « Verre introuvable »<br/>ou « dépasse du cadre »"]
    V -- oui --> L["Contour lissé, converti en mm"]
    L --> R(["Résultat : A, B, périmètre<br/>+ 3 images de contrôle"])

    classDef err fill:#fde2e1,stroke:#b42318,color:#5c0f0a
    classDef ok fill:#dcfce7,stroke:#15803d,color:#0b3d1c
    class E1,E2,E3,E4 err
    class R ok
```

Les trois images de contrôle, visibles dans la page **Pas à pas** de l'app :

```mermaid
flowchart LR
    I1["Étape 1<br/>Marqueurs détectés<br/>sur la photo d'origine"] --> I2["Étape 2<br/>Feuille redressée<br/>vue de dessus"] --> I3["Étape 3<br/>Contour du verre<br/>avec A et B"]
```

[← Retour au README](../README.md)
