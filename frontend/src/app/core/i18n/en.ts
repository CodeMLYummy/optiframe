import { Messages } from './fr';

export const en: Messages = {
  'app.tagline': 'From recycled lenses to a 3D-printed frame',
  'app.language': 'Language',

  'sheet.title': 'Reference sheet',
  'sheet.paper': 'Paper size',
  'sheet.letter': 'Letter (8.5 × 11 in)',
  'sheet.a4': 'A4',
  'sheet.download': 'Download the sheet to print',
  'sheet.printHint':
    'Print at 100 %, then measure 10 squares of the checkerboard in a straight line: {mm} mm expected. Many printers shrink the sheet a little; enter what you measure.',
  'sheet.sizeMode': 'Printed size',
  'sheet.modeSquares': '10 squares (mm)',
  'sheet.modePercent': 'Scale (%)',
  'sheet.squaresLabel': 'Measured length of 10 squares (mm)',
  'sheet.percentLabel': 'Print scale (%)',
  'sheet.scaleUsed': 'Scale used for the measurements: {percent} %',
  'sheet.invalid':
    'Invalid value: 10 squares must measure between 120 and 180 mm (scale 80 to 120 %).',
  'sheet.placement':
    'Lay the sheet on a lit background, then the lens, convex side up, in the middle of the frame. Nasal side toward the middle of the glasses.',
  'sheet.alignStrong': 'Line the lens up straight with the horizontal marks of the frame',
  'sheet.alignRest':
    ': width A and height B are measured along the sheet’s axes, so a rotated lens gives values that are too large. Keep the whole sheet in the picture.',

  'lens.R': 'Right lens (OD)',
  'lens.L': 'Left lens (OS)',
  'lens.takePhoto': 'Take a photo',
  'lens.import': 'Import',
  'lens.analyzing': 'Analyzing the photo…',
  'lens.perimeter': 'Perimeter',
  'lens.controlAlt': 'Check image: detected outline',
  'lens.testLens': 'Test lens (50 × 36 mm ellipse)',
  'lens.useTestLens': 'Use a test lens',
  'lens.badScale':
    'Invalid printed size for the sheet: check the length of 10 squares in the Sheet step.',
  'lens.takesSpread': '{n} photos of this lens: A differs by {a} mm, B by {b} mm',
  'lens.takesOk': 'consistent',
  'lens.takesWarn': 'more than {mm} mm: take the photo again',
  'lens.take': 'A {a} × B {b} mm',
  'lens.takeUsed': ' (used)',
  'lens.clearTakes': 'New lens: forget these photos',
  'lens.secondTake': 'Take a 2nd photo of this lens to check that the measurement is stable.',

  'pair.title': 'Lens outlines',
  'pair.download': 'Download the pair as SVG 1:1',
  'pair.hint':
    'Both outlines are in one file, at their measured size. Print at 100 %, without fitting to the page. The spacing between the lenses is not the bridge of the frame.',
  'pair.measureBoth': 'Measure both lenses to export the pair.',
  'pair.missing': 'Measure both lenses before exporting their outlines.',

  'frame.title': 'Frame',
  'frame.pd': 'Patient’s pupillary distance (PD, mm)',
  'frame.pdExample': 'e.g. 63',
  'frame.pdRight': 'Right PD (OD)',
  'frame.pdLeft': 'Left PD (OS)',
  'frame.pdHalfExample': 'e.g. 31.5',
  'frame.perEye': 'PD per eye',
  'frame.bridge': 'Calculated bridge:',
  'frame.standardBridge': 'No PD: standard {mm} mm bridge.',
  'frame.pdTooSmall':
    'PD too small for these lenses: only {mm} mm is left for the bridge (minimum {min} mm).',
  'frame.bridgeUnusual':
    '{mm} mm bridge, outside the usual range ({min} to {max} mm). Check the PD and the lens sizes.',
  'frame.generate': 'Generate the frame',
  'frame.generating': 'Generating…',
  'frame.measureFirst': 'Measure both lenses first.',
  'frame.failed': 'Could not generate the frame from these outlines. Take the photos again.',
  'frame.stats': '{triangles} triangles · {cm3} cm³ of filament',
  'frame.downloadFront': 'Download monture.stl',
  'frame.downloadTemples': 'Download branches.stl',
  'frame.templesHint':
    'Attach each temple to its lug with a paper clip or a piece of 1.75 mm filament: tight in the lug, free in the fork.',

  'fit.title': 'Check: lenses and frame',
  'fit.intro':
    'Each lens’s measured outline is drawn over the rim of the generated frame. The bottom of the groove must be the same distance from the lens all around, and the front lip must cover the edge of the lens.',
  'fit.aria': 'Outline and frame overlaid, {lens}',
  'fit.groove': 'Lens → groove bottom: {mean} mm (min {min}, max {max}), designed {expected} mm',
  'fit.lip':
    'Front lip over the lens edge: {mean} mm (min {min}, max {max}), designed {expected} mm',
  'fit.keyContour': 'measured outline',
  'fit.keyGroove': 'groove bottom',
  'fit.keyLip': 'front lip opening',

  'face.title': 'Preview on the face',
  'face.tryOn': 'Try it on',
  'face.importSelfie': 'Import a selfie',
  'face.privacy': 'Analyzed on the phone: the image is never sent or saved.',
  'face.loading': 'Loading face tracking…',
  'face.selfieAlt': 'Imported selfie',
  'face.scale':
    'True size, scaled from the iris (± 5 %). PD estimated from the image: {pd} mm (± 3 mm).',
  'face.framePd': 'Frame PD: {pd} mm.',
  'face.usePd': 'Use this PD',
  'face.position': 'Face the camera, eyes open, in good light.',
  'face.stop': 'Stop the camera',
  'face.cameraDenied': 'Camera denied or unavailable: import a selfie instead.',
  'face.noFace': 'No face found: use a front-facing photo, eyes open, in good light.',
  'face.unsupported':
    'Face tracking does not work in this browser. Try an up-to-date Chrome or Safari.',

  'steps.link': 'See each step',
  'steps.back': 'Back',
  'steps.details': '{markers} markers · fit error {error} mm · {ppm} px/mm · {method} · {ms} ms',
  'steps.none': 'No photo measured yet.',
  'steps.1': '1. Detected markers',
  'steps.2': '2. Rectified sheet',
  'steps.3': '3. Lens outline',

  'error.unreachable': 'Server unreachable. Check the connection and try again.',
  'error.unexpected': 'Unexpected error. Try again.',
  'error.unreadableImage': 'Could not read the image.',
  'error.IMAGE_UNREADABLE': 'Unreadable image. Use a JPEG or PNG photo.',
  'error.MARKERS_NOT_FOUND':
    'Reference sheet not found. Keep the whole sheet in the picture, with no glare on the checkerboard.',
  'error.SCALE_CHECK_FAILED':
    'The sheet looks folded or was poorly detected. Lay it flat and take the photo again.',
  'error.PHOTO_BLURRY': 'Blurry photo. Hold the phone still and tap the screen to focus.',
  'error.LENS_NOT_FOUND':
    'Lens not found. Place it in the middle of the frame, on the lit background.',
  'error.LENS_OUT_OF_WINDOW': 'The lens goes past the frame. Center it in the sheet’s rectangle.',
  'error.PRINT_SCALE_INVALID':
    'Invalid print scale. Measure 10 squares of the sheet: they must be between 120 and 180 mm.',
  'app.home': 'OptiFrame home',
  'app.themeSystem': 'Theme: automatic (system)',
  'app.themeLight': 'Theme: light',
  'app.themeDark': 'Theme: dark',

  'nav.steps': 'Steps',
  'nav.step': 'Step {n} of {total}: {name}',
  'nav.back': 'Back',
  'nav.next': 'Continue',
  'nav.start': 'Start',
  'nav.resume': 'Resume',
  'nav.toFiles': 'Files',

  'step.sheet': 'Sheet',
  'step.right': 'Right lens',
  'step.left': 'Left lens',
  'step.frame': 'Frame',
  'step.files': 'Files',

  'block.sheet': 'Enter a valid printed size to continue.',
  'block.right': 'Measure the right lens to continue.',
  'block.left': 'Measure the left lens to continue.',
  'block.frame': 'Generate the frame to continue.',

  'welcome.title': 'From a recycled lens to a print-ready file, in five steps',
  'welcome.chart': 'The five steps, read from top to bottom',
  'welcome.need': 'You will need',
  'welcome.needSheet': 'The reference sheet, printed (step 1)',
  'welcome.needLight': 'A lit background: a window, or a white screen',
  'welcome.needLenses': 'Both lenses, clean and dry',

  'sheet.lead':
    'The sheet gives the scale of every measurement. Print it, then enter its real size.',
  'sheet.print': 'Print',
  'sheet.measure': 'Measure the printed sheet',
  'sheet.place': 'Place the lens',

  'lens.leadR': 'Lay the right lens on the sheet, convex side up, then photograph the whole sheet.',
  'lens.leadL':
    'Same for the left lens: lens in the middle of the frame, whole sheet in the photo.',
  'lens.retake': 'New photo',
  'lens.result': 'Measurement',
  'lens.coherence': 'Measurement stability',

  'frame.lead': 'Enter the patient’s pupillary distance, then generate the frame.',
  'frame.viewerHint': 'Drag to rotate the frame.',
  'frame.ready': 'Frame ready',

  'files.lead': 'Download the files to print. The checks below are optional.',
  'files.print3d': '3D printing',
  'files.frontDesc': 'Frame front · {cm3} cm³ of filament',
  'files.templesDesc': 'Two {mm} mm temples, printed flat',
  'files.pairDesc': '1:1 outlines of both lenses, print at 100 %',
  'files.paper': 'Paper',
  'files.checks': 'Optional checks',
  'files.fitDesc': 'Measured outline over the frame rim',
  'files.faceDesc': 'The frame at true size on a face',
  'files.stepsDesc': 'What the program did, step by step',
  'files.needFrame': 'Generate the frame in step 4 first.',
  'files.goFrame': 'Go to the Frame step',

  'lens.measured': 'Lens measured',
  'steps.lead':
    'Each photo goes through three stages: finding the markers, straightening the sheet, then tracing the lens outline. The figures show how precisely each stage worked.',
  'steps.title': 'Measurement process',
};
