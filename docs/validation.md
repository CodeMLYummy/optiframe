# Validation et limites

## Objectif de précision

| Seuil | Source | Porte sur |
|---|---|---|
| **0,5 mm** | Norme ISO 12870 (montures de lunettes) | Largeur A, hauteur B et écart entre les verres (pont) |
| 1 mm | Grille du jury (30 points si l'écart moyen est ≤ 1 mm) | A et B |

Notre objectif est le seuil de la norme : **0,5 mm**. Une monture qui respecte 1 mm suffit pour le jury, mais 0,5 mm est ce qu'il faut pour qu'elle soit utilisable par un patient.

```mermaid
flowchart LR
    A["Erreur sur A droit"] --> P["Erreur sur le pont<br/>= erreur PD - (erreur A droit + erreur A gauche) / 2"]
    B["Erreur sur A gauche"] --> P
    PD["Erreur sur le PD saisi"] --> P
    P --> T{"≤ 0,5 mm ?"}
```

Le pont est calculé à partir du PD et des largeurs A : la moitié de l'erreur de chaque verre s'y retrouve. Bien mesurer A compte donc deux fois.

## Résultats

Écart entre la mesure et la vraie taille, avec la norme (0,5 mm) et la grille du jury (1 mm) :

```mermaid
xychart-beta
    title "Écart de mesure en mm (norme : 0,5 mm, jury : 1 mm)"
    x-axis ["Synthétique A", "Synthétique B", "Feuille PDF A", "Feuille PDF B"]
    y-axis "Écart (mm)" 0 --> 1.2
    bar [0.20, 0.20, 0.18, 0.17]
    line [0.5, 0.5, 0.5, 0.5]
    line [1, 1, 1, 1]
```

| Test | Vraie taille | Mesuré |
|---|---|---|
| Photo synthétique inclinée (`MeasurementServiceTest`) | 50,0 × 36,0 mm | 50,2 × 36,2 mm |
| Feuille PDF rastérisée à 300 dpi, déformée en perspective | 52,0 × 37,9 mm | 52,2 × 38,1 mm |
| Monture STL, deux verres différents (50 × 36 et 46 × 40) | 1 pièce fermée, 4 trous | 1 pièce, 0 défaut de maillage, 4 trous |

Les mesures sont toutes environ 0,2 mm trop grandes : ce biais constant se corrige avec `optiframe.edge-bias-mm`. Sur de vrais verres, l'épaisseur du bord peut ajouter 0,3 à 0,5 mm : sans calibration, on dépasserait la norme.

> À compléter : verres réels mesurés au pied à coulisse, plusieurs prises par verre, avant et après calibration de `edge-bias-mm`.

## Limites connues

```mermaid
flowchart LR
    L1["Le bord du verre est quelques mm<br/>au-dessus de la feuille"] --> I1["Contour agrandi<br/>d'environ 1 % à 30 cm"] --> F1["Photographier de plus loin<br/>+ corriger avec edge-bias-mm"]
    L2["A et B suivent les axes de la feuille"] --> I2["Verre posé de travers,<br/>autres valeurs"] --> F2["Repères d'alignement sur la feuille<br/>+ rectangle minimal renvoyé aussi"]
    L3["Méthode classique réglée<br/>pour le rétroéclairage"] --> I3["Échoue sans lumière<br/>par-dessous"] --> F3["Modèle d'IA entraîné"]
    L4["La mesure se fait<br/>sur le serveur"] --> I4["Connexion nécessaire"] --> F4["Serveur toujours allumé<br/>pendant l'évaluation"]
    L5["Rainure et lèvres<br/>non encore imprimées"] --> I5["Clipsage à confirmer"] --> F5["Impression test,<br/>ajuster DEFAULT_FRAME"]

    classDef cause fill:#fef3c7,stroke:#b45309,color:#451a03
    classDef fix fill:#dcfce7,stroke:#15803d,color:#0b3d1c
    class L1,L2,L3,L4,L5 cause
    class F1,F2,F3,F4,F5 fix
```

[← Retour au README](../README.md)
