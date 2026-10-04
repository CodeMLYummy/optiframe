import { Messages } from './fr';

export const es: Messages = {
  'app.tagline': 'De la lente reciclada a la montura impresa en 3D',
  'app.language': 'Idioma',

  'sheet.title': 'Hoja de referencia',
  'sheet.paper': 'Tamaño del papel',
  'sheet.letter': 'Carta (8,5 × 11 pulg.)',
  'sheet.a4': 'A4',
  'sheet.download': 'Descargar la hoja para imprimir',
  'sheet.printHint':
    'Imprima al 100 % y mida 10 casillas del damero en línea recta: se esperan {mm} mm. Muchas impresoras reducen un poco la hoja; indique lo que mide.',
  'sheet.sizeMode': 'Tamaño impreso',
  'sheet.modeSquares': 'Longitud de 10 casillas',
  'sheet.modePercent': 'Escala de impresión',
  'sheet.squaresLabel': 'Longitud medida de 10 casillas (mm)',
  'sheet.percentLabel': 'Escala de impresión (%)',
  'sheet.scaleUsed': 'Escala usada para las medidas: {percent} %',
  'sheet.invalid':
    'Valor no válido: 10 casillas deben medir entre 120 y 180 mm (escala del 80 al 120 %).',
  'sheet.placement':
    'Coloque la hoja sobre un fondo iluminado y luego la lente, con la cara convexa hacia arriba, en el centro del marco. El lado nasal hacia el centro de la montura.',
  'sheet.alignStrong': 'Alinee la lente bien recta con las marcas horizontales del marco',
  'sheet.alignRest':
    ': el ancho A y el alto B se miden según los ejes de la hoja; una lente girada da valores demasiado grandes. Encuadre toda la hoja.',

  'lens.R': 'Lente derecha (OD)',
  'lens.L': 'Lente izquierda (OI)',
  'lens.takePhoto': '📷 Tomar una foto',
  'lens.import': 'Importar',
  'lens.analyzing': 'Analizando la foto…',
  'lens.perimeter': 'Perímetro',
  'lens.controlAlt': 'Imagen de control: contorno detectado',
  'lens.testLens': 'Lente de prueba (elipse de 50 × 36 mm)',
  'lens.useTestLens': 'Usar una lente de prueba',
  'lens.badScale':
    'Tamaño de impresión de la hoja no válido: revise la longitud de las 10 casillas (arriba).',
  'lens.takesSpread': '{n} fotos de esta lente: diferencia A {a} mm, B {b} mm',
  'lens.takesOk': '✓ coherente',
  'lens.takesWarn': '⚠ más de {mm} mm: repita la foto',
  'lens.take': 'A {a} × B {b} mm',
  'lens.takeUsed': ' (usada)',
  'lens.clearTakes': 'Lente nueva: olvidar estas fotos',
  'lens.secondTake': 'Tome una 2.ª foto de esta lente para comprobar que la medida es estable.',

  'pair.title': 'Contornos de las lentes',
  'pair.download': 'Descargar el par en SVG 1:1',
  'pair.hint':
    'Los dos contornos están en un solo archivo, a su tamaño medido. Imprima al 100 %, sin ajustar a la página. La separación entre las lentes no representa el puente de la montura.',
  'pair.measureBoth': 'Mida las dos lentes para exportar el par.',
  'pair.missing': 'Mida las dos lentes antes de exportar sus contornos.',

  'frame.title': 'Montura',
  'frame.pd': 'Distancia pupilar del paciente (DP, mm)',
  'frame.pdExample': 'p. ej. 63',
  'frame.pdRight': 'DP derecha (OD)',
  'frame.pdLeft': 'DP izquierda (OI)',
  'frame.pdHalfExample': 'p. ej. 31.5',
  'frame.perEye': 'DP por ojo',
  'frame.bridge': 'Puente calculado:',
  'frame.standardBridge': 'Sin DP: puente estándar de {mm} mm.',
  'frame.pdTooSmall':
    'DP demasiado pequeña para estas lentes: solo quedan {mm} mm para el puente (mínimo {min} mm).',
  'frame.bridgeUnusual':
    'Puente de {mm} mm, fuera del rango habitual ({min} a {max} mm). Revise la DP y el tamaño de las lentes.',
  'frame.generate': 'Generar la montura',
  'frame.generating': 'Generando…',
  'frame.measureFirst': 'Mida primero las dos lentes.',
  'frame.failed': 'No se pudo generar la montura con estos contornos. Repita las fotos.',
  'frame.stats': '{triangles} triángulos · {cm3} cm³ de filamento',
  'frame.downloadFront': 'Descargar monture.stl',
  'frame.downloadTemples': 'Descargar branches.stl',
  'frame.templesHint':
    'Patillas de {mm} mm, para imprimir en plano. Fije cada patilla a su soporte con un clip o un trozo de filamento de 1,75 mm: ajustado en el soporte, libre en la horquilla.',

  'fit.title': 'Verificación: lentes y montura',
  'fit.intro':
    'El contorno medido de cada lente se superpone al aro de la montura generada. El fondo de la ranura debe estar a la misma distancia de la lente en todo el contorno, y el labio frontal debe cubrir el borde de la lente.',
  'fit.aria': 'Contorno y montura superpuestos, {lens}',
  'fit.groove':
    'Lente → fondo de la ranura: {mean} mm (mín. {min}, máx. {max}), previsto {expected} mm',
  'fit.lip':
    'Labio frontal sobre el borde de la lente: {mean} mm (mín. {min}, máx. {max}), previsto {expected} mm',
  'fit.keyContour': 'contorno medido',
  'fit.keyGroove': 'fondo de la ranura',
  'fit.keyLip': 'abertura del labio frontal',

  'face.title': 'Vista previa en el rostro',
  'face.tryOn': 'Probar en el rostro',
  'face.importSelfie': 'Importar un selfie',
  'face.privacy': 'Análisis hecho en el teléfono: la imagen no se envía ni se guarda.',
  'face.loading': 'Cargando el seguimiento del rostro…',
  'face.selfieAlt': 'Selfie importado',
  'face.scale':
    'Tamaño real, escala tomada del iris (± 5 %). DP estimada en la imagen: {pd} mm (± 3 mm).',
  'face.framePd': 'DP de la montura: {pd} mm.',
  'face.usePd': 'Usar esta DP',
  'face.position': 'Mire de frente a la cámara, con los ojos abiertos y buena luz.',
  'face.stop': 'Detener la cámara',
  'face.cameraDenied': 'Cámara denegada o no disponible: importe un selfie.',
  'face.noFace': 'No se encontró ningún rostro: foto de frente, ojos abiertos y buena luz.',
  'face.unsupported':
    'El seguimiento del rostro no funciona en este navegador. Pruebe Chrome o Safari actualizados.',

  'steps.link': 'Ver paso a paso',
  'steps.back': '← Volver',
  'steps.details':
    '{markers} marcadores · error de ajuste {error} mm · {ppm} px/mm · {method} · {ms} ms',
  'steps.none': 'Todavía no hay ninguna foto medida.',
  'steps.1': '1. Marcadores detectados',
  'steps.2': '2. Hoja enderezada',
  'steps.3': '3. Contorno de la lente',

  'error.unreachable': 'Servidor inaccesible. Revise la conexión e inténtelo de nuevo.',
  'error.unexpected': 'Error inesperado. Inténtelo de nuevo.',
  'error.unreadableImage': 'No se pudo leer la imagen.',
  'error.IMAGE_UNREADABLE': 'Imagen ilegible. Use una foto JPEG o PNG.',
  'error.MARKERS_NOT_FOUND':
    'No se encuentra la hoja de referencia. Encuadre toda la hoja, sin reflejos en el damero.',
  'error.SCALE_CHECK_FAILED':
    'La hoja parece doblada o mal detectada. Colóquela bien plana y repita la foto.',
  'error.PHOTO_BLURRY':
    'Foto borrosa. Mantenga el teléfono inmóvil y toque la pantalla para enfocar.',
  'error.LENS_NOT_FOUND':
    'No se encuentra la lente. Colóquela en el centro del marco, sobre el fondo iluminado.',
  'error.LENS_OUT_OF_WINDOW': 'La lente sobresale del marco. Céntrela en el rectángulo de la hoja.',
  'error.PRINT_SCALE_INVALID':
    'Escala de impresión no válida. Mida 10 casillas de la hoja: deben medir entre 120 y 180 mm.',
};
