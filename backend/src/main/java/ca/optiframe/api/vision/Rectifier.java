package ca.optiframe.api.vision;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.opencv.calib3d.Calib3d;
import org.opencv.core.Core;
import org.opencv.core.Mat;
import org.opencv.core.MatOfPoint;
import org.opencv.core.MatOfPoint2f;
import org.opencv.core.Point;
import org.opencv.core.Size;
import org.opencv.imgproc.Imgproc;
import org.opencv.objdetect.ArucoDetector;
import org.opencv.objdetect.DetectorParameters;
import org.opencv.objdetect.Dictionary;
import org.opencv.objdetect.Objdetect;
import org.springframework.stereotype.Component;

import ca.optiframe.api.config.OptiframeProperties;
import ca.optiframe.api.sheet.SheetLayout;
import ca.optiframe.api.vision.MeasurementException.Code;

/** Finds the ArUco markers of the sheet and warps the photo to a top-down view with a known scale. */
@Component
public class Rectifier {

	private static final int MIN_MARKERS = 3;

	private final SheetLayout layout;
	private final OptiframeProperties props;
	private final Map<Integer, SheetLayout.Marker> markersById;
	private final Dictionary dictionary;

	public Rectifier(SheetLayout layout, OptiframeProperties props) {
		OpenCv.ensureLoaded();
		this.layout = layout;
		this.props = props;
		this.markersById = layout.markers().stream()
				.collect(Collectors.toMap(SheetLayout.Marker::id, Function.identity()));
		this.dictionary = Objdetect.getPredefinedDictionary(dictionaryId(layout.dictionary()));
	}

	public RectifiedSheet rectify(Mat photo) {
		Mat gray = new Mat();
		Imgproc.cvtColor(photo, gray, Imgproc.COLOR_BGR2GRAY);

		DetectorParameters params = new DetectorParameters();
		params.set_cornerRefinementMethod(Objdetect.CORNER_REFINE_SUBPIX);
		ArucoDetector detector = new ArucoDetector(dictionary, params);
		List<Mat> corners = new ArrayList<>();
		Mat ids = new Mat();
		detector.detectMarkers(gray, corners, ids);

		double ppm = props.pxPerMm();
		List<Point> imagePts = new ArrayList<>();
		List<Point> sheetPts = new ArrayList<>();
		List<Integer> usedIds = new ArrayList<>();
		List<MatOfPoint> quads = new ArrayList<>();
		for (int i = 0; i < corners.size(); i++) {
			int id = (int) ids.get(i, 0)[0];
			SheetLayout.Marker marker = markersById.get(id);
			if (marker == null) {
				continue;
			}
			Point[] quad = new Point[4];
			for (int k = 0; k < 4; k++) {
				double[] p = corners.get(i).get(0, k);
				quad[k] = new Point(p[0], p[1]);
				imagePts.add(quad[k]);
				sheetPts.add(scale(markerCornerMm(marker, k), ppm));
			}
			usedIds.add(id);
			quads.add(new MatOfPoint(quad));
		}
		if (usedIds.size() < MIN_MARKERS) {
			throw new MeasurementException(Code.MARKERS_NOT_FOUND,
					"Feuille de référence introuvable (" + usedIds.size() + " marqueur(s) détecté(s) sur "
							+ layout.markers().size() + "). Cadrez toute la feuille, sans reflet sur les marqueurs.");
		}

		MatOfPoint2f src = new MatOfPoint2f(imagePts.toArray(Point[]::new));
		MatOfPoint2f dst = new MatOfPoint2f(sheetPts.toArray(Point[]::new));
		Mat homography = Calib3d.findHomography(src, dst, Calib3d.RANSAC, 0.3 * ppm);
		if (homography.empty()) {
			throw new MeasurementException(Code.MARKERS_NOT_FOUND,
					"Impossible de redresser la photo. Reprenez-la en cadrant toute la feuille.");
		}

		double errorMm = reprojectionErrorPx(src, dst, homography) / ppm;
		if (errorMm > props.maxReprojectionErrorMm()) {
			throw new MeasurementException(Code.SCALE_CHECK_FAILED, String.format(
					"La feuille semble pliée ou mal détectée (écart %.2f mm). Posez-la bien à plat et reprenez la photo.",
					errorMm));
		}

		Mat rectified = new Mat();
		Size size = new Size(layout.paper().widthMm() * ppm, layout.paper().heightMm() * ppm);
		Imgproc.warpPerspective(photo, rectified, homography, size, Imgproc.INTER_LINEAR);
		return new RectifiedSheet(rectified, ppm, usedIds, quads, errorMm);
	}

	/** ArUco corner order: top-left, top-right, bottom-right, bottom-left. */
	private Point markerCornerMm(SheetLayout.Marker m, int k) {
		double s = layout.markerSizeMm();
		return switch (k) {
			case 0 -> new Point(m.xMm(), m.yMm());
			case 1 -> new Point(m.xMm() + s, m.yMm());
			case 2 -> new Point(m.xMm() + s, m.yMm() + s);
			default -> new Point(m.xMm(), m.yMm() + s);
		};
	}

	private static Point scale(Point p, double f) {
		return new Point(p.x * f, p.y * f);
	}

	private static double reprojectionErrorPx(MatOfPoint2f src, MatOfPoint2f dst, Mat homography) {
		MatOfPoint2f projected = new MatOfPoint2f();
		Core.perspectiveTransform(src, projected, homography);
		Point[] a = projected.toArray();
		Point[] b = dst.toArray();
		double sum = 0;
		for (int i = 0; i < a.length; i++) {
			sum += Math.hypot(a[i].x - b[i].x, a[i].y - b[i].y);
		}
		return sum / a.length;
	}

	private static int dictionaryId(String name) {
		try {
			return Objdetect.class.getField(name).getInt(null);
		}
		catch (ReflectiveOperationException e) {
			throw new IllegalArgumentException("Unknown ArUco dictionary in sheet-layout.json: " + name, e);
		}
	}

}
