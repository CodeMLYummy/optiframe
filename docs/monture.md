# La monture

## Comment la monture est fabriquée

```mermaid
flowchart TD
    IN["Contour du verre droit<br/>+ contour du verre gauche<br/>+ PD du patient"] --> POS["Place le centre de chaque verre<br/>à son demi-PD du centre du nez<br/>(sans PD : pont standard de 18 mm)"]
    POS --> RIM["Cercle : contour agrandi de 4,2 mm,<br/>épaisseur 5 mm"]
    POS --> GROOVE["Rainure en V à 45° :<br/>0,2 mm de jeu + 1 mm de profondeur"]
    RIM --> JOIN["Assemble cercles + pont + tenons"]
    GROOVE --> CUT["Creuse les ouvertures<br/>et les trous des charnières"]
    JOIN --> CUT
    CUT --> CHECK{"Une seule pièce<br/>fermée ?"}
    CHECK -- oui --> OUT(["Résultat : aperçu 3D + monture.stl<br/>face avant à plat sur le plateau"])
    CHECK -- non --> ERR["Erreur : « Reprenez les photos »"]

    classDef err fill:#fde2e1,stroke:#b42318,color:#5c0f0a
    classDef ok fill:#dcfce7,stroke:#15803d,color:#0b3d1c
    class ERR err
    class OUT ok
```

Comment le verre tient dans le cercle (coupe du cercle, face avant en bas) :

```mermaid
flowchart TB
    BACK["Face arrière : petite lèvre de 0,4 mm<br/>le verre passe en forçant légèrement (clic)"]
    MID["Rainure en V : le biseau du verre s'y loge"]
    FRONT["Face avant : lèvre de 1 mm<br/>le verre ne peut pas tomber vers l'avant"]
    BACK --- MID --- FRONT
```

## Placement des verres : le PD du patient

Les verres recyclés vont à un nouveau patient : l'écart de l'ancienne monture ne compte pas. Le centre optique de chaque verre doit tomber devant la pupille, donc on place les verres à partir du PD (écart pupillaire) du patient, et le pont en découle.

```mermaid
flowchart LR
    PD[/"PD du patient<br/>(ou PD par œil)"/] --> C["Centre de chaque verre<br/>à son demi-PD du nez"]
    A[/"Largeurs A<br/>des deux verres"/] --> B
    C --> B{"Pont = PD - (A droit + A gauche) / 2"}
    B -- "moins de 10 mm" --> E["Erreur : les cercles se touchent"]
    B -- "hors 14 à 24 mm" --> W["Avertissement : vérifier le PD"]
    B -- "14 à 24 mm" --> OK(["Monture générée"])

    classDef err fill:#fde2e1,stroke:#b42318,color:#5c0f0a
    classDef warn fill:#fef3c7,stroke:#b45309,color:#451a03
    classDef ok fill:#dcfce7,stroke:#15803d,color:#0b3d1c
    class E err
    class W warn
    class OK ok
```

Sans PD saisi, l'app utilise un pont standard de 18 mm. Le centre optique est supposé au centre du rectangle boxing ; un verre décentré déplace l'effet prismatique (règle de Prentice : prisme = décentrement en cm × puissance).

**Convention :** les contours sont vus de face, face bombée vers le haut. Le verre droit (OD) est à gauche quand on regarde la monture de face, le côté nasal vers le centre. Le contrat partagé est `LensContour` (`frontend/src/app/core/lens.ts`, `backend/.../api/dto/LensContour.java`).

[← Retour au README](../README.md)
