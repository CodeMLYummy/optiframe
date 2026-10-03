package ca.optiframe.api.vision;

import nu.pattern.OpenCV;

/** Loads the native OpenCV library bundled in the openpnp jar, once. */
public final class OpenCv {

	static {
		OpenCV.loadLocally();
	}

	private OpenCv() {
	}

	public static void ensureLoaded() {
		// Triggers the static initializer.
	}

}
