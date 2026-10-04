package ca.optiframe.api.vision;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import org.junit.jupiter.api.Test;
import org.opencv.core.Core;
import org.opencv.core.CvType;
import org.opencv.core.Mat;
import org.opencv.core.MatOfByte;
import org.opencv.core.MatOfPoint2f;
import org.opencv.core.Point;
import org.opencv.core.Rect;
import org.opencv.core.Scalar;
import org.opencv.core.Size;
import org.opencv.imgcodecs.Imgcodecs;
import org.opencv.imgproc.Imgproc;
import org.opencv.objdetect.CharucoBoard;
import org.opencv.objdetect.Objdetect;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import ca.optiframe.api.api.dto.Eye;
import ca.optiframe.api.api.dto.MeasureResponse;
import ca.optiframe.api.sheet.SheetLayout;

/** End to end on a synthetic photo of the ChArUco sheet (default layout): blank lens window, tilted shot. */
@SpringBootTest
class CharucoMeasurementServiceTest {

	private static final double TRUE_PPM = 12;
	/** Width of the dark refraction rim, as seen on real lenses (0.3-0.5 mm). */
	private static final double RIM_MM = 0.5;

	@Autowired
	MeasurementService service;

	@Autowired
	SheetLayout layout;

	@Test
	void usesTheCharucoLayoutByDefault() {
		assertThat(layout.charuco()).isNotNull();
		assertThat(layout.dictionary()).isEqualTo("DICT_5X5_250");
	}

	@Test
	void measuresEllipticLensOnTiltedPhoto() {
		MatOfByte jpeg = new MatOfByte();
		Imgcodecs.imencode(".jpg", tiltedPhoto(renderBoard(50, 36, 90, 0)), jpeg);

		MeasureResponse r = service.measure(jpeg.toArray(), Eye.R, "classical");

		assertThat(r.markersFound()).isGreaterThan(40);
		assertThat(r.reprojectionErrorMm()).isLessThan(0.1);
		assertThat(r.contour().aMm()).isCloseTo(50, within(0.3));
		assertThat(r.contour().bMm()).isCloseTo(36, within(0.3));
		assertThat(r.steps()).hasSize(3);
	}

	@Test
	void ignoresTheSoftShadowNextToTheLens() {
		// Room light casts a shadow 25 grey levels deep, offset by 3 mm, with a 0.5 mm soft edge, like on real photos.
		MatOfByte jpeg = new MatOfByte();
		Imgcodecs.imencode(".jpg", tiltedPhoto(renderBoard(50, 36, 90, 25)), jpeg);

		MeasureResponse r = service.measure(jpeg.toArray(), Eye.R, "classical");

		assertThat(r.contour().aMm()).isCloseTo(50, within(0.3));
		assertThat(r.contour().bMm()).isCloseTo(36, within(0.3));
	}

	@Test
	void keepsAFaintRim() {
		// A clear lens shows a lighter rim than a tinted one: 90 grey levels below the paper instead of 160.
		MatOfByte jpeg = new MatOfByte();
		Imgcodecs.imencode(".jpg", tiltedPhoto(renderBoard(50, 36, 160, 25)), jpeg);

		MeasureResponse r = service.measure(jpeg.toArray(), Eye.R, "classical");

		assertThat(r.contour().aMm()).isCloseTo(50, within(0.3));
		assertThat(r.contour().bMm()).isCloseTo(36, within(0.3));
	}

	@Test
	void rejectsTheOldArucoSheet() {
		// 8 markers from DICT_4X4_50: none belongs to the ChArUco board.
		Mat sheet = new Mat(3000, 2200, CvType.CV_8UC3, new Scalar(250, 250, 250));
		var dict = Objdetect.getPredefinedDictionary(Objdetect.DICT_4X4_50);
		for (int id = 0; id < 8; id++) {
			Mat marker = new Mat();
			Objdetect.generateImageMarker(dict, id, 300, marker);
			Imgproc.cvtColor(marker, marker, Imgproc.COLOR_GRAY2BGR);
			marker.copyTo(new Mat(sheet, new Rect(100 + (id % 2) * 1700, 100 + (id / 2) * 700, 300, 300)));
		}
		MatOfByte jpeg = new MatOfByte();
		Imgcodecs.imencode(".jpg", sheet, jpeg);

		assertThatThrownBy(() -> service.measure(jpeg.toArray(), Eye.L, "classical"))
				.isInstanceOf(MeasurementException.class)
				.extracting(e -> ((MeasurementException) e).code())
				.isEqualTo(MeasurementException.Code.MARKERS_NOT_FOUND);
	}

	/**
	 * Board seen from above at TRUE_PPM, blank window, lens whose dark refraction rim ends at its true edge.
	 *
	 * @param rimGray grey level of the rim (paper is 250)
	 * @param shadowDepth how much darker the soft shadow offset towards the top-left is, 0 for none
	 */
	private Mat renderBoard(double aMm, double bMm, double rimGray, double shadowDepth) {
		SheetLayout.Charuco c = layout.charuco();
		CharucoBoard board = new CharucoBoard(new Size(c.squaresX(), c.squaresY()), (float) c.squareMm(),
				(float) c.markerMm(), Objdetect.getPredefinedDictionary(Objdetect.DICT_5X5_250));
		board.setLegacyPattern(c.legacyPattern());
		SheetLayout.Paper area = layout.rectifiedArea();
		int w = (int) Math.round(area.widthMm() * TRUE_PPM);
		int h = (int) Math.round(area.heightMm() * TRUE_PPM);
		Mat gray = new Mat();
		board.generateImage(new Size(w, h), gray, 0, 1);
		Mat sheet = new Mat();
		Imgproc.cvtColor(gray, sheet, Imgproc.COLOR_GRAY2BGR);

		SheetLayout.Rect win = layout.lensWindow();
		Imgproc.rectangle(sheet, new Point(win.xMm() * TRUE_PPM, win.yMm() * TRUE_PPM),
				new Point((win.xMm() + win.widthMm()) * TRUE_PPM, (win.yMm() + win.heightMm()) * TRUE_PPM),
				new Scalar(250, 250, 250), -1);
		Point center = new Point((win.xMm() + win.widthMm() / 2) * TRUE_PPM, (win.yMm() + win.heightMm() / 2) * TRUE_PPM);
		Size outer = new Size(aMm / 2 * TRUE_PPM, bMm / 2 * TRUE_PPM);
		Size inner = new Size((aMm / 2 - RIM_MM) * TRUE_PPM, (bMm / 2 - RIM_MM) * TRUE_PPM);
		if (shadowDepth > 0) {
			Mat shadow = Mat.zeros(sheet.size(), CvType.CV_8UC3);
			Point offset = new Point(center.x - 3 * TRUE_PPM, center.y - 3 * TRUE_PPM);
			Imgproc.ellipse(shadow, offset, outer, 0, 0, 360, Scalar.all(shadowDepth), -1);
			// Shadow edge about 0.5 mm wide, as measured on real photos: crisp enough to fool a low threshold.
			int blur = ((int) Math.round(0.5 * TRUE_PPM)) | 1;
			Imgproc.GaussianBlur(shadow, shadow, new Size(blur, blur), 0);
			Core.subtract(sheet, shadow, sheet);
		}
		Imgproc.ellipse(sheet, center, outer, 0, 0, 360, Scalar.all(rimGray), -1);
		Imgproc.ellipse(sheet, center, inner, 0, 0, 360, new Scalar(235, 235, 235), -1);

		// White paper margin around the board, like the printed page.
		Mat page = new Mat(h + 240, w + 240, CvType.CV_8UC3, new Scalar(250, 250, 250));
		sheet.copyTo(new Mat(page, new Rect(120, 120, w, h)));
		return page;
	}

	/** Perspective of a phone held above the table at an angle, on a dark table. */
	private static Mat tiltedPhoto(Mat sheet) {
		double w = sheet.cols(), h = sheet.rows();
		MatOfPoint2f src = new MatOfPoint2f(new Point(0, 0), new Point(w, 0), new Point(w, h), new Point(0, h));
		MatOfPoint2f dst = new MatOfPoint2f(new Point(420, 300), new Point(2580, 380), new Point(2800, 3700),
				new Point(250, 3600));
		Mat homography = Imgproc.getPerspectiveTransform(src, dst);
		Mat photo = new Mat();
		Imgproc.warpPerspective(sheet, photo, homography, new Size(3000, 4000), Imgproc.INTER_LINEAR,
				Core.BORDER_CONSTANT, new Scalar(60, 50, 40));
		Imgproc.GaussianBlur(photo, photo, new Size(3, 3), 0);
		return photo;
	}

}
