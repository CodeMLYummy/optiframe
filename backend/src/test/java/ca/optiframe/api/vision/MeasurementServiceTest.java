package ca.optiframe.api.vision;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import java.nio.ByteBuffer;
import java.util.zip.CRC32;

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
import org.opencv.objdetect.Objdetect;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import ca.optiframe.api.api.dto.Eye;
import ca.optiframe.api.api.dto.MeasureResponse;
import ca.optiframe.api.sheet.SheetLayout;

/** End to end on a synthetic photo: printed ArUco sheet, backlit 50 x 36 mm lens, shot at an angle. */
@SpringBootTest(properties = "optiframe.sheet-layout=sheet-layout.json")
class MeasurementServiceTest {

	private static final double TRUE_PPM = 12;
	/** Width of the dark refraction rim, as seen on real lenses (0.3-0.5 mm). */
	private static final double RIM_MM = 0.5;
	/**
	 * Tolerance on the synthetic lens. The polar contour refines to the outer side of the rim line; on this drawn
	 * 0.5 mm rim, blurred and resampled by the tilt, that side reads about +0.35 mm. Real lenses read unbiased
	 * against caliper values (+0.02 mm on 40 photos, see lensDetection/approaches.md), which are the criterion.
	 */
	private static final double SYNTHETIC_TOLERANCE_MM = 0.4;

	@Autowired
	MeasurementService service;

	@Autowired
	SheetLayout layout;

	@Test
	void measuresEllipticLensOnTiltedPhoto() {
		MatOfByte jpeg = new MatOfByte();
		Imgcodecs.imencode(".jpg", tiltedPhoto(renderSheet(50, 36)), jpeg);

		MeasureResponse r = service.measure(jpeg.toArray(), Eye.R, "classical");

		assertThat(r.markersFound()).isEqualTo(layout.markers().size());
		assertThat(r.contour().aMm()).isCloseTo(50, within(SYNTHETIC_TOLERANCE_MM));
		assertThat(r.contour().bMm()).isCloseTo(36, within(SYNTHETIC_TOLERANCE_MM));
		// Ramanujan's approximation of the ellipse perimeter.
		double a = 25, b = 18;
		double perimeter = Math.PI * (3 * (a + b) - Math.sqrt((3 * a + b) * (a + 3 * b)));
		assertThat(r.contour().perimeterMm()).isCloseTo(perimeter, within(1.0));
		assertThat(r.steps()).hasSize(3);
	}

	@Test
	void rejectsPhotoWithoutSheet() {
		Mat blank = new Mat(1000, 800, CvType.CV_8UC3, new Scalar(200, 200, 200));
		MatOfByte jpeg = new MatOfByte();
		Imgcodecs.imencode(".jpg", blank, jpeg);

		assertThatThrownBy(() -> service.measure(jpeg.toArray(), Eye.L, "auto"))
				.isInstanceOf(MeasurementException.class)
				.extracting(e -> ((MeasurementException) e).code())
				.isEqualTo(MeasurementException.Code.MARKERS_NOT_FOUND);
	}

	@Test
	void rejectsOtherFormatsBeforeDecoding() {
		MatOfByte bmp = new MatOfByte();
		Imgcodecs.imencode(".bmp", new Mat(100, 100, CvType.CV_8UC3, new Scalar(200, 200, 200)), bmp);

		assertThatThrownBy(() -> service.measure(bmp.toArray(), Eye.L, "auto"))
				.isInstanceOf(MeasurementException.class)
				.extracting(e -> ((MeasurementException) e).code())
				.isEqualTo(MeasurementException.Code.IMAGE_UNREADABLE);
	}

	@Test
	void rejectsHugePngBeforeDecoding() {
		// Signature + IHDR declaring 40000 x 40000 px RGB: what a decompression bomb starts with.
		byte[] ihdr = { 'I', 'H', 'D', 'R', 0, 0, (byte) 0x9c, 0x40, 0, 0, (byte) 0x9c, 0x40, 8, 2, 0, 0, 0 };
		CRC32 crc = new CRC32();
		crc.update(ihdr);
		byte[] png = ByteBuffer.allocate(8 + 4 + ihdr.length + 4)
				.put(new byte[] { (byte) 0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n' })
				.putInt(13)
				.put(ihdr)
				.putInt((int) crc.getValue())
				.array();

		assertThatThrownBy(() -> service.measure(png, Eye.L, "auto"))
				.isInstanceOf(MeasurementException.class)
				.extracting(e -> ((MeasurementException) e).code())
				.isEqualTo(MeasurementException.Code.IMAGE_UNREADABLE);
	}

	/** Sheet seen exactly from above at TRUE_PPM, with a lens whose dark refraction rim ends at its true edge. */
	private Mat renderSheet(double aMm, double bMm) {
		int w = (int) (layout.paper().widthMm() * TRUE_PPM);
		int h = (int) (layout.paper().heightMm() * TRUE_PPM);
		Mat sheet = new Mat(h, w, CvType.CV_8UC3, new Scalar(250, 250, 250));

		var dict = Objdetect.getPredefinedDictionary(Objdetect.DICT_4X4_50);
		int side = (int) Math.round(layout.markerSizeMm() * TRUE_PPM);
		for (SheetLayout.Marker m : layout.markers()) {
			Mat marker = new Mat();
			Objdetect.generateImageMarker(dict, m.id(), side, marker);
			Imgproc.cvtColor(marker, marker, Imgproc.COLOR_GRAY2BGR);
			marker.copyTo(new Mat(sheet, new Rect((int) Math.round(m.xMm() * TRUE_PPM),
					(int) Math.round(m.yMm() * TRUE_PPM), side, side)));
		}

		SheetLayout.Rect win = layout.lensWindow();
		Point center = new Point((win.xMm() + win.widthMm() / 2) * TRUE_PPM,
				(win.yMm() + win.heightMm() / 2) * TRUE_PPM);
		Size outer = new Size(aMm / 2 * TRUE_PPM, bMm / 2 * TRUE_PPM);
		Size inner = new Size((aMm / 2 - RIM_MM) * TRUE_PPM, (bMm / 2 - RIM_MM) * TRUE_PPM);
		Imgproc.ellipse(sheet, center, outer, 0, 0, 360, new Scalar(90, 90, 90), -1);
		Imgproc.ellipse(sheet, center, inner, 0, 0, 360, new Scalar(235, 235, 235), -1);
		return sheet;
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
