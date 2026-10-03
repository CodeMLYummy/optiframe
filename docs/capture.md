# Dispositif de capture

```mermaid
flowchart TB
    PH[/"Téléphone, tenu de face<br/>à 30-40 cm, zoom ×2 si possible"/]
    LENS["Verre, face bombée vers le haut,<br/>au centre du cadre"]
    SHEET["Feuille imprimée à 100 %<br/>8 marqueurs ArUco + règle de 100 mm"]
    LIGHT["Écran blanc d'un portable<br/>ou fenêtre (lumière par-dessous)"]
    PH -. "photo de toute la feuille" .-> LENS
    LENS --- SHEET --- LIGHT

    classDef lens fill:#dbeafe,stroke:#1d4ed8,color:#0b1f4d
    classDef light fill:#fef3c7,stroke:#b45309,color:#451a03
    class LENS lens
    class LIGHT light
```

1. Imprimer `frontend/public/feuille-optiframe.pdf` **à 100 %** et vérifier la règle de 100 mm au pied à coulisse.
2. Poser la feuille sur l'écran blanc d'un portable (luminosité maximale) ou contre une fenêtre.
3. Poser le verre au centre du cadre, horizontal entre les repères.
4. Photographier toute la feuille, de face.

La disposition de la feuille est définie une seule fois dans `backend/src/main/resources/sheet-layout.json`. Le serveur et `training/make_sheet.py` lisent ce même fichier, donc la feuille imprimée et le détecteur restent toujours d'accord.

[← Retour au README](../README.md)
