package ca.optiframe.api.vision;

import java.util.Base64;

import org.opencv.core.Mat;
import org.opencv.core.MatOfByte;
import org.opencv.core.MatOfInt;
import org.opencv.core.Size;
import org.opencv.imgcodecs.Imgcodecs;
import org.opencv.imgproc.Imgproc;

/** Control images sent back to the app, downscaled so the JSON stays small. */
final class DebugImages {

	private static final int MAX_SIDE = 1000;

	private DebugImages() {
	}

	static String toDataUrl(Mat image) {
		Mat small = image;
		double f = (double) MAX_SIDE / Math.max(image.cols(), image.rows());
		if (f < 1) {
			small = new Mat();
			Imgproc.resize(image, small, new Size(), f, f, Imgproc.INTER_AREA);
		}
		MatOfByte jpeg = new MatOfByte();
		Imgcodecs.imencode(".jpg", small, jpeg, new MatOfInt(Imgcodecs.IMWRITE_JPEG_QUALITY, 85));
		return "data:image/jpeg;base64," + Base64.getEncoder().encodeToString(jpeg.toArray());
	}

}
