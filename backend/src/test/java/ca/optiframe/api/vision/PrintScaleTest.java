package ca.optiframe.api.vision;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.assertj.core.api.Assertions.within;

import org.junit.jupiter.api.Test;
import org.opencv.core.MatOfByte;
import org.opencv.imgcodecs.Imgcodecs;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import ca.optiframe.api.api.dto.Eye;
import ca.optiframe.api.api.dto.MeasureResponse;
import ca.optiframe.api.sheet.SheetLayout;

/** A sheet printed smaller than nominal: optiframe.print-scale converts the measurement back to real mm. */
@SpringBootTest(properties = "optiframe.print-scale=0.9")
class PrintScaleTest {

	@Autowired
	MeasurementService service;

	@Autowired
	SheetLayout layout;

	@Test
	void scalesTheMeasurementToTheRealSizeOfThePrint() {
		// Drawn 50 x 36 mm on the nominal sheet; on a sheet printed at 90 % the same lens is 45 x 32.4 mm.
		MatOfByte jpeg = new MatOfByte();
		Imgcodecs.imencode(".jpg",
				CharucoMeasurementServiceTest
						.tiltedPhoto(CharucoMeasurementServiceTest.renderBoard(layout, 50, 36, 90, 0)),
				jpeg);

		MeasureResponse r = service.measure(jpeg.toArray(), Eye.R, "classical");

		assertThat(r.contour().aMm()).isCloseTo(50 * 0.9, within(0.4));
		assertThat(r.contour().bMm()).isCloseTo(36 * 0.9, within(0.4));
		assertThat(r.printScale()).isEqualTo(0.9);
	}

	@Test
	void theScaleSentByTheAppOverridesTheServerSetting() {
		MeasureResponse r = service.measure(photo(), Eye.R, "classical", 0.95);

		assertThat(r.printScale()).isEqualTo(0.95);
		assertThat(r.contour().aMm()).isCloseTo(50 * 0.95, within(0.4));
		assertThat(r.contour().bMm()).isCloseTo(36 * 0.95, within(0.4));
	}

	@Test
	void refusesAScaleThatCannotBeThisSheet() {
		assertThatThrownBy(() -> service.measure(photo(), Eye.R, "classical", 0.5))
				.isInstanceOf(MeasurementException.class)
				.extracting(e -> ((MeasurementException) e).code())
				.isEqualTo(MeasurementException.Code.PRINT_SCALE_INVALID);
	}

	private byte[] photo() {
		MatOfByte jpeg = new MatOfByte();
		Imgcodecs.imencode(".jpg",
				CharucoMeasurementServiceTest
						.tiltedPhoto(CharucoMeasurementServiceTest.renderBoard(layout, 50, 36, 90, 0)),
				jpeg);
		return jpeg.toArray();
	}

}
