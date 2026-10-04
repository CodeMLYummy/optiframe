package ca.optiframe.api.vision;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

import org.opencv.calib3d.Calib3d;
import org.opencv.core.Core;
import org.opencv.core.Mat;
import org.opencv.core.MatOfPoint;
import org.opencv.core.MatOfPoint2f;
import org.opencv.core.MatOfPoint3f;
import org.opencv.core.Point;
import org.opencv.core.Point3;
import org.opencv.core.Size;
import org.opencv.imgproc.Imgproc;
import org.opencv.objdetect.ArucoDetector;
import org.opencv.objdetect.CharucoBoard;
import org.opencv.objdetect.CharucoDetector;
import org.opencv.objdetect.CharucoParameters;
import org.opencv.objdetect.DetectorParameters;
import org.opencv.objdetect.Dictionary;
import org.opencv.objdetect.Objdetect;
import org.opencv.objdetect.RefineParameters;
import org.springframework.stereotype.Component;

import ca.optiframe.api.config.OptiframeProperties;
import ca.optiframe.api.sheet.SheetLayout;
import ca.optiframe.api.vision.MeasurementException.Code;

/**
 * Finds the reference sheet and warps the photo to a top-down view with a known scale. Supports the ArUco sheet
 * (corners of separate markers) and the ChArUco sheet (chessboard corners, sub-pixel, many more points).
 */
@Component
public class Rectifier {

	private static final int MIN_MARKERS = 3;
	/** Enough ChArUco corners for a stable homography, still reachable when part of the board is cropped. */
	private static final int MIN_CHARUCO_CORNERS = 8;
	/** Board corners on the lens window edge have no chessboard around them: the generator says to ignore them. */
	private static final double WINDOW_EDGE_MARGIN_MM = 0.5;

	private final SheetLayout layout;
	private final OptiframeProperties props;
	private final Map<Integer, SheetLayout.Marker> markersById;
	private final Dictionary dictionary;
	/** ChArUco only: corner positions by corner id, marker squares by marker id. */
	private final Point3[] boardCorners;
	private final Map<Integer, SheetLayout.Rect> boardMarkers;
	private final CharucoBoard board;

	/** Point correspondences between the photo (px) and the sheet (mm). */
	private record Matches(List<Point> imagePx, List<Point> sheetMm, List<Integer> markerIds, List<MatOfPoint> quads,
			List<SheetLayout.Rect> markerAreasMm) {
	}

	public Rectifier(SheetLayout layout, OptiframeProperties props) {
		OpenCv.ensureLoaded();
		this.layout = layout;
		this.props = props;
		this.markersById = layout.markers().stream()
				.collect(Collectors.toMap(SheetLayout.Marker::id, Function.identity()));
		this.dictionary = Objdetect.getPredefinedDictionary(dictionaryId(layout.dictionary()));

		SheetLayout.Charuco c = layout.charuco();
		if (c == null) {
			this.board = null;
			this.boardCorners = new Point3[0];
			this.boardMarkers = Map.of();
		}
		else {
			this.board = new CharucoBoard(new Size(c.squaresX(), c.squaresY()), (float) c.squareMm(),
					(float) c.markerMm(), dictionary);
			board.setLegacyPattern(c.legacyPattern());
			this.boardCorners = board.getChessboardCorners().toArray();
			this.boardMarkers = markerSquares(board);
		}
	}

	public RectifiedSheet rectify(Mat photo) {
		Mat gray = new Mat();
		Imgproc.cvtColor(photo, gray, Imgproc.COLOR_BGR2GRAY);
		Matches matches = board == null ? detectArucoSheet(gray) : detectCharucoSheet(gray);

		double ppm = props.pxPerMm();
		MatOfPoint2f src = new MatOfPoint2f(matches.imagePx().toArray(Point[]::new));
		MatOfPoint2f dst = new MatOfPoint2f(matches.sheetMm().stream().map(p -> scale(p, ppm)).toArray(Point[]::new));
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
		SheetLayout.Paper area = layout.rectifiedArea();
		Size size = new Size(area.widthMm() * ppm, area.heightMm() * ppm);
		Imgproc.warpPerspective(photo, rectified, homography, size, Imgproc.INTER_LINEAR);
		return new RectifiedSheet(rectified, ppm, matches.markerIds(), matches.quads(), matches.markerAreasMm(),
				matches.imagePx().size(), errorMm);
	}

	private Matches detectArucoSheet(Mat gray) {
		DetectorParameters params = new DetectorParameters();
		params.set_cornerRefinementMethod(Objdetect.CORNER_REFINE_SUBPIX);
		ArucoDetector detector = new ArucoDetector(dictionary, params);
		List<Mat> corners = new ArrayList<>();
		Mat ids = new Mat();
		detector.detectMarkers(gray, corners, ids);

		Matches m = new Matches(new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), new ArrayList<>(),
				new ArrayList<>());
		for (int i = 0; i < corners.size(); i++) {
			int id = (int) ids.get(i, 0)[0];
			SheetLayout.Marker marker = markersById.get(id);
			if (marker == null) {
				continue;
			}
			Point[] quad = quad(corners.get(i));
			for (int k = 0; k < 4; k++) {
				m.imagePx().add(quad[k]);
				m.sheetMm().add(markerCornerMm(marker, k));
			}
			m.markerIds().add(id);
			m.quads().add(new MatOfPoint(quad));
			m.markerAreasMm().add(new SheetLayout.Rect(marker.xMm(), marker.yMm(), layout.markerSizeMm(),
					layout.markerSizeMm()));
		}
		if (m.markerIds().size() < MIN_MARKERS) {
			throw new MeasurementException(Code.MARKERS_NOT_FOUND,
					"Feuille de référence introuvable (" + m.markerIds().size() + " marqueur(s) détecté(s) sur "
							+ layout.markers().size() + "). Cadrez toute la feuille, sans reflet sur les marqueurs.");
		}
		return m;
	}

	private Matches detectCharucoSheet(Mat gray) {
		DetectorParameters params = new DetectorParameters();
		params.set_cornerRefinementMethod(Objdetect.CORNER_REFINE_SUBPIX);
		CharucoDetector detector = new CharucoDetector(board, new CharucoParameters(), params, new RefineParameters());
		Mat corners = new Mat();
		Mat cornerIds = new Mat();
		List<Mat> markerCorners = new ArrayList<>();
		Mat markerIds = new Mat();
		detector.detectBoard(gray, corners, cornerIds, markerCorners, markerIds);

		Matches m = new Matches(new ArrayList<>(), new ArrayList<>(), new ArrayList<>(), new ArrayList<>(),
				new ArrayList<>());
		SheetLayout.Rect window = layout.lensWindow();
		for (int i = 0; i < cornerIds.rows(); i++) {
			Point3 p = boardCorners[(int) cornerIds.get(i, 0)[0]];
			if (window.contains(p.x, p.y, WINDOW_EDGE_MARGIN_MM)) {
				continue;
			}
			double[] xy = corners.get(i, 0);
			m.imagePx().add(new Point(xy[0], xy[1]));
			m.sheetMm().add(new Point(p.x, p.y));
		}
		for (int i = 0; i < markerCorners.size(); i++) {
			int id = (int) markerIds.get(i, 0)[0];
			SheetLayout.Rect square = boardMarkers.get(id);
			if (square == null) {
				continue;
			}
			m.markerIds().add(id);
			m.quads().add(new MatOfPoint(quad(markerCorners.get(i))));
			m.markerAreasMm().add(square);
		}
		if (m.imagePx().size() < MIN_CHARUCO_CORNERS) {
			throw new MeasurementException(Code.MARKERS_NOT_FOUND,
					"Feuille de référence introuvable (" + m.imagePx().size() + " coin(s) du damier détecté(s), "
							+ MIN_CHARUCO_CORNERS + " requis). Cadrez toute la feuille, sans reflet sur le damier.");
		}
		return m;
	}

	/** Square of each marker of the board, in board mm, from its four object points. */
	private static Map<Integer, SheetLayout.Rect> markerSquares(CharucoBoard board) {
		int[] ids = board.getIds().toArray();
		List<MatOfPoint3f> objPoints = board.getObjPoints();
		Map<Integer, SheetLayout.Rect> squares = new HashMap<>();
		for (int i = 0; i < ids.length; i++) {
			Point3[] pts = objPoints.get(i).toArray();
			double minX = Double.MAX_VALUE, minY = Double.MAX_VALUE, maxX = -Double.MAX_VALUE, maxY = -Double.MAX_VALUE;
			for (Point3 p : pts) {
				minX = Math.min(minX, p.x);
				minY = Math.min(minY, p.y);
				maxX = Math.max(maxX, p.x);
				maxY = Math.max(maxY, p.y);
			}
			squares.put(ids[i], new SheetLayout.Rect(minX, minY, maxX - minX, maxY - minY));
		}
		return squares;
	}

	private static Point[] quad(Mat corners) {
		Point[] quad = new Point[4];
		for (int k = 0; k < 4; k++) {
			double[] p = corners.get(0, k);
			quad[k] = new Point(p[0], p[1]);
		}
		return quad;
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
			throw new IllegalArgumentException("Unknown ArUco dictionary in the sheet layout: " + name, e);
		}
	}

}
