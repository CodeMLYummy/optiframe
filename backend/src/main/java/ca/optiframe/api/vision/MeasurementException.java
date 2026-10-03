package ca.optiframe.api.vision;

/** A photo that cannot be measured. The message is shown as is to the user, so it is in French. */
public class MeasurementException extends RuntimeException {

	public enum Code {
		IMAGE_UNREADABLE, MARKERS_NOT_FOUND, SCALE_CHECK_FAILED, PHOTO_BLURRY, LENS_NOT_FOUND, LENS_OUT_OF_WINDOW
	}

	private final Code code;

	public MeasurementException(Code code, String message) {
		super(message);
		this.code = code;
	}

	public Code code() {
		return code;
	}

}
