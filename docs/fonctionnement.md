# Fonctionnement

## Parcours de l'utilisateur

L'app guide l'utilisateur en cinq étapes, une à la fois. L'accueil les présente comme les lignes d'un tableau d'acuité. En haut de l'écran, l'échelle des étapes (1 à 5) montre l'étape en cours, soulignée en rouge, et coche en vert celles qui sont terminées. Le bouton **Continuer**, en bas, reste désactivé tant que l'étape n'a pas son résultat, avec une phrase qui dit ce qui manque.

| Étape                | Ce que fait l'utilisateur                                                                                        | Pour continuer                              |
| -------------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------- |
| 1. Feuille           | Choisit Letter ou A4, télécharge la feuille, indique la longueur mesurée de 10 cases (ou l'échelle d'impression) | Une taille d'impression valide (80 à 120 %) |
| 2. Verre droit (OD)  | Prend la photo ou l'importe ; peut en prendre une 2e pour vérifier la stabilité                                  | Le verre droit mesuré                       |
| 3. Verre gauche (OG) | Même chose avec le verre gauche                                                                                  | Le verre gauche mesuré                      |
| 4. Monture           | Saisit le PD (total ou par œil), puis **Générer la monture** depuis la barre du bas                              | La monture générée                          |
| 5. Fichiers          | Télécharge `monture.stl`, `branches.stl` et `contours-paire.svg`                                                 | —                                           |

Depuis l'étape **Fichiers**, trois vérifications facultatives :

- **Vérification : verres et monture** : contour mesuré superposé au cercle de la monture, écart en mm tout autour.
- **Aperçu sur le visage** : monture à taille réelle sur la caméra frontale ou un selfie, analysée sur le téléphone. Le PD estimé peut remplacer celui saisi ; l'app renvoie alors à l'étape Monture pour régénérer.
- **Processus de mesure** : pour chaque verre, ce que le programme a fait, étape par étape (voir plus bas).

L'app suit le thème clair ou sombre du système, ou celui choisi avec le bouton en haut à droite. Elle existe en français, anglais et espagnol. Le thème, la langue et les réglages de la feuille sont gardés sur le téléphone.

```mermaid
sequenceDiagram
    actor U as Utilisateur
    participant App as Application (téléphone)
    participant API as Serveur

    U->>App: Ouvre le lien (QR code), Commencer
    U->>App: Étape 1 : imprime la feuille, indique sa taille réelle
    loop Étapes 2 et 3 : chaque verre (droit, puis gauche)
        U->>App: Prend la photo
        App->>App: Corrige l'orientation, réduit à 4000 px
        App->>API: Envoie la photo et l'échelle d'impression
        alt Photo correcte
            API-->>App: Contour + mesures + images de contrôle
            App-->>U: Affiche A × B et le périmètre, Continuer s'active
        else Problème détecté
            API-->>App: Message clair (feuille, flou, verre mal placé)
            App-->>U: "Reprenez la photo : ..."
        end
    end
    U->>App: Étape 4 : saisit le PD (ou PD par œil), Générer la monture
    App->>App: Calcule la monture en 3D (sur le téléphone)
    App-->>U: Aperçu 3D, Continuer
    U->>App: Étape 5 : télécharge monture.stl, branches.stl, contours SVG
```

## Comment une photo devient une mesure

Chaque contrôle peut arrêter le traitement avec un message clair qui dit quoi corriger, dans la langue de l'app.

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

Les trois images de contrôle, visibles dans la page **Processus de mesure** de l'app (étape Fichiers), avec le nombre de marqueurs trouvés, l'écart d'ajustement en mm, la résolution en px/mm, la méthode de segmentation et la durée :

```mermaid
flowchart LR
    I1["Étape 1<br/>Marqueurs détectés<br/>sur la photo d'origine"] --> I2["Étape 2<br/>Feuille redressée<br/>vue de dessus"] --> I3["Étape 3<br/>Contour du verre<br/>avec A et B"]
```

[← Retour au README](../README.md)
