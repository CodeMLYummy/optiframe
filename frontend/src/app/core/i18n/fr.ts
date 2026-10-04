/**
 * French, the reference language: every other language must define exactly these keys (checked by the compiler).
 * `{name}` is replaced by a parameter; numbers are formatted by the caller in the current language.
 */
export const fr = {
  'app.tagline': 'Du verre recyclé à la monture imprimée en 3D',
  'app.language': 'Langue',

  'sheet.title': 'Feuille de référence',
  'sheet.paper': 'Format du papier',
  'sheet.letter': 'Letter (8,5 × 11 po)',
  'sheet.a4': 'A4',
  'sheet.download': 'Télécharger la feuille à imprimer',
  'sheet.printHint':
    "Imprimez à 100 %, puis mesurez 10 cases du damier (en ligne droite) : {mm} mm attendus. Beaucoup d'imprimantes réduisent un peu la feuille ; indiquez ce que vous mesurez.",
  'sheet.sizeMode': "Taille d'impression",
  'sheet.modeSquares': 'Longueur de 10 cases',
  'sheet.modePercent': "Échelle d'impression",
  'sheet.squaresLabel': 'Longueur mesurée de 10 cases (mm)',
  'sheet.percentLabel': "Échelle d'impression (%)",
  'sheet.scaleUsed': 'Échelle utilisée pour les mesures : {percent} %',
  'sheet.invalid': 'Valeur invalide : 10 cases doivent mesurer entre 120 et 180 mm (échelle 80 à 120 %).',
  'sheet.placement':
    'Posez la feuille sur un fond éclairé, puis le verre, face bombée vers le haut, au centre du cadre. Côté nasal vers le centre de la monture.',
  'sheet.alignStrong': 'Alignez le verre bien droit sur les repères horizontaux du cadre',
  'sheet.alignRest':
    ' : la largeur A et la hauteur B sont mesurées selon les axes de la feuille, un verre tourné donne des valeurs trop grandes. Cadrez toute la feuille.',

  'lens.R': 'Verre droit (OD)',
  'lens.L': 'Verre gauche (OG)',
  'lens.takePhoto': '📷 Prendre une photo',
  'lens.import': 'Importer',
  'lens.analyzing': 'Analyse de la photo…',
  'lens.perimeter': 'Périmètre',
  'lens.controlAlt': 'Image de contrôle : contour détecté',
  'lens.testLens': 'Verre de test (ellipse 50 × 36 mm)',
  'lens.useTestLens': 'Utiliser un verre de test',
  'lens.badScale': "Taille d'impression de la feuille invalide : vérifiez la longueur des 10 cases (en haut).",
  'lens.takesSpread': '{n} photos de ce verre : écart A {a} mm, B {b} mm',
  'lens.takesOk': '✓ cohérent',
  'lens.takesWarn': '⚠ plus de {mm} mm : reprenez la photo',
  'lens.take': 'A {a} × B {b} mm',
  'lens.takeUsed': ' (utilisée)',
  'lens.clearTakes': 'Nouveau verre : oublier ces photos',
  'lens.secondTake': 'Reprenez une 2e photo de ce verre pour vérifier que la mesure est stable.',

  'pair.title': 'Contours des verres',
  'pair.download': 'Télécharger la paire en SVG 1:1',
  'pair.hint':
    "Les deux contours sont réunis dans un seul fichier, à leur taille mesurée. Imprimez à 100 %, sans ajuster à la page. L'espacement entre les verres ne représente pas le pont de la monture.",
  'pair.measureBoth': 'Mesurez les deux verres pour exporter la paire.',
  'pair.missing': "Mesurez les deux verres avant d'exporter leurs contours.",

  'frame.title': 'Monture',
  'frame.pd': 'Écart pupillaire du patient (PD, mm)',
  'frame.pdExample': 'ex. 63',
  'frame.pdRight': 'PD droit (OD)',
  'frame.pdLeft': 'PD gauche (OG)',
  'frame.pdHalfExample': 'ex. 31.5',
  'frame.perEye': 'PD par œil',
  'frame.bridge': 'Pont calculé :',
  'frame.standardBridge': 'Sans PD : pont standard de {mm} mm.',
  'frame.pdTooSmall': 'PD trop petit pour ces verres : il ne reste que {mm} mm pour le pont (minimum {min} mm).',
  'frame.bridgeUnusual':
    'Pont de {mm} mm, hors de la plage habituelle ({min} à {max} mm). Vérifiez le PD et la taille des verres.',
  'frame.generate': 'Générer la monture',
  'frame.generating': 'Génération…',
  'frame.measureFirst': "Mesurez les deux verres d'abord.",
  'frame.failed': 'Impossible de générer la monture avec ces contours. Reprenez les photos.',
  'frame.stats': '{triangles} triangles · {cm3} cm³ de filament',
  'frame.downloadFront': 'Télécharger monture.stl',
  'frame.downloadTemples': 'Télécharger branches.stl',
  'frame.templesHint':
    'Branches de {mm} mm, à imprimer à plat. Fixez chaque branche à son tenon avec un trombone ou un bout de filament de 1,75 mm : serré dans le tenon, libre dans la fourche.',

  'fit.title': 'Vérification : verres et monture',
  'fit.intro':
    'Le contour mesuré de chaque verre est superposé au cercle de la monture générée. Le fond de la rainure doit être à la même distance du verre tout autour, et la lèvre avant doit recouvrir le bord du verre.',
  'fit.aria': 'Contour et monture superposés, {lens}',
  'fit.groove': 'Verre → fond de rainure : {mean} mm (min {min}, max {max}), prévu {expected} mm',
  'fit.lip': 'Lèvre avant sur le bord du verre : {mean} mm (min {min}, max {max}), prévu {expected} mm',
  'fit.keyContour': 'contour mesuré',
  'fit.keyGroove': 'fond de la rainure',
  'fit.keyLip': 'ouverture de la lèvre avant',

  'face.title': 'Aperçu sur le visage',
  'face.tryOn': 'Essayer sur le visage',
  'face.importSelfie': 'Importer un selfie',
  'face.privacy': "Analyse faite sur le téléphone : l'image n'est envoyée nulle part ni enregistrée.",
  'face.loading': 'Chargement du suivi du visage…',
  'face.selfieAlt': 'Selfie importé',
  'face.scale': "Taille réelle, échelle donnée par l'iris (± 5 %). PD estimé sur l'image : {pd} mm (± 3 mm).",
  'face.framePd': 'PD de la monture : {pd} mm.',
  'face.usePd': 'Utiliser ce PD',
  'face.position': 'Placez votre visage de face, yeux ouverts, bien éclairé.',
  'face.stop': 'Arrêter la caméra',
  'face.cameraDenied': 'Caméra refusée ou indisponible : importez plutôt un selfie.',
  'face.noFace': 'Aucun visage trouvé : photo de face, yeux ouverts, bien éclairée.',
  'face.unsupported': 'Le suivi du visage ne fonctionne pas sur ce navigateur. Essayez Chrome ou Safari à jour.',

  'steps.link': 'Voir le pas à pas',
  'steps.back': '← Retour',
  'steps.details': "{markers} marqueurs · écart d'ajustement {error} mm · {ppm} px/mm · {method} · {ms} ms",
  'steps.none': "Aucune photo mesurée pour l'instant.",
  'steps.1': '1. Marqueurs détectés',
  'steps.2': '2. Feuille redressée',
  'steps.3': '3. Contour du verre',

  'error.unreachable': 'Serveur injoignable. Vérifiez la connexion et réessayez.',
  'error.unexpected': 'Erreur inattendue. Réessayez.',
  'error.unreadableImage': "Impossible de lire l'image.",
  'error.IMAGE_UNREADABLE': 'Image illisible. Utilisez une photo JPEG ou PNG.',
  'error.MARKERS_NOT_FOUND': 'Feuille de référence introuvable. Cadrez toute la feuille, sans reflet sur le damier.',
  'error.SCALE_CHECK_FAILED': 'La feuille semble pliée ou mal détectée. Posez-la bien à plat et reprenez la photo.',
  'error.PHOTO_BLURRY': "Photo floue. Tenez le téléphone immobile et touchez l'écran pour faire la mise au point.",
  'error.LENS_NOT_FOUND': 'Verre introuvable. Placez-le au centre du cadre, sur le fond éclairé.',
  'error.LENS_OUT_OF_WINDOW': 'Le verre dépasse du cadre. Centrez-le dans le rectangle de la feuille.',
  'error.PRINT_SCALE_INVALID': "Échelle d'impression invalide. Mesurez 10 cases de la feuille : elles doivent faire entre 120 et 180 mm.",
};

export type MessageKey = keyof typeof fr;
export type Messages = Record<MessageKey, string>;
