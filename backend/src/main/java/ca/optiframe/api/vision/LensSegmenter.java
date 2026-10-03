package ca.optiframe.api.vision;

import org.opencv.core.Mat;

/** Isolates the lens in the rectified lens window. */
public interface LensSegmenter {

	String name();

	boolean available();

	/**
	 * @param window BGR crop of the lens window of the rectified sheet
	 * @return CV_8UC1 mask of the same size, 255 inside the lens (holes filled), 0 elsewhere
	 */
	Mat segment(Mat window, double pxPerMm);

}
