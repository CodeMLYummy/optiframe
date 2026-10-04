package ca.optiframe.api.vision;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Iterator;
import java.util.List;
import java.util.Locale;

import javax.imageio.ImageIO;
import javax.imageio.ImageReader;
import javax.imageio.stream.ImageInputStream;

import org.opencv.core.Core;
import org.opencv.core.CvType;
import org.opencv.core.Mat;
import org.opencv.core.MatOfByte;
import org.opencv.core.MatOfDouble;
import org.opencv.core.Point;
import org.opencv.core.Rect;
import org.opencv.core.Scalar;
import org.opencv.imgcodecs.Imgcodecs;
import org.opencv.imgproc.Imgproc;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import ca.optiframe.api.api.dto.Eye;
import ca.optiframe.api.api.dto.LensContour;
import ca.optiframe.api.api.dto.MeasureResponse;
import ca.optiframe.api.config.OptiframeProperties;
import ca.optiframe.api.sheet.SheetLayout;
import ca.optiframe.api.vision.MeasurementException.Code;

/** Photo to lens contour: rectify, segment, measure. */
@Service
public class MeasurementService {

	private static final Logger log = LoggerFactory.getLogger(MeasurementService.class);
	private static final Scalar GREEN = new Scalar(0, 200, 0);
	private static final Scalar RED = new Scalar(0, 0, 255);
	private static final Scalar BLUE = new Scalar(255, 120, 0);
	/** 30 MP: above any phone photo (the app sends at most 4000 px on the long side), about 90 MB once decoded. */
	private static final long MAX_PIXELS = 30_000_000;

	private final SheetLayout layout;
	private final OptiframeProperties props;
	private final Rectifier rectifier;
	private final ClassicalSegmenter classical;
	private final OnnxSegmenter onnx;
	private final ContourMeasurer measurer;

	public MeasurementService(SheetLayout layout, OptiframeProperties props, Rectifier rectifier,
			ClassicalSegmenter classical, OnnxSegmenter onnx, ContourMeasurer measurer) {
		this.layout = layout;
		this.props = props;
		this.rectifier = rectifier;
		this.classical = classical;
		this.onnx = onnx;
		this.measurer = measurer;
	}

	/**
	 * @param method "auto" (model if available), "classical" or "onnx"
	 */
	public MeasureResponse measure(byte[] imageBytes, Eye eye, String method) {
		long start = System.currentTimeMillis();
		checkImageHeader(imageBytes);
		Mat photo = Imgcodecs.imdecode(new MatOfByte(imageBytes), Imgcodecs.IMREAD_COLOR);
		if (photo.empty()) {
			throw new MeasurementException(Code.IMAGE_UNREADABLE, "Image illisible. Utilisez une photo JPEG ou PNG.");
		}

		RectifiedSheet sheet = rectifier.rectify(photo);
		double ppm = sheet.pxPerMm();

		double sharpness = markerSharpness(sheet);
		if (sharpness < props.minSharpness()) {
			throw new MeasurementException(Code.PHOTO_BLURRY,
					"Photo floue. Tenez le téléphone immobile et touchez l'écran pour faire la mise au point.");
		}

		SheetLayout.Rect w = layout.lensWindow();
		Rect roi = new Rect((int) Math.round(w.xMm() * ppm), (int) Math.round(w.yMm() * ppm),
				(int) Math.round(w.widthMm() * ppm), (int) Math.round(w.heightMm() * ppm));
		Mat window = new Mat(sheet.image(), roi).clone();

		LensSegmenter segmenter = pick(method);
		Mat mask = segmenter.segment(window, ppm);
		if (Core.countNonZero(mask) == 0) {
			throw new MeasurementException(Code.LENS_NOT_FOUND,
					"Verre introuvable. Placez-le au centre du cadre, sur le fond éclairé.");
		}
		Rect lensBox = Imgproc.boundingRect(mask);
		if (lensBox.x <= 1 || lensBox.y <= 1 || lensBox.br().x >= roi.width - 1 || lensBox.br().y >= roi.height - 1) {
			throw new MeasurementException(Code.LENS_OUT_OF_WINDOW,
					"Le verre dépasse du cadre. Centrez-le dans le rectangle de la feuille.");
		}

		// The rectified image is in the sheet's nominal mm; a sheet printed smaller holds more pixels per real mm.
		ContourMeasurer.Measurement m = measurer.measure(mask, ppm / props.printScale(), eye, props.edgeBiasMm());
		saveForDataset(window, mask);

		List<MeasureResponse.Step> steps = List.of(
				new MeasureResponse.Step("1. Marqueurs détectés", DebugImages.toDataUrl(markersOverlay(photo, sheet))),
				new MeasureResponse.Step("2. Feuille redressée", DebugImages.toDataUrl(rectifiedOverlay(sheet, roi))),
				new MeasureResponse.Step("3. Contour du verre", DebugImages.toDataUrl(contourOverlay(window, m))));

		long elapsed = System.currentTimeMillis() - start;
		LensContour c = m.contour();
		log.info("Measured {} with {}: A={} B={} mm ({} markers, {} points, err {} mm, {} ms)", eye, segmenter.name(),
				String.format("%.2f", c.aMm()), String.format("%.2f", c.bMm()), sheet.markerIds().size(),
				sheet.pointsUsed(), String.format("%.3f", sheet.reprojectionErrorMm()), elapsed);
		return new MeasureResponse(c, segmenter.name(), ppm, sheet.markerIds().size(), sheet.reprojectionErrorMm(),
				sharpness, m.rotatedAMm(), m.rotatedBMm(), steps, elapsed);
	}

	/**
	 * Reads only the header (pure Java) before the native decoder sees the bytes: JPEG or PNG only, and a pixel
	 * count that fits in memory. A few-MB PNG can declare 30000 x 30000 px and decode to gigabytes.
	 */
	private static void checkImageHeader(byte[] imageBytes) {
		try (ImageInputStream in = ImageIO.createImageInputStream(new ByteArrayInputStream(imageBytes))) {
			Iterator<ImageReader> readers = ImageIO.getImageReaders(in);
			if (readers.hasNext()) {
				ImageReader reader = readers.next();
				try {
					reader.setInput(in, true, true);
					String format = reader.getFormatName().toLowerCase(Locale.ROOT);
					if ((format.equals("jpeg") || format.equals("png"))
							&& (long) reader.getWidth(0) * reader.getHeight(0) <= MAX_PIXELS) {
						return;
					}
				}
				finally {
					reader.dispose();
				}
			}
		}
		catch (IOException | RuntimeException e) {
			// Falls through to the rejection below.
		}
		throw new MeasurementException(Code.IMAGE_UNREADABLE,
				"Image illisible ou trop grande. Utilisez une photo JPEG ou PNG.");
	}

	private LensSegmenter pick(String method) {
		return switch (method) {
			case "classical" -> classical;
			default -> onnx.available() ? onnx : classical;
		};
	}

	/** Variance of the Laplacian over the detected markers: they are sharp black and white squares in every photo. */
	private double markerSharpness(RectifiedSheet sheet) {
		double ppm = sheet.pxPerMm();
		Rect bounds = new Rect(0, 0, sheet.image().cols(), sheet.image().rows());
		double sum = 0;
		int count = 0;
		for (SheetLayout.Rect area : sheet.markerAreasMm()) {
			Rect r = intersect(new Rect((int) Math.round(area.xMm() * ppm), (int) Math.round(area.yMm() * ppm),
					(int) Math.round(area.widthMm() * ppm), (int) Math.round(area.heightMm() * ppm)), bounds);
			if (r.area() == 0) {
				continue;
			}
			Mat region = new Mat(sheet.image(), r);
			Mat gray = new Mat();
			Imgproc.cvtColor(region, gray, Imgproc.COLOR_BGR2GRAY);
			Mat lap = new Mat();
			Imgproc.Laplacian(gray, lap, CvType.CV_64F);
			MatOfDouble mean = new MatOfDouble();
			MatOfDouble std = new MatOfDouble();
			Core.meanStdDev(lap, mean, std);
			sum += std.get(0, 0)[0] * std.get(0, 0)[0];
			count++;
		}
		// No marker square in view (ChArUco corners alone can be enough for the homography): not judged blurry here.
		return count == 0 ? Double.MAX_VALUE : sum / count;
	}

	private static Rect intersect(Rect a, Rect b) {
		int x = Math.max(a.x, b.x);
		int y = Math.max(a.y, b.y);
		int w = Math.min(a.x + a.width, b.x + b.width) - x;
		int h = Math.min(a.y + a.height, b.y + b.height) - y;
		return w > 0 && h > 0 ? new Rect(x, y, w, h) : new Rect();
	}

	private static Mat markersOverlay(Mat photo, RectifiedSheet sheet) {
		Mat out = photo.clone();
		int thickness = Math.max(3, photo.cols() / 300);
		Imgproc.polylines(out, sheet.markerQuads(), true, GREEN, thickness);
		return out;
	}

	private static Mat rectifiedOverlay(RectifiedSheet sheet, Rect roi) {
		Mat out = sheet.image().clone();
		Imgproc.rectangle(out, roi.tl(), roi.br(), BLUE, 6);
		return out;
	}

	private static Mat contourOverlay(Mat window, ContourMeasurer.Measurement m) {
		Mat out = window.clone();
		Imgproc.polylines(out, List.of(m.pixelContour()), true, RED, 3);
		Rect box = Imgproc.boundingRect(m.pixelContour());
		Imgproc.rectangle(out, box.tl(), box.br(), BLUE, 2);
		LensContour c = m.contour();
		String label = String.format("A %.1f  B %.1f mm", c.aMm(), c.bMm());
		Imgproc.putText(out, label, new Point(20, 60), Imgproc.FONT_HERSHEY_SIMPLEX, 1.8, RED, 4);
		return out;
	}

	private void saveForDataset(Mat window, Mat mask) {
		String dir = props.datasetDir();
		if (dir == null || dir.isBlank()) {
			return;
		}
		try {
			Path root = Path.of(dir);
			Files.createDirectories(root.resolve("images"));
			Files.createDirectories(root.resolve("masks"));
			String name = System.currentTimeMillis() + ".png";
			Imgcodecs.imwrite(root.resolve("images").resolve(name).toString(), window);
			Imgcodecs.imwrite(root.resolve("masks").resolve(name).toString(), mask);
		}
		catch (Exception e) {
			log.warn("Could not save dataset sample", e);
		}
	}

}
