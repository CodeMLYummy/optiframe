package ca.optiframe.api.api;

import java.io.IOException;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;

import ca.optiframe.api.api.dto.Eye;
import ca.optiframe.api.api.dto.MeasureResponse;
import ca.optiframe.api.sheet.SheetLayout;
import ca.optiframe.api.vision.MeasurementService;

@RestController
@RequestMapping("/api")
public class MeasureController {

	private final MeasurementService service;
	private final SheetLayout layout;

	public MeasureController(MeasurementService service, SheetLayout layout) {
		this.service = service;
		this.layout = layout;
	}

	@PostMapping(path = "/measure", consumes = "multipart/form-data")
	public MeasureResponse measure(@RequestParam MultipartFile image, @RequestParam Eye eye,
			@RequestParam(defaultValue = "auto") String method,
			@RequestParam(required = false) Double printScale) throws IOException {
		return service.measure(image.getBytes(), eye, method, printScale);
	}

	@GetMapping("/sheet")
	public SheetLayout sheet() {
		return layout;
	}

}
