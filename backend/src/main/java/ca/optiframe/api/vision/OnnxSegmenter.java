package ca.optiframe.api.vision;

import java.nio.FloatBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Map;

import ai.onnxruntime.OnnxTensor;
import ai.onnxruntime.OrtEnvironment;
import ai.onnxruntime.OrtException;
import ai.onnxruntime.OrtSession;
import jakarta.annotation.PreDestroy;
import org.opencv.core.CvType;
import org.opencv.core.Mat;
import org.opencv.core.Size;
import org.opencv.imgproc.Imgproc;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import ca.optiframe.api.config.OptiframeProperties;

/**
 * Runs the segmentation model trained in {@code training/}. Preprocessing must match {@code training/dataset.py}:
 * window crop resized to N x N, RGB, /255, ImageNet mean/std, NCHW. Output: one logit channel, N x N.
 */
@Component
public class OnnxSegmenter implements LensSegmenter {

	private static final Logger log = LoggerFactory.getLogger(OnnxSegmenter.class);
	private static final float[] MEAN = { 0.485f, 0.456f, 0.406f };
	private static final float[] STD = { 0.229f, 0.224f, 0.225f };

	private final int inputSize;
	private final OrtEnvironment env;
	private final OrtSession session;

	public OnnxSegmenter(OptiframeProperties props) throws OrtException {
		OpenCv.ensureLoaded();
		this.inputSize = props.modelInputSize();
		Path model = Path.of(props.modelPath());
		if (Files.isRegularFile(model)) {
			this.env = OrtEnvironment.getEnvironment();
			this.session = env.createSession(model.toString(), new OrtSession.SessionOptions());
			log.info("Segmentation model loaded from {}", model.toAbsolutePath());
		}
		else {
			this.env = null;
			this.session = null;
			log.info("No segmentation model at {}, using the classical segmenter", model.toAbsolutePath());
		}
	}

	@Override
	public String name() {
		return "onnx";
	}

	@Override
	public boolean available() {
		return session != null;
	}

	@Override
	public Mat segment(Mat window, double pxPerMm) {
		int n = inputSize;
		Mat rgb = new Mat();
		Imgproc.resize(window, rgb, new Size(n, n), 0, 0, Imgproc.INTER_AREA);
		Imgproc.cvtColor(rgb, rgb, Imgproc.COLOR_BGR2RGB);
		byte[] pixels = new byte[n * n * 3];
		rgb.get(0, 0, pixels);

		FloatBuffer input = FloatBuffer.allocate(3 * n * n);
		for (int c = 0; c < 3; c++) {
			for (int i = 0; i < n * n; i++) {
				input.put(((pixels[i * 3 + c] & 0xff) / 255f - MEAN[c]) / STD[c]);
			}
		}
		input.rewind();

		float[] logits = new float[n * n];
		try (OnnxTensor tensor = OnnxTensor.createTensor(env, input, new long[] { 1, 3, n, n });
				OrtSession.Result result = session.run(Map.of(session.getInputNames().iterator().next(), tensor))) {
			float[][] plane = ((float[][][][]) result.get(0).getValue())[0][0];
			for (int y = 0; y < n; y++) {
				System.arraycopy(plane[y], 0, logits, y * n, n);
			}
		}
		catch (OrtException e) {
			throw new IllegalStateException("Segmentation model failed", e);
		}

		Mat prob = new Mat(n, n, CvType.CV_32FC1);
		prob.put(0, 0, logits);
		Imgproc.resize(prob, prob, window.size(), 0, 0, Imgproc.INTER_LINEAR);
		Mat mask = new Mat();
		Imgproc.threshold(prob, mask, 0, 255, Imgproc.THRESH_BINARY);
		mask.convertTo(mask, CvType.CV_8UC1);

		// Keep the main blob only, holes filled.
		return Masks.largest(Masks.externalContours(mask), 0, Double.MAX_VALUE)
				.map(c -> Masks.filled(c, window.size()))
				.orElse(mask);
	}

	@PreDestroy
	void close() throws OrtException {
		if (session != null) {
			session.close();
		}
	}

}
